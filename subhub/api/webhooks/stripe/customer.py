import logging
import json

from subhub.api.webhooks.stripe.abstract import AbstractStripeWebhookEvent
from subhub.api.webhooks.routes.static import StaticRoutes

logger = logging.getLogger("customer.created")
log_handle = logging.StreamHandler()
log_handle.setLevel(logging.INFO)
logformat = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log_handle.setFormatter(logformat)
logger.addHandler(log_handle)


class StripeCustomerCreated(AbstractStripeWebhookEvent):
    def run(self):
        print(f"customer created: {self.payload}")
        d = self.payload
        sfd = {}
        sfd["event_id"] = d["id"]
        sfd["event_type"] = "customer_created"
        sfd["email"] = d["data"]["object"]["email"]
        sfd["stripe_id"] = d["data"]["object"]["id"]
        sfd["name"] = d["data"]["object"]["name"]
        user_id = d["data"]["object"]["metadata"].get("userid")
        sfd["user_id"] = user_id

        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(sfd))


class StripeCustomerDeleted(AbstractStripeWebhookEvent):
    def run(self):
        d = self.payload
        sfd = {}
        sfd["event_id"] = d["id"]
        sfd["event_type"] = d["type"]
        sfd["email"] = d["data"]["object"]["email"]
        sfd["stripe_id"] = d["data"]["object"]["id"]
        sfd["name"] = d["data"]["object"]["name"]
        user_id = d["data"]["object"]["metadata"].get("userid")
        sfd["user_id"] = user_id

        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(sfd))


class StripeCustomerSourceExpiring(AbstractStripeWebhookEvent):
    def run(self):
        print(f"customer source expiring: {self.payload}")
        d = self.payload
        sfd = {}
        sfd["event_id"] = d["id"]
        sfd["event_type"] = "customer_source_expiring"
        sfd["stripe_id"] = d["data"]["object"]["customer"]

        routes = [
            StaticRoutes.SALESFORCE_ROUTE
        ]  # setup not complete StaticRoutes.FIREFOX_ROUTE,
        self.send_to_routes(routes, json.dumps(sfd))


class StripeCustomerSubscriptionCreated(AbstractStripeWebhookEvent):
    def run(self):
        d = self.payload
        sfd = {}
        sfd["event_id"] = d["id"]
        sfd["event_type"] = d["type"]
        sfd["stripe_id"] = d["data"]["object"]["id"]
        sfd["customer_id"] = d["data"]["object"]["customer"]
        sfd["current_period_start"] = d["data"]["object"]["current_period_start"]
        sfd["current_period_end"] = d["data"]["object"]["current_period_end"]
        sfd["canceled_at"] = d["data"]["object"]["canceled_at"]
        sfd["days_until_due"] = d["data"]["object"]["days_until_due"]
        sfd["default_payment_method"] = d["data"]["object"]["default_payment_method"]
        sfd["plan_id"] = d["data"]["object"]["plan"]["id"]
        sfd["plan_amount"] = d["data"]["object"]["plan"]["amount"]
        sfd["plan_currency"] = d["data"]["object"]["plan"]["currency"]
        sfd["plan_interval"] = d["data"]["object"]["plan"]["interval"]
        sfd["status"] = d["data"]["object"]["status"]
        sfd["trial_start"] = d["data"]["object"]["trial_start"]
        sfd["trial_end"] = d["data"]["object"]["trial_end"]
        sfd["tax_percent"] = d["data"]["object"]["tax_percent"]
        sfd["application_fee_percent"] = d["data"]["object"]["application_fee_percent"]
        user_id = d["data"]["object"]["metadata"].get("userid")
        sfd["user_id"] = user_id

        routes = [StaticRoutes.SALESFORCE_ROUTE, StaticRoutes.FIREFOX_ROUTE]
        self.send_to_routes(routes, json.dumps(sfd))


class StripeCustomerSubscriptionDeleted(AbstractStripeWebhookEvent):
    def run(self):
        d = self.payload
        sfd = {}
        sfd["event_id"] = d["id"]
        sfd["event_type"] = "customer_subscription_deleted"
        sfd["stripe_id"] = d["data"]["object"]["customer"]
        sfd["created"] = d["data"]["object"]["created"]
        sfd["subscription_created"] = d["data"]["object"]["items"]["data"][0]["created"]
        sfd["current_period_start"] = d["data"]["object"]["current_period_start"]
        sfd["current_period_end"] = d["data"]["object"]["current_period_end"]
        sfd["plan_amount"] = d["data"]["object"]["plan"]["amount"]
        sfd["plan_currency"] = d["data"]["object"]["plan"]["currency"]
        sfd["plan_name"] = d["data"]["object"]["plan"]["nickname"]
        sfd["trial_period_days"]: d["data"]["object"]["plan"]["trial_period_days"]
        sfd["status"]: d["data"]["object"]["status"]

        routes = [StaticRoutes.SALESFORCE_ROUTE, StaticRoutes.FIREFOX_ROUTE]
        self.send_to_routes(routes, json.dumps(sfd))


class StripeCustomerSubscriptionUpdated(AbstractStripeWebhookEvent):
    def run(self):
        d = self.payload
        sfd = {}
        sfd["event_id"] = d["id"]
        sfd["event_type"] = "customer_subscription_updated"
        sfd["stripe_id"] = d["data"]["object"]["customer"]
        sfd["created"] = d["data"]["object"]["created"]
        sfd["subscription_created"] = d["data"]["object"]["items"]["data"][0]["created"]
        sfd["current_period_start"] = d["data"]["object"]["current_period_start"]
        sfd["current_period_end"] = d["data"]["object"]["current_period_end"]
        sfd["plan_amount"] = d["data"]["object"]["plan"]["amount"]
        sfd["plan_currency"] = d["data"]["object"]["plan"]["currency"]
        sfd["plan_name"] = d["data"]["object"]["plan"]["nickname"]
        sfd["trial_period_days"]: d["data"]["object"]["plan"]["trial_period_days"]
        sfd["status"]: d["data"]["object"]["status"]

        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(sfd))


class StripeCustomerUpdated(AbstractStripeWebhookEvent):
    def run(self):
        print(f"customer updated: {self.payload}")
        d = self.payload
        sfd = {}

        sfd["event_id"] = d["id"]
        sfd["event_type"] = d["type"]
        sfd["email"] = d["data"]["object"]["email"]
        sfd["stripe_id"] = d["data"]["object"]["id"]
        sfd["name"] = d["data"]["object"]["name"]

        routes = [
            StaticRoutes.SALESFORCE_ROUTE
        ]  # setup not complete StaticRoutes.FIREFOX_ROUTE,
        self.send_to_routes(routes, json.dumps(sfd))
