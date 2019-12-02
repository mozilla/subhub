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
from hub.shared.vendor_utils import format_brand
from shared.log import get_logger
from hub.shared import vendor
from hub.shared.db import SubHubDeletedAccountModel

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
            brand = format_brand(latest_charge.payment_method_details.card.brand)

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

            next_invoice = vendor.retrieve_stripe_invoice_upcoming_by_subscription(
                customer_id=self.payload.data.object.customer,
                subscription_id=self.payload.data.object.id,
            )
            next_invoice_date = next_invoice.get("period_end", 0)

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
                next_invoice_date=next_invoice_date,
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
        previous_plan = previous_attributes.get("plan")
        logger.debug(
            "previous plan",
            previous_plan=previous_plan,
            previous_attributes=previous_attributes,
        )

        data = None
        routes = None
        if current_cancel_at_period_end and not previous_cancel_at_period_end:
            data = self.create_payload(
                "customer.subscription_cancelled", user_id, previous_plan=None
            )
            logger.info("customer subscription cancel at period end", data=data)
            routes = [StaticRoutes.SALESFORCE_ROUTE]
        elif (
            not current_cancel_at_period_end
            and not previous_cancel_at_period_end
            and self.payload.data.object.status == "active"
            and not previous_plan
        ):
            data = self.create_payload(
                "customer.recurring_charge", user_id, previous_plan=None
            )
            logger.info("customer subscription new recurring", data=data)
            routes = [StaticRoutes.SALESFORCE_ROUTE]
        elif previous_plan:
            data = self.create_payload(
                "customer.subscription_change", user_id, previous_plan=previous_plan
            )
            logger.info("customer subscription change", data=data)
            routes = [StaticRoutes.SALESFORCE_ROUTE]
        elif (
            not current_cancel_at_period_end
            and previous_cancel_at_period_end
            and previous_plan is None
        ):
            data = self.create_payload(
                "customer.subscription.reactivated", user_id, previous_plan=None
            )
            logger.info("customer subscription reactivated", data=data)
            routes = [StaticRoutes.SALESFORCE_ROUTE]
        else:
            logger.warning(
                "customer subscription updated not processed", payload=self.payload
            )

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
            metadata = customer.get("metadata", None)
            user_id = metadata.get("userid", None)

        if user_id is None:
            logger.error(
                "customer subscription updated - no userid",
                error=customer_id,
                is_customer_deleted=deleted,
            )
            raise ClientError(f"userid is None for customer {customer_id}")

        return user_id

    def create_payload(self, event_type, user_id, previous_plan) -> Dict[str, Any]:
        """
        Create payload to be sent to external sources based on event_type
        :param event_type:
        :param user_id:
        :param previous_plan:
        :return payload:
        :raises InvalidRequestError:
        """
        logger.info("create payload", event_type=event_type)
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
            elif event_type == "customer.subscription_change":
                payload.update(
                    self.get_subscription_change(
                        payload, previous_plan=previous_plan, new_product=product
                    )
                )

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
        brand = format_brand(latest_charge.payment_method_details.card.brand)
        upcoming_invoice = vendor.retrieve_stripe_invoice_upcoming(
            customer=self.payload.data.object.customer
        )

        logger.info("latest invoice", latest_invoice=latest_invoice)
        logger.info("latest charge", latest_charge=latest_charge)

        next_invoice = vendor.retrieve_stripe_invoice_upcoming_by_subscription(
            customer_id=self.payload.data.object.customer,
            subscription_id=self.payload.data.object.id,
        )
        next_invoice_date = next_invoice.get("period_end", 0)

        return dict(
            canceled_at=self.payload.data.object.canceled_at,
            cancel_at=self.payload.data.object.cancel_at,
            cancel_at_period_end=self.payload.data.object.cancel_at_period_end,
            current_period_start=self.payload.data.object.current_period_start,
            current_period_end=self.payload.data.object.current_period_end,
            next_invoice_date=next_invoice_date,
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
            proration_amount=upcoming_invoice.get("amount_due", 0),
            total_amount=self.get_total_upcoming_invoice_amount(
                upcoming_invoice=upcoming_invoice
            ),
        )

    def get_total_upcoming_invoice_amount(
        self, upcoming_invoice: Dict[str, Any]
    ) -> float:
        """
        Get the total amount of the upcoming invoice
        :param upcoming_invoice:
        :return:
        """
        total_amount = 0
        for line in upcoming_invoice["lines"]["data"]:
            total_amount += line.get("amount", 0)
        return total_amount

    def get_reactivation_data(self) -> Dict[str, Any]:
        """
        Format data specific to recurring charge
        :return dict:
        """
        invoice_id = self.payload.data.object.latest_invoice
        latest_invoice = vendor.retrieve_stripe_invoice(invoice_id)
        latest_charge = vendor.retrieve_stripe_charge(latest_invoice.charge)
        last4 = latest_charge.payment_method_details.card.last4
        brand = format_brand(latest_charge.payment_method_details.card.brand)

        return dict(
            close_date=self.payload.created,
            current_period_end=self.payload.data.object.current_period_end,
            last4=last4,
            brand=brand,
        )

    def get_subscription_change(
        self,
        payload: Dict[str, Any],
        previous_plan: Dict[str, Any],
        new_product: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Format data specific to a changed subscription
        :param payload:
        :param previous_plan:
        :param new_product:
        :return dict:
        """
        previous_product = vendor.retrieve_stripe_product(previous_plan["product"])
        event_type = self.get_subscription_type(new_product, previous_product)
        invoice = vendor.retrieve_stripe_invoice(
            invoice_id=self.payload.data.object.latest_invoice
        )
        upcoming_invoice = vendor.retrieve_stripe_invoice_upcoming(
            customer=payload.get("customer_id", None)
        )
        logger.debug(
            "sub change",
            event_type=event_type,
            payload=payload,
            self_payload=self.payload,
            upcoming_invoice=upcoming_invoice,
            amount_due=upcoming_invoice.get("amount_due", 0),
        )
        plan = vendor.retrieve_stripe_plan(previous_plan.get("id", None))
        nickname_old = format_plan_nickname(
            product_name=previous_plan.get("nickname", "Not available"),
            plan_interval=plan.get("interval", None),
        )
        return dict(
            nickname_old=nickname_old,
            nickname_new=payload.pop("nickname"),
            event_type=event_type,
            close_date=self.payload.get("created", None),
            plan_amount_new=payload.pop("plan_amount"),
            plan_amount_old=self.get_previous_plan_amount(
                previous_plan=previous_plan.get("id", None)
            ),
            interval=self.payload.data.object.plan.interval,
            current_period_end=self.payload.data.object.current_period_end,
            invoice_number=invoice.get("number", None),
            invoice_id=invoice.get("id", None),
            proration_amount=upcoming_invoice.get("amount_due", 0),
        )

    def get_subscription_type(
        self, new_product: Dict[str, Any], previous_product: Dict[str, Any]
    ) -> str:
        """
        Determine if new product is an upgrade or downgrade
        :param new_product:
        :param previous_product:
        :return:
        """
        logger.debug(
            "get sub meta", new_product=new_product, previous_product=previous_product
        )
        new_product_metadata = new_product.get("metadata", None)
        new_product_set_order = new_product_metadata.get("productSetOrder", 0)
        previous_product_metadata = previous_product.get("metadata", None)
        previous_product_set_order = previous_product_metadata.get("productSetOrder", 0)
        logger.debug(
            "get subscription type",
            new_product_set_order=new_product_set_order,
            previous_product_set_order=previous_product_set_order,
        )
        if new_product_set_order > previous_product_set_order:
            return "customer.subscription.upgrade"
        elif previous_product_set_order > new_product_set_order:
            return "customer.subscription.downgrade"
        else:
            raise InvalidRequestError(
                message="Not valid subscription change", param="invalid_change"
            )

    def get_previous_plan_amount(self, previous_plan: str) -> int:
        """
        Get new plan amount for upgrade/downgrade
        :param previous_plan:
        :return:
        """
        plan = vendor.retrieve_stripe_plan(previous_plan)
        return plan.get("amount", 0)
