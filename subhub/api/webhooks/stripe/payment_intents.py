import logging
import json

from subhub.api.webhooks.stripe.abstract import AbstractStripeWebhookEvent
from subhub.api.webhooks.routes.static import StaticRoutes

logger = logging.getLogger("payment_intents")
log_handle = logging.StreamHandler()
log_handle.setLevel(logging.INFO)
logformat = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log_handle.setFormatter(logformat)
logger.addHandler(log_handle)


class StripePaymentIntentSucceeded(AbstractStripeWebhookEvent):
    def run(self):
        d = self.payload
        sfd = {}
        sfd["event_id"] = d["id"]
        sfd["event_type"] = d["type"]
        sfd["brand"] = d["data"]["object"]["charges"]["data"][0][
            "payment_method_details"
        ]["card"]["brand"]
        sfd["last4"] = d["data"]["object"]["charges"]["data"][0][
            "payment_method_details"
        ]["card"]["last4"]
        sfd["exp_month"] = d["data"]["object"]["charges"]["data"][0][
            "payment_method_details"
        ]["card"]["exp_month"]
        sfd["exp_year"] = d["data"]["object"]["charges"]["data"][0][
            "payment_method_details"
        ]["card"]["exp_year"]
        sfd["charge_id"] = d["data"]["object"]["charges"]["data"][0]["id"]
        sfd["invoice_id"] = d["data"]["object"]["invoice"]
        sfd["customer_id"] = d["data"]["object"]["customer"]
        amount_paid = 0
        for p in d["data"]["object"]["charges"]["data"]:
            amount_paid = amount_paid + (p["amount"] - p["amount_refunded"])
        sfd["amount_paid"] = amount_paid
        sfd["created"] = d["data"]["object"]["created"]

        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(sfd))
