# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import time
import stripe

from stripe.error import InvalidRequestError
from datetime import datetime
from typing import Optional, Dict, Any

from hub.vendor.abstract import AbstractStripeHubEvent
from hub.routes.static import StaticRoutes
from hub.shared.exceptions import ClientError
from hub.shared.universal import format_plan_nickname
from structlog import get_logger

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
            updated_customer = stripe.Customer.retrieve(id=customer_id)
            user_id = updated_customer.metadata.get("userid")
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
    def run(self) -> None:
        logger.info("customer subscription deleted", payload=self.payload)
        try:
            customer_id = self.payload.data.object.customer
            updated_customer = stripe.Customer.retrieve(id=customer_id)
            user_id = updated_customer.metadata.get("userid")
        except InvalidRequestError as e:
            logger.error("Unable to find customer", error=e)
            raise e
        if user_id:
            product = stripe.Product.retrieve(self.payload.data.object.plan.product)

            data = dict(
                active=self.is_active_or_trialing,
                subscriptionId=self.payload.data.object.id,
                productName=product["name"],
                eventId=self.payload.id,  # required by FxA
                event_id=self.payload.id,
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
    def run(self) -> None:
        logger.info("customer subscription updated", payload=self.payload)
        try:
            customer_id = self.payload.data.object.customer
            updated_customer = stripe.Customer.retrieve(id=customer_id)
            user_id = updated_customer.metadata.get("userid")
        except InvalidRequestError as e:
            logger.error("Unable to find customer", error=e)
            raise e
        if user_id:
            previous_attributes: Dict[str, Any] = dict()
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

                product = stripe.Product.retrieve(self.payload.data.object.plan.product)
                plan_nickname = format_plan_nickname(
                    product_name=product["name"],
                    plan_interval=self.payload.data.object.plan.interval,
                )

                data = dict(
                    event_id=self.payload.id,
                    event_type="customer.subscription_cancelled",
                    uid=user_id,
                    customer_id=self.payload.data.object.customer,
                    subscription_id=self.payload.data.object.id,
                    plan_amount=self.payload.data.object.plan.amount,
                    canceled_at=self.payload.data.object.canceled_at,
                    cancel_at=self.payload.data.object.cancel_at,
                    cancel_at_period_end=self.payload.data.object.cancel_at_period_end,
                    nickname=plan_nickname,
                    invoice_id=self.payload.data.object.latest_invoice,
                    current_period_start=self.payload.data.object.current_period_start,
                    current_period_end=self.payload.data.object.current_period_end,
                )
                logger.info("customer subscription cancel at period end", data=data)
                routes = [StaticRoutes.SALESFORCE_ROUTE]
                self.send_to_routes(routes, json.dumps(data))
            elif (
                not self.payload.data.object.cancel_at_period_end
                and self.payload.data.object.status == "active"
                # and not previous_attributes.get("cancel_at_period_end")
            ):
                try:
                    customer_id = self.payload.data.object.customer
                    updated_customer = stripe.Customer.retrieve(id=customer_id)
                    user_id = updated_customer.metadata.get("userid")
                    invoice_id = self.payload.data.object.latest_invoice
                    latest_invoice = self.get_latest_invoice(invoice_id)
                    logger.info("latest invoice", latest_invoice=latest_invoice)
                    invoice_number = latest_invoice.number  # type: ignore
                    charge = latest_invoice.charge  # type: ignore
                    logger.info("charge", charge=charge)
                    latest_charge = self.get_latest_charge(charge)
                    logger.info("latest charge", latest_charge=latest_charge)
                    last4 = (
                        latest_charge.payment_method_details.card.last4  # type: ignore
                    )
                    brand = (
                        latest_charge.payment_method_details.card.brand  # type: ignore
                    )
                except InvalidRequestError as e:
                    logger.error("Unable to gather data", error=e)
                    raise e

                product = stripe.Product.retrieve(self.payload.data.object.plan.product)
                product_name = product["name"]

                plan_nickname = format_plan_nickname(
                    product_name=product_name,
                    plan_interval=self.payload.data.object.plan.interval,
                )
                data = dict(
                    event_id=self.payload.id,
                    event_type="customer.recurring_charge",
                    uid=user_id,
                    active=self.is_active_or_trialing,
                    subscriptionId=self.payload.data.object.id,  # required by FxA
                    subscription_id=self.payload.data.object.id,
                    productName=product_name,
                    nickname=plan_nickname,
                    eventCreatedAt=self.payload.created,  # required by FxA
                    messageCreatedAt=int(time.time()),  # required by FxA
                    invoice_id=self.payload.data.object.latest_invoice,
                    customer_id=self.payload.data.object.customer,
                    created=self.payload.data.object.created,
                    plan_amount=self.payload.data.object.plan.amount,
                    eventId=self.payload.id,  # required by FxA
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
                logger.info("customer subscription new recurring", data=data)
                routes = [StaticRoutes.SALESFORCE_ROUTE]
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

    def get_latest_invoice(self, invoice_id) -> Optional[Dict[str, Any]]:
        attempts = 2
        latest_invoice = stripe.Invoice.retrieve(id=invoice_id)
        logger.info("get latest invoice", latest_invoice=latest_invoice)
        while attempts > 0:
            attempts -= 1
            if latest_invoice.charge is None or latest_invoice.number is None:
                time.sleep(0.2)
                self.get_latest_invoice(invoice_id)
            else:
                return latest_invoice
        return None

    def get_latest_charge(self, charge) -> Optional[Dict[str, Any]]:
        attempts = 2
        latest_charge = stripe.Charge.retrieve(id=charge)
        logger.info("get latest charge", latest_charge=latest_charge)
        while attempts > 0:
            attempts -= 1
            if (
                latest_charge.payment_method_details.card.last4 is None
                or latest_charge.payment_method_details.card.brand is None
            ):
                time.sleep(0.2)
                self.get_latest_charge(charge)
            else:
                return latest_charge
        return None
