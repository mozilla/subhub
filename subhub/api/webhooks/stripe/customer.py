import logging
import json

from attrdict import AttrDict
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
        data = self.create_data(
            email=self.payload.data.object.email,
            customer_id=self.payload.data.object.id,
            name=self.payload.data.object.name,
            user_id=self.payload.data.object.metadata.userid,
        )
        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(data))


class StripeCustomerDeleted(AbstractStripeWebhookEvent):
    def run(self):
        data = self.create_data(
            email=self.payload.data.object.email,
            customer_id=self.payload.data.object.id,
            name=self.payload.data.object.name,
            user_id=self.payload.data.object.metadata.userid,
        )
        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(data))


class StripeCustomerUpdated(AbstractStripeWebhookEvent):
    def run(self):
        data = self.create_data(
            email=self.payload.data.object.email,
            customer_id=self.payload.data.object.id,
            name=self.payload.data.object.name,
        )
        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(data))


class StripeCustomerSourceExpiring(AbstractStripeWebhookEvent):
    def run(self):
        data = self.create_data(
            customer_id=self.payload.data.object.customer,
            last4=self.payload.data.object.last4,
            brand=self.payload.data.object.brand,
            exp_month=self.payload.data.object.exp_month,
            exp_year=self.payload.data.object.exp_year,
        )
        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(data))


class StripeCustomerSubscriptionCreated(AbstractStripeWebhookEvent):
    def run(self):
        data = {
            "event_id": self.payload.id,
            "event_type": self.payload.type,
            "customer_id": self.payload.data.object.customer,
            "subscription_id": self.payload.data.object.id,
            "current_period_start": self.payload.data.object.current_period_start,
            "current_period_end": self.payload.data.object.current_period_end,
            "canceled_at": self.payload.data.object.canceled_at,
            "days_until_due": self.payload.data.object.days_until_due,
            "default_payment_method": self.payload.data.object.default_payment_method,
            "plan_id": self.payload.data.object.plan.id,
            "plan_amount": self.payload.data.object.plan.amount,
            "plan_currency": self.payload.data.object.plan.currency,
            "plan_interval": self.payload.data.object.plan.interval,
            "status": self.payload.data.object.status,
            "trial_start": self.payload.data.object.trial_start,
            "trial_end": self.payload.data.object.trial_end,
            "tax_percent": self.payload.data.object.tax_percent,
            "application_fee_percent": self.payload.data.object.application_fee_percent,
            "user_id": self.payload.data.object.metadata.get("userid", None),  # why?
        }
        routes = [StaticRoutes.SALESFORCE_ROUTE, StaticRoutes.FIREFOX_ROUTE]
        self.send_to_routes(routes, json.dumps(data))


class StripeCustomerSubscriptionDeleted(AbstractStripeWebhookEvent):
    def run(self):
        # items is a keyword in the attrdict; this steps around that
        items = AttrDict(self.payload.data.object["items"])
        data = {
            "event_id": self.payload.id,
            "event_type": self.payload.type,
            "customer_id": self.payload.data.object.customer,
            "subscription_id": self.payload.data.object.id,
            "current_period_start": self.payload.data.object.current_period_start,
            "current_period_end": self.payload.data.object.current_period_end,
            "subscription_created": items.data[0].created,
            "plan_amount": self.payload.data.object.plan.amount,
            "plan_currency": self.payload.data.object.plan.currency,
            "plan_name": self.payload.data.object.plan.nickname,
            "trial_period_days": self.payload.data.object.plan.trial_period_days,
            "status": self.payload.data.object.status,
            "canceled_at": self.payload.data.object.canceled_at,
            "created": self.payload.data.object.created,
        }
        routes = [StaticRoutes.SALESFORCE_ROUTE, StaticRoutes.FIREFOX_ROUTE]
        self.send_to_routes(routes, json.dumps(data))


class StripeCustomerSubscriptionUpdated(AbstractStripeWebhookEvent):
    def run(self):
        if self.payload.data.object.cancel_at_period_end:
            data = self.create_data(
                customer_id=self.payload.data.object.customer,
                subscription_id=self.payload.data.object.id,
                plan_amount=self.payload.data.object.plan.amount,
                canceled_at=self.payload.data.object.canceled_at,
                cancel_at=self.payload.data.object.cancel_at,
                cancel_at_period_end=self.payload.data.object.cancel_at_period_end,
            )
            routes = [StaticRoutes.SALESFORCE_ROUTE]
            self.send_to_routes(routes, json.dumps(data))
        else:
            logger.info(
                f"cancel_at_period_end {self.payload.data.object.cancel_at_period_end}"
            )
