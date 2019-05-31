import logging
import json

from subhub.api.webhooks.stripe.abstract import AbstractStripeWebhookEvent
from subhub.api.webhooks.routes.static import StaticRoutes

logger = logging.getLogger("invoice")
log_handle = logging.StreamHandler()
log_handle.setLevel(logging.INFO)
logformat = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log_handle.setFormatter(logformat)
logger.addHandler(log_handle)


class StripeInvoiceFinalized(AbstractStripeWebhookEvent):
    def run(self):
        d = self.payload
        sfd = {}

        sfd["event_id"] = d["id"]
        sfd["event_type"] = d["type"]
        sfd["customer_id"] = d["data"]["object"]["customer"]
        sfd["created"] = d["data"]["object"]["created"]
        sfd["subscription_id"] = d["data"]["object"]["subscription"]
        sfd["period_end"] = d["data"]["object"]["period_end"]
        sfd["period_start"] = d["data"]["object"]["period_start"]
        sfd["amount_paid"] = d["data"]["object"]["amount_paid"]
        sfd["currency"] = d["data"]["object"]["currency"]
        sfd["charge"] = d["data"]["object"]["charge"]
        sfd["invoice_number"] = d["data"]["object"]["number"]
        sfd["description"] = d["data"]["object"]["lines"]["data"][0]["description"]
        sfd["application_fee_amount"] = d["data"]["object"]["application_fee_amount"]
        sfd["invoice_id"] = d["data"]["object"]["id"]

        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(sfd))


class StripeInvoicePaymentFailed(AbstractStripeWebhookEvent):
    def run(self):
        d = self.payload
        sfd = {}

        sfd["event_id"] = d["id"]
        sfd["event_type"] = d["type"]
        sfd["customer_id"] = d["data"]["object"]["customer"]
        sfd["subscription_id"] = d["data"]["object"]["subscription"]
        sfd["number"] = d["data"]["object"]["number"]
        sfd["amount_due"] = d["data"]["object"]["amount_due"]
        sfd["created"] = d["data"]["object"]["created"]
        sfd["currency"] = d["data"]["object"]["currency"]
        sfd["charge"] = d["data"]["object"]["charge"]

        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(sfd))
