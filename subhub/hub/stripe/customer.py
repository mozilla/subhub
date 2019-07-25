#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import time
from datetime import datetime

import stripe
from stripe.error import InvalidRequestError

from subhub.hub.stripe.abstract import AbstractStripeHubEvent
from subhub.hub.routes.static import StaticRoutes
from subhub.exceptions import ClientError

from subhub.log import get_logger

logger = get_logger()


class StripeCustomerCreated(AbstractStripeHubEvent):
    def run(self):
        logger.info("customer created", payload=self.payload)
        cust_name = self.payload.data.object.name
        if not cust_name:
            cust_name = ""
        data = self.create_data(
            email=self.payload.data.object.email,
            customer_id=self.payload.data.object.id,
            name=cust_name,
            user_id=self.payload.data.object.metadata.get("userid", None),
        )
        logger.info("customer created", data=data)
        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(data))


class StripeCustomerDeleted(AbstractStripeHubEvent):
    def run(self):
        logger.info("customer deleted", payload=self.payload)
        cust_name = self.payload.data.object.name
        if not cust_name:
            cust_name = ""
        data = self.create_data(
            email=self.payload.data.object.email,
            customer_id=self.payload.data.object.id,
            name=cust_name,
            user_id=self.payload.data.object.metadata.get("userid", None),
        )
        logger.info("customer deleted", data=data)
        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(data))


class StripeCustomerUpdated(AbstractStripeHubEvent):
    def run(self):
        logger.info("customer updated", payload=self.payload)
        cust_name = self.payload.data.object.name
        if not cust_name:
            cust_name = ""
        data = self.create_data(
            email=self.payload.data.object.email,
            customer_id=self.payload.data.object.id,
            name=cust_name,
        )
        logger.info("customer updated", data=data)
        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(data))


class StripeCustomerSourceExpiring(AbstractStripeHubEvent):
    def run(self):
        try:
            logger.info("customer source expiring")
            customer_id = self.payload.data.object.customer
            updated_customer = stripe.Customer.retrieve(id=customer_id)
            email = updated_customer.email
            nicknames = list()
            for subs in updated_customer.subscriptions["data"]:
                if subs["status"] in ["active", "trialing"]:
                    nicknames.append(subs["plan"]["nickname"])
            data = self.create_data(
                email=email,
                nickname=nicknames[0],
                customer_id=self.payload.data.object.customer,
                last4=self.payload.data.object.last4,
                brand=self.payload.data.object.brand,
                exp_month=self.payload.data.object.exp_month,
                exp_year=self.payload.data.object.exp_year,
            )
            routes = [StaticRoutes.SALESFORCE_ROUTE]
            self.send_to_routes(routes, json.dumps(data))
        except InvalidRequestError as e:
            logger.error("Unable to find customer", error=e)
            raise InvalidRequestError(message="Unable to find customer", param=str(e))


class StripeCustomerSubscriptionCreated(AbstractStripeHubEvent):
    def run(self):
        logger.info("customer subscription created", payload=self.payload)
        try:
            customer_id = self.payload.data.object.customer
            updated_customer = stripe.Customer.retrieve(id=customer_id)
            user_id = updated_customer.metadata.get("userid")
        except InvalidRequestError as e:
            logger.error("Unable to find customer", error=e)
            raise InvalidRequestError(message="Unable to find customer", param=str(e))
        if user_id:
            data = self.create_data(
                uid=user_id,
                active=self.is_active_or_trialing,
                subscriptionId=self.payload.data.object.id,
                subscription_id=self.payload.data.object.id,
                productName=self.payload.data.object.plan.nickname,
                eventId=self.payload.id,  # required by FxA
                eventCreatedAt=self.payload.created,  # required by FxA
                messageCreatedAt=int(time.time()),  # required by FxA
                invoice_id=self.payload.data.object.latest_invoice,
                plan_amount=self.payload.data.object.plan.amount,
                customer_id=self.payload.data.object.customer,
                nickname=self.payload.data.object.plan.nickname,
                created=self.payload.data.object.plan.created,
                canceled_at=self.payload.data.object.canceled_at,
                cancel_at=self.payload.data.object.cancel_at,
                cancel_at_period_end=self.payload.data.object.cancel_at_period_end,
            )
            logger.info("customer subscription created", data=data)
            routes = [StaticRoutes.FIREFOX_ROUTE, StaticRoutes.SALESFORCE_ROUTE]
            self.send_to_routes(routes, json.dumps(data))
        else:
            logger.error(
                "customer subscription created no userid",
                error=self.payload.object.customer,
                user_id=user_id,
            )
            raise ClientError(
                f"userid is None for customer {self.payload.object.customer}"
            )


class StripeCustomerSubscriptionDeleted(AbstractStripeHubEvent):
    def run(self):
        logger.info("customer subscription deleted", payload=self.payload)
        try:
            customer_id = self.payload.data.object.customer
            updated_customer = stripe.Customer.retrieve(id=customer_id)
            user_id = updated_customer.metadata.get("userid")
        except InvalidRequestError as e:
            logger.error("Unable to find customer", error=e)
            raise InvalidRequestError(message="Unable to find customer", param=str(e))
        if user_id:
            data = dict(
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
            logger.error(
                "customer subscription deleted no userid",
                error=self.payload.object.customer,
                user_id=user_id,
            )
            raise ClientError(
                f"userid is None for customer {self.payload.object.customer}"
            )


class StripeCustomerSubscriptionUpdated(AbstractStripeHubEvent):
    def run(self):
        logger.info("customer subscription updated", payload=self.payload)
        try:
            customer_id = self.payload.data.object.customer
            updated_customer = stripe.Customer.retrieve(id=customer_id)
            user_id = updated_customer.metadata.get("userid")
        except InvalidRequestError as e:
            logger.error("Unable to find customer", error=e)
            raise InvalidRequestError(message="Unable to find customer", param=str(e))
        if user_id:
            previous_attributes = dict()
            try:
                previous_attributes = self.payload.data.previous_attributes
            except AttributeError:
                logger.error("no previous attributes", data=self.payload.data)
            logger.info("previous attributes", previous_attributes=previous_attributes)
            logger.info(
                "previous cancel",
                previous_cancel=previous_attributes.get("cancel_at_period_end"),
            )
            if self.payload.data.object.cancel_at_period_end:
                logger.info(
                    "cancel at period end",
                    end=self.payload.data.object.cancel_at_period_end,
                )
                data = self.create_data(
                    uid=user_id,
                    customer_id=self.payload.data.object.customer,
                    subscriptionId=self.payload.data.object.id,  # required by FxA
                    subscription_id=self.payload.data.object.id,
                    plan_amount=self.payload.data.object.plan.amount,
                    canceled_at=self.payload.data.object.canceled_at,
                    cancel_at=self.payload.data.object.cancel_at,
                    cancel_at_period_end=self.payload.data.object.cancel_at_period_end,
                    nickname=self.payload.data.object.plan.nickname,
                    messageCreatedAt=int(time.time()),  # required by FxA
                    invoice_id=self.payload.data.object.latest_invoice,
                    eventId=self.payload.id,  # required by FxA
                )
                logger.info("customer subscription cancel at period end", data=data)
                routes = [StaticRoutes.FIREFOX_ROUTE, StaticRoutes.SALESFORCE_ROUTE]
                self.send_to_routes(routes, json.dumps(data))
            elif (
                not self.payload.data.object.cancel_at_period_end
                and self.payload.data.object.status == "active"
                and not previous_attributes.get("cancel_at_period_end")
            ):
                data = self.create_data(
                    uid=user_id,
                    active=self.is_active_or_trialing,
                    subscriptionId=self.payload.data.object.id,  # required by FxA
                    subscription_id=self.payload.data.object.id,
                    productName=self.payload.data.object.plan.nickname,
                    nickname=self.payload.data.object.plan.nickname,
                    eventCreatedAt=self.payload.created,  # required by FxA
                    messageCreatedAt=int(time.time()),  # required by FxA
                    invoice_id=self.payload.data.object.latest_invoice,
                    customer_id=self.payload.data.object.customer,
                    created=self.payload.data.object.plan.created,
                    plan_amount=self.payload.data.object.plan.amount,
                    eventId=self.payload.id,  # required by FxA
                    canceled_at=self.payload.data.object.canceled_at,
                    cancel_at=self.payload.data.object.cancel_at,
                    cancel_at_period_end=self.payload.data.object.cancel_at_period_end,
                )
                logger.info("customer subscription new recurring", data=data)
                routes = [StaticRoutes.FIREFOX_ROUTE, StaticRoutes.SALESFORCE_ROUTE]
                self.send_to_routes(routes, json.dumps(data))
            else:
                logger.info(
                    "cancel_at_period_end false",
                    data=self.payload.data.object.cancel_at_period_end,
                )
        else:
            logger.error(
                "customer subscription updated - no userid",
                error=self.payload.object.customer,
            )
            raise ClientError(
                f"userid is None for customer {self.payload.object.customer}"
            )
