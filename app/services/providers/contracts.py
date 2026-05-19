from typing import Protocol


class HostingProvider(Protocol):
    async def create_account(self, domain: str, package_id: str, contact_email: str) -> dict:
        ...

    async def suspend_account(self, username: str, reason: str) -> dict:
        ...

    async def unsuspend_account(self, username: str) -> dict:
        ...

    async def terminate_account(self, username: str) -> dict:
        ...

    async def reset_password(self, username: str) -> dict:
        ...

    async def change_package(self, username: str, package_id: str) -> dict:
        ...


class DomainProvider(Protocol):
    async def check_availability(self, domain_name: str) -> dict:
        ...

    async def register_domain(self, domain_name: str, years: int) -> dict:
        ...

    async def renew_domain(self, domain_name: str, years: int) -> dict:
        ...

    async def update_nameservers(self, domain_name: str, nameservers: list[str]) -> dict:
        ...


class PaymentGateway(Protocol):
    def verify_signature(self, payload: dict, signature: str) -> bool:
        ...

    async def parse_webhook(self, payload: dict) -> dict:
        ...

