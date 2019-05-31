import logging
import json

from subhub.api.webhooks.stripe.abstract import AbstractStripeWebhookEvent
from subhub.api.webhooks.routes.static import StaticRoutes

logger = logging.getLogger("charge_succeeded")
log_handle = logging.StreamHandler()
log_handle.setLevel(logging.INFO)
logformat = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log_handle.setFormatter(logformat)
logger.addHandler(log_handle)


class StripeChargeSucceededEvent(AbstractStripeWebhookEvent):
    def run(self):
        d = self.payload

        sfd = {}
        sfd["event_id"] = d["id"]
        sfd["event_type"] = d["type"]
        sfd["transaction_amount"] = d["data"]["object"]["amount"]
        sfd["created_date"] = d["created"]
        sfd["transaction_currency"] = d["data"]["object"]["currency"]
        sfd["charge_id"] = d["id"]
        sfd["customer_id"] = d["data"]["object"]["customer"]
        sfd["card_last4"] = d["data"]["object"]["payment_method_details"]["card"][
            "last4"
        ]
        sfd["card_brand"] = d["data"]["object"]["payment_method_details"]["card"][
            "brand"
        ]
        sfd["card_exp_month"] = d["data"]["object"]["payment_method_details"]["card"][
            "exp_month"
        ]
        sfd["card_exp_year"] = d["data"]["object"]["payment_method_details"]["card"][
            "exp_year"
        ]
        sfd["invoice_id"] = d["data"]["object"]["invoice"]
        order_id = d["data"]["object"]["metadata"].get("order_id")
        sfd["order_id"] = order_id
        sfd["application_fee"] = d["data"]["object"]["application_fee"]
        routes = [StaticRoutes.SALESFORCE_ROUTE]

        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(sfd))


class StripeChargeCapturedEvent(AbstractStripeWebhookEvent):
    def run(self):
        print(self.payload)
