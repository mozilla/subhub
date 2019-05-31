import logging
import json

from subhub.api.webhooks.stripe.abstract import AbstractStripeWebhookEvent
from subhub.api.webhooks.routes.static import StaticRoutes

logger = logging.getLogger("subscription.created")
log_handle = logging.StreamHandler()
log_handle.setLevel(logging.INFO)
logformat = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log_handle.setFormatter(logformat)
logger.addHandler(log_handle)


class StripeSubscriptionCreated(AbstractStripeWebhookEvent):
    def run(self):
        d = self.payload
        sfd = {}

        sfd["event_id"] = d["id"]
        sfd["event_type"] = d["type"]
        sfd["customer_id"] = d["data"]["object"]["id"]
        sfd["created"] = d["data"]["object"]["created"]
        sfd["subscription_created"] = d["data"]["items"]["data"][0]["created"]
        sfd["current_period_start"] = d["data"]["current_period_start"]
        sfd["current_period_end"] = d["data"]["current_period_end"]
        sfd["plan_amount"] = d["data"]["plan"]["amount"]
        sfd["plan_currency"] = d["data"]["plan"]["currency"]
        sfd["plan_name"] = d["data"]["plan"]["nickname"]

        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(sfd))
