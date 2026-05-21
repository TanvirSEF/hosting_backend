import os
import unittest
from datetime import datetime, timedelta
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite:///./test_nexhost.db"
os.environ["JWT_SECRET"] = "test-secret-key-that-is-long-enough-for-hs256"
os.environ["REDIS_URL"] = "redis://127.0.0.1:6379/15"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.database.session import Base
from app.main import app
from app.core.security import create_access_token, get_password_hash
from app.core.celery_app import celery_app
from app.models.billing import BillingReason, BillingServiceType, Invoice, InvoiceStatus
from app.models.domain import DomainStatus, UserDomain
from app.models.hosting import HostingOrder, HostingPackage, HostingStatus
from app.models.hosting_tools import HostingUsageSnapshot
from app.models.security import AuditLog
from app.models.user import User
from app.services.billing_lifecycle import (
    create_hosting_renewal_invoice,
    generate_renewal_invoices,
    mark_due_reminders,
    process_overdue_services,
)
from app.services.domain_provider import domain_provider
from app.services.whm import whm_service
from app.tasks.hosting_tool_tasks import sync_all_usage_mock


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


class BackendFlowTestCase(unittest.TestCase):
    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(app)

    def db(self):
        return TestingSessionLocal()

    def create_user(self, is_admin=False, email="user@example.com") -> User:
        db = self.db()
        try:
            user = User(
                full_name="Test User",
                email=email,
                hashed_password=get_password_hash("password123"),
                is_active=True,
                is_admin=is_admin,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
        finally:
            db.close()

    def auth_headers(self, user: User) -> dict:
        return {"Authorization": f"Bearer {create_access_token(user.id)}"}

    def create_package(self) -> HostingPackage:
        db = self.db()
        try:
            package = HostingPackage(
                name="Starter",
                whm_package_id="starter_pkg",
                price_bdt=Decimal("500.00"),
                billing_period_days=30,
                is_active=True,
            )
            db.add(package)
            db.commit()
            db.refresh(package)
            return package
        finally:
            db.close()


class AuthTests(BackendFlowTestCase):
    def test_signup_login_and_me_flow(self):
        signup = self.client.post(
            "/api/v1/auth/signup",
            json={
                "full_name": "Hasan",
                "email": "hasan@example.com",
                "phone_number": "01700000000",
                "password": "strongpass123",
            },
        )
        self.assertEqual(signup.status_code, 201)
        self.assertIn("access_token", signup.json())

        login = self.client.post(
            "/api/v1/auth/login",
            json={"email": "hasan@example.com", "password": "strongpass123"},
        )
        self.assertEqual(login.status_code, 200)
        token = login.json()["access_token"]

        me = self.client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["email"], "hasan@example.com")


class AdminOperationTests(BackendFlowTestCase):
    def test_admin_can_manage_user_and_self_demote_is_blocked(self):
        admin = self.create_user(is_admin=True, email="admin@example.com")
        user = self.create_user(email="client@example.com")

        update = self.client.put(
            f"/api/v1/admin/users/{user.id}",
            headers=self.auth_headers(admin),
            json={"full_name": "Client Updated", "phone_number": "01800000000"},
        )
        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.json()["full_name"], "Client Updated")

        disable = self.client.put(
            f"/api/v1/admin/users/{user.id}/active",
            headers=self.auth_headers(admin),
            json={"is_active": False},
        )
        self.assertEqual(disable.status_code, 200)
        self.assertFalse(disable.json()["is_active"])

        promote = self.client.put(
            f"/api/v1/admin/users/{user.id}/admin-role",
            headers=self.auth_headers(admin),
            json={"is_admin": True},
        )
        self.assertEqual(promote.status_code, 200)
        self.assertTrue(promote.json()["is_admin"])

        self_demote = self.client.put(
            f"/api/v1/admin/users/{admin.id}/admin-role",
            headers=self.auth_headers(admin),
            json={"is_admin": False},
        )
        self.assertEqual(self_demote.status_code, 400)

        db = self.db()
        try:
            audit_count = db.query(AuditLog).count()
            self.assertGreaterEqual(audit_count, 3)
        finally:
            db.close()

    def test_package_update_disable_and_safe_delete(self):
        admin = self.create_user(is_admin=True, email="admin@example.com")
        user = self.create_user(email="client@example.com")
        package = self.create_package()

        update = self.client.put(
            f"/api/v1/admin/hosting-packages/{package.id}",
            headers=self.auth_headers(admin),
            json={"price_bdt": "650.00", "billing_period_days": 60},
        )
        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.json()["billing_period_days"], 60)

        disable = self.client.put(
            f"/api/v1/admin/hosting-packages/{package.id}/disable",
            headers=self.auth_headers(admin),
        )
        self.assertEqual(disable.status_code, 200)
        self.assertFalse(disable.json()["is_active"])

        db = self.db()
        try:
            linked = HostingOrder(
                user_id=user.id,
                package_id=package.id,
                domain="linked.com",
                package_name="Starter",
                status=HostingStatus.ACTIVE,
            )
            db.add(linked)
            db.commit()
        finally:
            db.close()

        blocked_delete = self.client.delete(
            f"/api/v1/admin/hosting-packages/{package.id}",
            headers=self.auth_headers(admin),
        )
        self.assertEqual(blocked_delete.status_code, 400)


class HostingDomainFlowTests(BackendFlowTestCase):
    def test_hosting_order_creates_service_linked_unpaid_invoice(self):
        user = self.create_user(email="client@example.com")
        package = self.create_package()

        response = self.client.post(
            "/api/v1/hosting/orders",
            headers=self.auth_headers(user),
            json={"domain": "example.com", "package_id": package.id},
        )
        self.assertEqual(response.status_code, 201)
        order_id = response.json()["id"]

        db = self.db()
        try:
            invoice = db.query(Invoice).filter(Invoice.service_id == order_id).first()
            self.assertIsNotNone(invoice)
            self.assertEqual(invoice.service_type, BillingServiceType.HOSTING)
            self.assertEqual(invoice.billing_reason, BillingReason.INITIAL_PURCHASE)
            self.assertEqual(invoice.status, InvoiceStatus.UNPAID)
        finally:
            db.close()

    def test_domain_registration_creates_active_domain_with_auto_renew(self):
        user = self.create_user(email="client@example.com")
        response = self.client.post(
            "/api/v1/domain/register",
            headers=self.auth_headers(user),
            json={"domain_name": "domain.com", "years": 1},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], DomainStatus.ACTIVE.value)
        self.assertTrue(response.json()["auto_renew"])


class BillingLifecycleTests(BackendFlowTestCase):
    def test_renewal_invoice_is_idempotent_and_paid_invoice_extends_expiry(self):
        user = self.create_user(email="client@example.com")
        package = self.create_package()
        db = self.db()
        try:
            order = HostingOrder(
                user_id=user.id,
                package_id=package.id,
                domain="renew.com",
                package_name=package.name,
                username="renew01",
                status=HostingStatus.ACTIVE,
                whm_package_id=package.whm_package_id,
                expires_at=datetime.utcnow() + timedelta(days=2),
            )
            db.add(order)
            db.commit()
            db.refresh(order)
            order_id = order.id
            old_expiry = order.expires_at

            first = create_hosting_renewal_invoice(db, order)
            second = create_hosting_renewal_invoice(db, order)
            self.assertEqual(first.id, second.id)
            db.commit()
            invoice_id = first.id
        finally:
            db.close()

        pay = self.client.post(
            "/api/v1/billing/verify-payment",
            json={"invoice_id": invoice_id, "gateway": "bkash", "transaction_id": "TXN-RENEW-1"},
        )
        self.assertEqual(pay.status_code, 200)
        self.assertTrue(pay.json()["lifecycle_result"]["applied"])

        db = self.db()
        try:
            refreshed = db.query(HostingOrder).filter(HostingOrder.id == order_id).first()
            self.assertGreater(refreshed.expires_at, old_expiry)
        finally:
            db.close()

    def test_generate_reminders_and_overdue_processing(self):
        user = self.create_user(email="client@example.com")
        package = self.create_package()
        db = self.db()
        try:
            order = HostingOrder(
                user_id=user.id,
                package_id=package.id,
                domain="overdue.com",
                package_name=package.name,
                username="over01",
                status=HostingStatus.ACTIVE,
                expires_at=datetime.utcnow() + timedelta(days=1),
            )
            domain = UserDomain(
                user_id=user.id,
                domain_name="expired.com",
                status=DomainStatus.ACTIVE,
                expiry_date=datetime.utcnow() - timedelta(days=1),
            )
            db.add_all([order, domain])
            db.commit()
            db.refresh(order)

            generated = generate_renewal_invoices(db, days_ahead=7)
            self.assertEqual(generated["generated_hosting_invoices"], 1)
            reminders = mark_due_reminders(db, days_ahead=7)
            self.assertGreaterEqual(reminders, 1)

            invoice = (
                db.query(Invoice)
                .filter(
                    Invoice.service_type == BillingServiceType.HOSTING,
                    Invoice.service_id == order.id,
                )
                .first()
            )
            invoice.due_at = datetime.utcnow() - timedelta(days=1)
            db.commit()

            overdue = process_overdue_services(db)
            self.assertEqual(overdue["hosting_suspended"], 1)
            self.assertEqual(overdue["domains_expired"], 1)
            db.flush()
            db.refresh(order)
            db.refresh(domain)
            self.assertEqual(order.status, HostingStatus.SUSPENDED)
            self.assertEqual(domain.status, DomainStatus.EXPIRED)
        finally:
            db.close()


class MockProviderTests(BackendFlowTestCase):
    def test_whm_and_domain_mock_providers_return_success(self):
        import asyncio

        async def run_checks():
            suspend = await whm_service.suspend_account("cpuser", "Testing")
            unsuspend = await whm_service.unsuspend_account("cpuser")
            reset = await whm_service.reset_password("cpuser")
            nameservers = await domain_provider.update_nameservers("example.com", ["ns1.test", "ns2.test"])
            renew = await domain_provider.renew_domain("example.com", 1)
            return suspend, unsuspend, reset, nameservers, renew

        suspend, unsuspend, reset, nameservers, renew = asyncio.run(run_checks())
        self.assertTrue(suspend["success"])
        self.assertTrue(unsuspend["success"])
        self.assertTrue(reset["success"])
        self.assertIn("password", reset)
        self.assertTrue(nameservers["success"])
        self.assertTrue(renew["success"])


class CeleryBeatScheduleTests(BackendFlowTestCase):
    def test_expected_periodic_jobs_are_registered(self):
        schedule = celery_app.conf.beat_schedule
        self.assertIn("generate-renewal-invoices-daily", schedule)
        self.assertEqual(schedule["generate-renewal-invoices-daily"]["task"], "tasks.generate_renewal_invoices")
        self.assertIn("mark-due-reminders-daily", schedule)
        self.assertEqual(schedule["mark-due-reminders-daily"]["task"], "tasks.mark_due_reminders")
        self.assertIn("process-overdue-services-hourly", schedule)
        self.assertEqual(schedule["process-overdue-services-hourly"]["task"], "tasks.process_overdue_services")
        self.assertIn("sync-active-hosting-usage-every-six-hours", schedule)
        self.assertEqual(schedule["sync-active-hosting-usage-every-six-hours"]["task"], "tasks.sync_all_usage_mock")

    def test_scheduled_usage_sync_covers_active_and_suspended_services(self):
        user = self.create_user(email="client@example.com")
        package = self.create_package()
        db = self.db()
        try:
            active = HostingOrder(
                user_id=user.id,
                package_id=package.id,
                domain="active-usage.com",
                package_name=package.name,
                username="active01",
                status=HostingStatus.ACTIVE,
            )
            suspended = HostingOrder(
                user_id=user.id,
                package_id=package.id,
                domain="suspended-usage.com",
                package_name=package.name,
                username="susp01",
                status=HostingStatus.SUSPENDED,
            )
            terminated = HostingOrder(
                user_id=user.id,
                package_id=package.id,
                domain="terminated-usage.com",
                package_name=package.name,
                username="term01",
                status=HostingStatus.TERMINATED,
            )
            db.add_all([active, suspended, terminated])
            db.commit()
        finally:
            db.close()

        import app.tasks.hosting_tool_tasks as hosting_tool_tasks

        original_session_local = hosting_tool_tasks.SessionLocal
        hosting_tool_tasks.SessionLocal = TestingSessionLocal
        try:
            result = sync_all_usage_mock()
            self.assertEqual(result["synced_hosting_orders"], 2)
        finally:
            hosting_tool_tasks.SessionLocal = original_session_local

        db = self.db()
        try:
            snapshots = db.query(HostingUsageSnapshot).all()
            self.assertEqual(len(snapshots), 2)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
