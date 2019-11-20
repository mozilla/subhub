# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import time
import stripe

from stripe.error import InvalidRequestError
from datetime import datetime
from typing import Optional, Dict, Any
from flask import g

from vendor.abstract import AbstractStripeHubEvent
from routes.static import StaticRoutes
from src.shared.exceptions import ClientError
from src.shared.utils import format_plan_nickname
from src.shared.log import get_logger
from src.shared import vendor
from src.shared.db import SubHubDeletedAccountModel

logger = get_logger()


class StripeCustomerCreated(AbstractStripeHubEvent):
    def run(self) -> bool:
        """
        Parse the event data sent by Stripe contained within self.payload
        :return True to indicate successfully sent
        """
        logger.info("customer created", payload=self.payload)
        data = self.create_payload()
        logger.info("customer created", data=data)
        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(data))
        return True

    def create_payload(self) -> Dict[str, Any]:
        """
        Create payload to be sent to external sources
        :return:
        """
        cust_name = self.payload.data.object.name
        if not cust_name:
            cust_name = ""
        return self.create_data(
            email=self.payload.data.object.email,
            customer_id=self.payload.data.object.id,
            name=cust_name,
            user_id=self.payload.data.object.metadata.get("userid", None),
        )


class StripeCustomerDeleted(AbstractStripeHubEvent):
    def run(self) -> bool:
        """
        Parse the event data sent by Stripe contained within self.payload
        :return True to indicate successfully sent
        """
        logger.info("customer deleted", payload=self.payload)
        deleted_user = self.get_deleted_user()
        data = self.create_payload(deleted_user)
        logger.info("customer delete", data=data)
        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(data))
        return True

    def get_deleted_user(self) -> SubHubDeletedAccountModel:
        """
        Fetch a deleted user based off of key data within payload
        Raise error if user cannot be fetched or does not exist
        :return:
        :raises ClientError
        """
        try:
            customer_id = self.payload.data.object.id
            uid = self.payload.data.object.metadata.userid
        except AttributeError as e:
            logger.error(
                "customer deleted - unable to get lookup data from payload", error=e
            )
            raise ClientError(
                f"subhub_deleted_user could not be fetched - missing keys"
            )

        deleted_user = g.subhub_deleted_users.get_user(uid, customer_id)
        if deleted_user is None:
            logger.error(
                "customer deleted - subhub deleted user not found",
                customer_id=customer_id,
                user_id=uid,
            )
            raise ClientError(
                f"subhub_deleted_user is None for customer {customer_id} and user {uid}"
            )

        return deleted_user

    def create_payload(self, deleted_user) -> Dict[str, Any]:
        """
        Create payload to be sent to external sources
        :param deleted_user:
        :return:
        """
        plan_amount = 0
        current_period_end = None
        current_period_start = None
        nicknames = list()
        for user_plan in deleted_user.subscription_info:
            plan_amount = plan_amount + user_plan["plan_amount"]
            nicknames.append(user_plan["nickname"])
            current_period_start = user_plan["current_period_start"]
            current_period_end = user_plan["current_period_end"]
        subs = ",".join(
            [(x.get("subscription_id")) for x in deleted_user.subscription_info]
        )

        return self.create_data(
            created=self.payload.data.object.created,
            customer_id=self.payload.data.object.id,
            plan_amount=plan_amount,
            nickname=nicknames,
            subscription_id=subs,
            subscriptionId=subs,  # required by FxA
            current_period_end=current_period_end,
            current_period_start=current_period_start,
            uid=self.payload.data.object.metadata.userid,  # required by FxA
            eventCreatedAt=self.payload.created,  # required by FxA
            messageCreatedAt=int(time.time()),  # required by FxA
            eventId=self.payload.id,  # required by FxA
        )


class StripeCustomerSourceExpiring(AbstractStripeHubEvent):
    def run(self) -> bool:
        """
        Parse the event data sent by Stripe contained within self.payload
        :return True to indicate successfully sent
        """
        try:
            logger.info("customer source expiring")
            customer_id = self.payload.data.object.customer
            customer = vendor.retrieve_stripe_customer(customer_id)
        except InvalidRequestError as e:
            logger.error("Unable to find customer", error=e)
            raise e

        data = self.create_payload(customer)
        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(data))
        return True

    def create_payload(self, customer) -> Dict[str, Any]:
        """
        Create payload to be sent to external sources
        :param customer:
        :return:
        """
        email = customer.email
        plan_nickname = self.first_plan_name(customer.subscriptions["data"])
        return self.create_data(
            email=email,
            nickname=plan_nickname,
            customer_id=self.payload.data.object.customer,
            last4=self.payload.data.object.last4,
            brand=self.payload.data.object.brand,
            exp_month=self.payload.data.object.exp_month,
            exp_year=self.payload.data.object.exp_year,
        )

    def first_plan_name(self, subscriptions) -> str:
        """
        Get the plan name to return in the payload
        :param subscriptions:
        :return:
        """
        name = ""
        for subscription in subscriptions:
            if subscription["status"] in ["active", "trialing"]:
                product = vendor.retrieve_stripe_product(
                    subscription["plan"]["product"]
                )

                name = format_plan_nickname(
                    product_name=product["name"],
                    plan_interval=subscription["plan"]["interval"],
                )
                break

        return name


class StripeCustomerSubscriptionCreated(AbstractStripeHubEvent):
    def run(self) -> bool:
        """
        Parse the event data sent by Stripe contained within self.payload
        :return True to indicate successfully sent
        """
        logger.info("customer subscription created", payload=self.payload)
        customer_id = self.payload.data.object.customer
        user_id = self.get_user_id(customer_id)

        data: Dict[str, Any] = self.create_payload(user_id)

        # NOTE:
        # Firefox's route has a particular casing requirement
        # Salesforce's route doesn't care.
        data_projection_by_route: Dict[str, Any] = {
            StaticRoutes.FIREFOX_ROUTE: [
                "uid",
                "active",
                "subscriptionId",
                "productId",
                "eventId",
                "eventCreatedAt",
                "messageCreatedAt",
            ],
            StaticRoutes.SALESFORCE_ROUTE: data.keys(),
        }
        self.customer_event_to_all_routes(data_projection_by_route, data)
        logger.info("customer subscription created", data=data)
        return True

    def get_user_id(self, customer_id) -> str:
        """
        Fetch the user_id associated with the Stripe customer_id
        :param customer_id:
        :return user_id:
        :raises InvalidRequestError
        :raises ClientError
        """
        try:
            customer = vendor.retrieve_stripe_customer(customer_id=customer_id)
        except InvalidRequestError as e:
            logger.error("Unable to find customer", error=e)
            raise e

        deleted = customer.get("deleted", False)
        user_id = None
        if not deleted:
            user_id = customer.metadata.get("userid")

        if user_id is None:
            logger.error(
                "customer subscription created - no userid",
                error=customer_id,
                is_customer_deleted=deleted,
            )
            raise ClientError(f"userid is None for customer {customer_id}")

        return user_id

    def create_payload(self, user_id) -> Dict[str, Any]:
        """
        Create payload to be sent to external sources
        :param user_id:
        :return:
        """
        try:
            invoice_id = self.payload.data.object.latest_invoice
            latest_invoice = vendor.retrieve_stripe_invoice(invoice_id)
            invoice_number = latest_invoice.number
            charge_id = latest_invoice.charge
            latest_charge = vendor.retrieve_stripe_charge(charge_id)
            last4 = latest_charge.payment_method_details.card.last4
            brand = latest_charge.payment_method_details.card.brand

            logger.info("latest invoice", latest_invoice=latest_invoice)
            logger.info("latest charge", latest_charge=latest_charge)

            product = vendor.retrieve_stripe_product(
                self.payload.data.object.plan.product
            )
            product_name = product["name"]
            product_id = product["id"]

            plan_nickname = format_plan_nickname(
                product_name=product_name,
                plan_interval=self.payload.data.object.plan.interval,
            )

            return self.create_data(
                uid=user_id,
                active=self.is_active_or_trialing,
                subscriptionId=self.payload.data.object.id,  # required by FxA
                subscription_id=self.payload.data.object.id,
                productName=product_name,
                productId=product_id,
                eventId=self.payload.id,  # required by FxA
                eventCreatedAt=self.payload.created,  # required by FxA
                messageCreatedAt=int(time.time()),  # required by FxA
                invoice_id=self.payload.data.object.latest_invoice,
                plan_amount=self.payload.data.object.plan.amount,
                customer_id=self.payload.data.object.customer,
                nickname=plan_nickname,
                created=self.payload.data.object.created,
                canceled_at=self.payload.data.object.canceled_at,
                cancel_at=self.payload.data.object.cancel_at,
                cancel_at_period_end=self.payload.data.object.cancel_at_period_end,
                currency=self.payload.data.object.plan.currency,
                current_period_start=self.payload.data.object.current_period_start,
                current_period_end=self.payload.data.object.current_period_end,
                invoice_number=invoice_number,
                brand=brand,
                last4=last4,
                charge=charge_id,
            )
        except InvalidRequestError as e:
            logger.error("Unable to gather subscription create data", error=e)
            raise e


class StripeCustomerSubscriptionDeleted(AbstractStripeHubEvent):
    def run(self) -> bool:
        """
        Parse the event data sent by Stripe contained within self.payload
        :return True to indicate successfully sent
        """
        logger.info("customer subscription deleted", payload=self.payload)
        customer_id = self.payload.data.object.customer
        user_id = self.get_user_id(customer_id)

        data = self.create_payload(user_id)
        routes = [StaticRoutes.FIREFOX_ROUTE]
        self.send_to_routes(routes, json.dumps(data))
        return True

    def get_user_id(self, customer_id) -> str:
        """
        Fetch the user_id associated with the Stripe customer_id
        :param customer_id:
        :return user_id:
        :raises InvalidRequestError
        :raises ClientError
        """
        try:
            customer = vendor.retrieve_stripe_customer(customer_id=customer_id)

        except InvalidRequestError as e:
            logger.error("Unable to find customer", error=e)
            raise e

        deleted = customer.get("deleted", False)
        user_id = None
        if not deleted:
            user_id = customer.metadata.get("userid")

        if user_id is None:
            logger.error(
                "customer subscription deleted - no userid",
                error=customer_id,
                is_customer_deleted=deleted,
            )
            raise ClientError(f"userid is None for customer {customer_id}")

        return user_id

    def create_payload(self, user_id) -> Dict[str, Any]:
        """
        Create payload to be sent to external sources
        :return payload:
        """
        return dict(
            uid=user_id,
            active=self.is_active_or_trialing,
            subscriptionId=self.payload.data.object.id,
            productId=self.payload.data.object.plan.product,
            eventId=self.payload.id,
            eventCreatedAt=self.payload.created,
            messageCreatedAt=int(time.time()),
        )


class StripeCustomerSubscriptionUpdated(AbstractStripeHubEvent):
    def run(self) -> bool:
        """
        Parse the event data sent by Stripe contained within self.payload
        Evaluate the data to determine if it should be sent to external routes
        if data should be sent:
            Prepare data for source
            Send to selected routes
            :return True:
        else
            :return False:
        """
        logger.info("customer subscription updated", payload=self.payload)

        customer_id = self.payload.data.object.customer
        user_id = self.get_user_id(customer_id)

        current_cancel_at_period_end = self.payload.data.object.cancel_at_period_end

        previous_attributes = self.payload.data.previous_attributes
        previous_cancel_at_period_end = previous_attributes.get(
            "cancel_at_period_end", False
        )

        data = None
        routes = None
        if current_cancel_at_period_end and not previous_cancel_at_period_end:
            data = self.create_payload("customer.subscription_cancelled", user_id)
            logger.info("customer subscription cancel at period end", data=data)
            routes = [StaticRoutes.SALESFORCE_ROUTE]
        elif (
            not current_cancel_at_period_end
            and not previous_cancel_at_period_end
            and self.payload.data.object.status == "active"
        ):
            data = self.create_payload("customer.recurring_charge", user_id)
            logger.info("customer subscription new recurring", data=data)
            routes = [StaticRoutes.SALESFORCE_ROUTE]
        elif not current_cancel_at_period_end and previous_cancel_at_period_end:
            data = self.create_payload("customer.subscription.reactivated", user_id)
            logger.info("customer subscription reactivated", data=data)
            routes = [StaticRoutes.SALESFORCE_ROUTE]

        if data is not None and routes is not None:
            self.send_to_routes(routes, json.dumps(data))
            return True

        logger.info("Conditions not met to send data to external routes")
        return False

    def get_user_id(self, customer_id) -> str:
        """
        Fetch the user_id associated with the Stripe customer_id
        :param customer_id:
        :return user_id:
        :raises InvalidRequestError
        :raises ClientError
        """
        try:
            customer = vendor.retrieve_stripe_customer(customer_id=customer_id)
        except InvalidRequestError as e:
            logger.error("Unable to find customer", error=e)
            raise e

        deleted = customer.get("deleted", False)
        user_id = None
        if not deleted:
            user_id = customer.metadata.get("userid")

        if user_id is None:
            logger.error(
                "customer subscription updated - no userid",
                error=customer_id,
                is_customer_deleted=deleted,
            )
            raise ClientError(f"userid is None for customer {customer_id}")

        return user_id

    def create_payload(self, event_type, user_id) -> Dict[str, Any]:
        """
        Create payload to be sent to external sources based on event_type
        :param event_type:
        :param user_id:
        :return payload:
        :raises InvalidRequestError:
        """
        try:
            product = vendor.retrieve_stripe_product(
                self.payload.data.object.plan.product
            )
            plan_nickname = format_plan_nickname(
                product_name=product["name"],
                plan_interval=self.payload.data.object.plan.interval,
            )

            payload = dict(
                event_id=self.payload.id,
                event_type=event_type,
                uid=user_id,
                customer_id=self.payload.data.object.customer,
                subscription_id=self.payload.data.object.id,
                plan_amount=self.payload.data.object.plan.amount,
                nickname=plan_nickname,
            )

            if event_type == "customer.subscription_cancelled":
                payload.update(self.get_cancellation_data())
            elif event_type == "customer.recurring_charge":
                payload.update(self.get_recurring_data(product_name=product["name"]))
            elif event_type == "customer.subscription.reactivated":
                payload.update(self.get_reactivation_data())

            return payload
        except InvalidRequestError as e:
            logger.error("Unable to gather subscription update data", error=e)
            raise e

    def get_cancellation_data(self) -> Dict[str, Any]:
        """
        Format data specific to subscription cancellation
        :return dict:
        """
        return dict(
            canceled_at=self.payload.data.object.canceled_at,
            cancel_at=self.payload.data.object.cancel_at,
            cancel_at_period_end=self.payload.data.object.cancel_at_period_end,
            current_period_start=self.payload.data.object.current_period_start,
            current_period_end=self.payload.data.object.current_period_end,
            invoice_id=self.payload.data.object.latest_invoice,
        )

    def get_recurring_data(self, product_name) -> Dict[str, Any]:
        """
        Format data specific to recurring charge
        :param product_name:
        :return dict:
        """
        invoice_id = self.payload.data.object.latest_invoice
        latest_invoice = vendor.retrieve_stripe_invoice(invoice_id)
        invoice_number = latest_invoice.number
        charge_id = latest_invoice.charge
        latest_charge = vendor.retrieve_stripe_charge(charge_id)
        last4 = latest_charge.payment_method_details.card.last4
        brand = latest_charge.payment_method_details.card.brand

        logger.info("latest invoice", latest_invoice=latest_invoice)
        logger.info("latest charge", latest_charge=latest_charge)

        return dict(
            canceled_at=self.payload.data.object.canceled_at,
            cancel_at=self.payload.data.object.cancel_at,
            cancel_at_period_end=self.payload.data.object.cancel_at_period_end,
            current_period_start=self.payload.data.object.current_period_start,
            current_period_end=self.payload.data.object.current_period_end,
            invoice_id=self.payload.data.object.latest_invoice,
            active=self.is_active_or_trialing,
            subscriptionId=self.payload.data.object.id,  # required by FxA
            productName=product_name,
            eventCreatedAt=self.payload.created,  # required by FxA
            messageCreatedAt=int(time.time()),  # required by FxA
            created=self.payload.data.object.created,
            eventId=self.payload.id,  # required by FxA
            currency=self.payload.data.object.plan.currency,
            invoice_number=invoice_number,
            brand=brand,
            last4=last4,
            charge=charge_id,
        )

    def get_reactivation_data(self) -> Dict[str, Any]:
        """
        Format data specific to recurring charge
        :return dict:
        """
        invoice_id = self.payload.data.object.latest_invoice
        latest_invoice = vendor.retrieve_stripe_invoice(invoice_id)
        latest_charge = vendor.retrieve_stripe_charge(latest_invoice.charge)
        last4 = latest_charge.payment_method_details.card.last4
        brand = latest_charge.payment_method_details.card.brand

        return dict(
            close_date=self.payload.created,
            current_period_end=self.payload.data.object.current_period_end,
            last4=last4,
            brand=brand,
        )
