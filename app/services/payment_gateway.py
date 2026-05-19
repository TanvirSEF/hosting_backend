from app.models.billing import PaymentGateway


class PaymentGatewayService:
    """
    Simulation boundary for payment providers.

    Real SSLCommerz, bKash, and Nagad implementations should live behind this
    service contract so billing routes do not depend on vendor-specific payloads.
    """

    def verify_manual_payment(self, gateway: PaymentGateway, transaction_id: str, amount) -> dict:
        return {
            "success": True,
            "gateway": gateway.value,
            "transaction_id": transaction_id,
            "amount": str(amount),
            "mode": "manual_simulation",
        }

    def verify_webhook_signature(self, gateway: PaymentGateway, payload: dict, signature: str) -> bool:
        return False

    async def parse_webhook(self, gateway: PaymentGateway, payload: dict) -> dict:
        return {
            "success": False,
            "gateway": gateway.value,
            "error": "Webhook integration placeholder. Add real provider parser here.",
        }


payment_gateway_service = PaymentGatewayService()
