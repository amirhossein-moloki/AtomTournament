from zarinpal import ZarinPal
from zarinpal.utils import Config
from django.conf import settings


class ZarinpalService:
    def __init__(self):
        self.config = Config(
            merchant_id=settings.ZARINPAL_MERCHANT_ID,
            sandbox=settings.ZARINPAL_SANDBOX,
        )
        self.zarinpal = ZarinPal(self.config)

    def create_payment(
        self, amount, description, callback_url, mobile=None, email=None
    ):
        try:
            response = self.zarinpal.payments.create(
                {
                    "amount": amount,
                    "callback_url": callback_url,
                    "description": description,
                    "mobile": mobile,
                    "email": email,
                }
            )
            return response
        except Exception as e:
            return {"error": str(e)}

    def verify_payment(self, amount, authority):
        try:
            response = self.zarinpal.verifications.verify(
                {
                    "amount": amount,
                    "authority": authority,
                }
            )
            return response
        except Exception as e:
            return {"error": str(e)}

    def generate_payment_url(self, authority):
        return self.zarinpal.payments.generate_payment_url(authority)
