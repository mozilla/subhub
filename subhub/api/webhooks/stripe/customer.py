import json
import time

import stripe

from subhub.api.webhooks.stripe.abstract import AbstractStripeWebhookEvent
from subhub.api.webhooks.routes.static import StaticRoutes
from subhub.exceptions import ClientError

from subhub.log import get_logger

logger = get_logger()


class StripeCustomerCreated(AbstractStripeWebhookEvent):
    def run(self):
        cust_name = self.payload.data.object.name
        if not cust_name:
            cust_name = " "
        data = self.create_data(
            email=self.payload.data.object.email,
            customer_id=self.payload.data.object.id,
            name=cust_name,
            user_id=self.payload.data.object.metadata.get("userid", None),
        )
        logger.info("customer created", data=data)
        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(data))


class StripeCustomerDeleted(AbstractStripeWebhookEvent):
    def run(self):
        cust_name = self.payload.data.object.name
        if not cust_name:
            cust_name = " "
        data = self.create_data(
            email=self.payload.data.object.email,
            customer_id=self.payload.data.object.id,
            name=cust_name,
            user_id=self.payload.data.object.metadata.get("userid", None),
        )
        logger.info("customer deleted", data=data)
        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(data))


class StripeCustomerUpdated(AbstractStripeWebhookEvent):
    def run(self):
        cust_name = self.payload.data.object.name
        if not cust_name:
            cust_name = " "
        data = self.create_data(
            email=self.payload.data.object.email,
            customer_id=self.payload.data.object.id,
            name=cust_name,
        )
        logger.info("customer updated", data=data)
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
        user_id = self.payload.data.object.metadata.get("userid", None)
        updated_customer = ""
        if not user_id:
            customer_id = self.payload.data.object.customer
            updated_customer = stripe.Customer.retrieve(customer_id)
            user_id = updated_customer.metadata.get("userid")
        if user_id:
            data = dict(
                uid=user_id,
                active=self.is_active_or_trialing,
                subscriptionId=self.payload.data.object.id,
                productName=self.payload.data.object.plan.nickname,
                eventId=self.payload.id,  # required by FxA
                event_id=self.payload.id,  # required by SubHub
                eventCreatedAt=self.payload.created,
                messageCreatedAt=int(time.time()),
            )
            logger.info("customer subscription created", data=data)
            routes = [StaticRoutes.FIREFOX_ROUTE]
            self.send_to_routes(routes, json.dumps(data))
        else:
            raise ClientError(f"userid is None for customer {updated_customer}")


class StripeCustomerSubscriptionDeleted(AbstractStripeWebhookEvent):
    def run(self):
        user_id = self.payload.data.object.metadata.get("userid", None)
        if not user_id:
            customer_id = self.payload.data.object.customer
            updated_customer = stripe.Customer.retrieve(customer_id)
            user_id = updated_customer.metadata.get("userid")
        if user_id:
            data = dict(
                uid=user_id,
                active=self.is_active_or_trialing,
                subscriptionId=self.payload.data.object.id,
                productName=self.payload.data.object.plan.nickname,
                eventId=self.payload.id,  # required by FxA
                event_id=self.payload.id,  # required by SubHub
                eventCreatedAt=self.payload.created,
                messageCreatedAt=int(time.time()),
            )
            logger.info("customer subscription deleted", data=data)
            routes = [StaticRoutes.FIREFOX_ROUTE]
            self.send_to_routes(routes, json.dumps(data))
        else:
            raise ClientError(
                f"userid is None for customer {self.payload.object.customer}"
            )


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
            logger.info("customer subscription updated", data=data)
            routes = [StaticRoutes.SALESFORCE_ROUTE]
            self.send_to_routes(routes, json.dumps(data))
        else:
            logger.info(
                "cancel_at_period_end",
                data=self.payload.data.object.cancel_at_period_end,
            )
