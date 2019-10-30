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

from hub.vendor.abstract import AbstractStripeHubEvent
from hub.routes.static import StaticRoutes
from hub.shared.exceptions import ClientError
from hub.shared.utils import format_plan_nickname
from shared.log import get_logger
from hub.shared import vendor

logger = get_logger()


class StripeCustomerCreated(AbstractStripeHubEvent):
    def run(self) -> None:
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
    def run(self) -> None:
        logger.info("customer deleted", payload=self.payload)
        customer_id = self.payload.data.object.id
        uid = self.payload.data.object.metadata.userid
        deleted_user = g.subhub_deleted_users.get_user(uid, customer_id)
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
        data = self.create_data(
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
        logger.info("customer delete", data=data)
        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(data))


class StripeCustomerSourceExpiring(AbstractStripeHubEvent):
    def run(self) -> None:
        try:
            logger.info("customer source expiring")
            customer_id = self.payload.data.object.customer
            updated_customer = stripe.Customer.retrieve(id=customer_id)
            email = updated_customer.email

            nicknames = list()
            products = {}  # type: Dict
            for subs in updated_customer.subscriptions["data"]:
                if subs["status"] in ["active", "trialing"]:
                    try:
                        product = products[subs["plan"]["product"]]
                    except KeyError:
                        product = stripe.Product.retrieve(subs["plan"]["product"])
                        products[subs["plan"]["product"]] = product

                    plan_nickname = format_plan_nickname(
                        product_name=product["name"],
                        plan_interval=subs["plan"]["interval"],
                    )
                    nicknames.append(plan_nickname)
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
            raise e


class StripeCustomerSubscriptionCreated(AbstractStripeHubEvent):
    def run(self) -> None:
        logger.info("customer subscription created", payload=self.payload)
        try:
            customer_id = self.payload.data.object.customer
            updated_customer = vendor.retrieve_stripe_customer(customer_id=customer_id)
            if not isinstance(updated_customer, dict):
                updated_customer = updated_customer.to_dict()
            metadata = updated_customer.get("metadata")
            if metadata:
                user_id = metadata.get("userid")
        except InvalidRequestError as e:
            logger.error("Unable to find customer", error=e)
            raise e
        try:
            logger.info("invoice", latest=self.payload.data.object.latest_invoice)
            invoice_id = self.payload.data.object.latest_invoice
            latest_invoice = stripe.Invoice.retrieve(id=invoice_id)
            logger.info(
                "latest invoice",
                latest_invoice=latest_invoice.number,
                charge=latest_invoice.charge,
            )
            invoice_number = latest_invoice.number
            charge = latest_invoice.charge
        except InvalidRequestError as e:
            logger.error("Unable to retrieve invoice", error=e)
            raise e
        try:
            latest_charge = stripe.Charge.retrieve(id=charge)
            logger.info(
                "latest charge", last4=latest_charge.payment_method_details["card"]
            )
            last4 = latest_charge.payment_method_details["card"]["last4"]
            brand = latest_charge.payment_method_details["card"]["brand"]
        except InvalidRequestError as e:
            logger.error("Unable to retrieve charge", error=e)
            raise e
        if user_id:
            product = stripe.Product.retrieve(self.payload.data.object.plan.product)
            product_name = product["name"]
            product_id = product["id"]

            plan_nickname = format_plan_nickname(
                product_name=product_name,
                plan_interval=self.payload.data.object.plan.interval,
            )

            data = self.create_data(
                uid=user_id,
                active=self.is_active_or_trialing,
                subscriptionId=self.payload.data.object.id,
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
                charge=charge,
            )
            # NOTE:
            # Firefox's route has a particular casing requirement
            # Salesforce's route doesn't care.
            data_projection_by_route = {
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
    def run(self) -> None:
        logger.info("customer subscription deleted", payload=self.payload)
        try:
            customer_id = self.payload.data.object.customer
            updated_customer = vendor.retrieve_stripe_customer(customer_id=customer_id)
            if not isinstance(updated_customer, dict):
                updated_customer = updated_customer.to_dict()
            metadata = updated_customer.get("metadata")
            if metadata:
                user_id = metadata.get("userid")
        except InvalidRequestError as e:
            logger.error("Unable to find customer", error=e)
            raise e
        if user_id:
            product = stripe.Product.retrieve(self.payload.data.object.plan.product)
            product_id = product["id"]
            data = dict(
                uid=user_id,
                active=self.is_active_or_trialing,
                subscriptionId=self.payload.data.object.id,
                productId=product_id,
                eventId=self.payload.id,
                eventCreatedAt=self.payload.created,
                messageCreatedAt=int(time.time()),
            )
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
            updated_customer = stripe.Customer.retrieve(id=customer_id)
            user_id = updated_customer.metadata.get("userid", None)
        except InvalidRequestError as e:
            logger.error("Unable to find customer", error=e)
            raise e

        if user_id is None:
            logger.error("customer subscription updated - no userid", error=customer_id)
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
            product = stripe.Product.retrieve(self.payload.data.object.plan.product)
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
        invoice_number = latest_invoice.number  # type: ignore
        charge_id = latest_invoice.charge  # type: ignore
        latest_charge = vendor.retrieve_stripe_charge(charge_id)
        last4 = latest_charge.payment_method_details.card.last4  # type: ignore
        brand = latest_charge.payment_method_details.card.brand  # type: ignore

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
        last4 = latest_charge.payment_method_details.card.last4  # type: ignore
        brand = latest_charge.payment_method_details.card.brand  # type: ignore

        return dict(
            close_date=self.payload.created,
            current_period_end=self.payload.data.object.current_period_end,
            last4=last4,
            brand=brand,
        )
