# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json

from datetime import datetime

from stripe.error import InvalidRequestError
from stripe import Product, Customer, Subscription
from typing import Dict, Any

from hub.vendor.abstract import AbstractStripeHubEvent
from hub.routes.static import StaticRoutes
from hub.shared.vendor_utils import format_brand
from hub.shared.vendor import (
    retrieve_stripe_subscription,
    retrieve_stripe_invoice_upcoming,
    retrieve_stripe_invoice_upcoming_by_subscription,
    retrieve_stripe_invoice,
    retrieve_stripe_charge,
)
from shared.log import get_logger

logger = get_logger()


class StripeInvoicePaymentFailed(AbstractStripeHubEvent):
    def run(self) -> bool:
        """
        Handle Invoice Payment Failed events from Stripe.
        If the payment failed on subscription_create take no action and :return false
        Else format data to be sent to Salesforce :return true
        :return:
        """
        logger.info("invoice payment failed event received", payload=self.payload)

        if self.payload.data.object.billing_reason == "subscription_create":
            logger.info(
                "invoice payment failed on subscription create - data not sent to external routes"
            )
            return False

        data = self.create_payload()
        logger.info("invoice payment failed", data=data)
        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(data))
        return True

    def create_payload(self) -> Dict[str, Any]:
        """
        Create payload to be sent to external sources
        :return payload:
        :raises InvalidRequestError:
        """
        try:
            invoice_data = self.payload.data.object.lines.data
            product = Product.retrieve(invoice_data[0]["plan"]["product"])
            nickname = product["name"]
        except InvalidRequestError as e:
            logger.error("Unable to get plan nickname for payload", error=e)
            nickname = ""

        return self.create_data(
            customer_id=self.payload.data.object.customer,
            subscription_id=self.payload.data.object.subscription,
            currency=self.payload.data.object.currency,
            charge_id=self.payload.data.object.charge,
            amount_due=self.payload.data.object.amount_due,
            created=self.payload.data.object.created,
            nickname=nickname,
        )


class StripeInvoicePaymentSucceeded(AbstractStripeHubEvent):
    def run(self) -> bool:
        """
        Parse the event data sent by Stripe contained within self.payload
        :return True to indicate successfully sent
        """
        logger.debug("invoice payment succeeded", payload=self.payload)
        subscription_id = self.payload.data.object.subscription
        subscription = retrieve_stripe_subscription(subscription_id)
        if subscription:
            plan = subscription.get("plan")
            created = self.payload.data.object.created
            customer = subscription.get("customer")
            user_id = None
            metadata = customer.get("metadata")
            if metadata:
                user_id = metadata.get("userid")
            is_subscription_new = self.determine_new(subscription, created)
            logger.debug(
                "invoice payment succeeded",
                is_subscription_new=is_subscription_new,
                customer=customer,
            )
            if is_subscription_new == "new":
                event_type = "customer.subscription.created"
                data = self.create_payload(
                    event_type, user_id, plan, customer, subscription
                )
                logger.debug("data", data=data)
                routes = [StaticRoutes.SALESFORCE_ROUTE]
                self.send_to_routes(routes, json.dumps(data))
                return True
            elif is_subscription_new == "recurring":
                event_type = "customer.recurring_charge"
                data = self.create_payload(
                    event_type, user_id, plan, customer, subscription
                )
                logger.debug("data", data=data)
                routes = [StaticRoutes.SALESFORCE_ROUTE]
                self.send_to_routes(routes, json.dumps(data))
                return True
            else:
                logger.error(
                    "plan type not supported", payment_type=is_subscription_new
                )
        return False

    def determine_new(self, subscription: Subscription, created_date: int) -> str:
        """
        Evaluate Subscription information to determine if payment is for a new subscription.
        """
        plan = subscription.get("plan")
        start_date = subscription.get("start_date")
        logger.debug(
            "determine new", plan=plan, start_date=start_date, created_date=created_date
        )
        if plan:
            interval = plan.get("interval")
            logger.info("interval", interval=interval)
            if interval == "month":
                month_diff = self.diff_month(start_date, created_date)
                logger.info("month diff", month_diff=month_diff)
                if month_diff > 0:
                    return "recurring"
                else:
                    return "new"
            elif interval == "day":
                diff_day = self.diff_day(start_date, created_date)
                if diff_day > 0:
                    return "recurring"
                else:
                    return "new"
            else:
                return "unsupported-unknown"
        return "unsupported-unknown"

    def diff_month(self, begin_date_int: int, end_date_int: int) -> int:
        """
        Calculate the difference in months between two unix date objects and return as int
        """
        begin_date = datetime.fromtimestamp(begin_date_int)
        end_date = datetime.fromtimestamp(end_date_int)
        logger.debug("diff month", begin_date=begin_date, end_date=end_date)
        return (
            (end_date.year - begin_date.year) * 12 + end_date.month - begin_date.month
        )

    def diff_day(self, begin_date_int: int, end_date_int: int) -> int:
        """
        Calculate the difference in months between two unix date objects and return as int
        """
        begin_date = datetime.fromtimestamp(begin_date_int)
        begin = datetime(begin_date.year, begin_date.month, begin_date.day).strftime(
            "%s"
        )
        end_date = datetime.fromtimestamp(end_date_int)
        end = datetime(end_date.year, end_date.month, end_date.day).strftime("%s")
        logger.debug(
            "diff day",
            begin_date=begin_date,
            end_date=end_date,
            begin=begin,
            end=end,
            rounded=round((float(end) - float(begin)) / (60 * 60 * 24)),
        )
        return round((float(end) - float(begin)) / (60 * 60 * 24))

    def create_payload(
        self,
        event_type,
        user_id,
        plan: Dict[str, Any],
        customer: Dict[str, Any],
        subscription: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create payload to be sent to external sources based on event_type
        :param event_type:
        :param user_id:
        :param plan:
        :param customer:
        :param subscription:
        :return payload:
        :raises InvalidRequestError:
        """
        logger.debug("create payload", event_type=event_type)
        try:
            plan_nickname = plan.get("name")

            payload = dict(
                event_id=self.payload.id,
                event_type=event_type,
                uid=user_id,
                customer_id=customer.get("id"),
                subscription_id=subscription.get("id"),
                plan_amount=plan.get("amount"),
                nickname=plan_nickname,
            )
            payload.update(
                self.get_subscription_data(
                    customer=customer,
                    product_name=plan.get("nickname"),
                    subscription=subscription,
                    event_type=event_type,
                )
            )
            return payload
        except InvalidRequestError as e:
            logger.error("Unable to gather subscription update data", error=e)
            raise e

    def get_subscription_data(
        self,
        customer: Dict[str, Any],
        product_name: str,
        subscription: Dict[str, Any],
        event_type: str,
    ) -> Dict[str, Any]:
        """
        Format data specific to new subscription
        :param customer:
        :param product_name:
        :param subscription:
        :param event_type:
        :return dict:
        """
        invoice_id = subscription.get("latest_invoice")
        latest_invoice = retrieve_stripe_invoice(invoice_id)
        invoice_number = latest_invoice.get("number")
        charge_id = latest_invoice.get("charge")
        latest_charge = retrieve_stripe_charge(charge_id)
        payment_method_details = latest_charge.get("payment_method_details")
        if payment_method_details:
            card = payment_method_details.get("card")
            if card:
                last4 = card.get("last4")
                brand = format_brand(card.get("brand"))
            else:
                return None
        else:
            return None

        plan = subscription.get("plan")
        next_invoice = retrieve_stripe_invoice_upcoming_by_subscription(
            customer_id=customer.get("id"), subscription_id=subscription.get("id")
        )
        next_invoice_date = next_invoice.get("period_end", 0)

        data = dict(
            canceled_at=subscription.get("canceled_at"),
            cancel_at=subscription.get("cancel_at"),
            cancel_at_period_end=subscription.get("cancel_at_period_end"),
            current_period_start=subscription.get("current_period_start"),
            current_period_end=subscription.get("current_period_end"),
            next_invoice_date=next_invoice_date,
            invoice_id=subscription.get("latest_invoice"),
            active=self.payment_active_or_trialing(subscription.get("status")),
            productName=product_name,
            created=subscription.get("created"),
            currency=plan.get("currency"),
            invoice_number=invoice_number,
            brand=brand,
            last4=last4,
            charge=charge_id,
        )
        if event_type == "customer.recurring_charge":
            data.update(self.get_recurring_data(customer_id=customer.get("id")))
        return data

    def get_recurring_data(self, customer_id: str) -> Dict[str, Any]:
        """
        Format data specific to recurring subscription
        :param customer_id:
        :return dict:
        """
        upcoming_invoice = retrieve_stripe_invoice_upcoming(customer=customer_id)
        return dict(
            proration_amount=upcoming_invoice.get("amount_due", 0),
            total_amount=self.get_total_upcoming_invoice_amount(
                upcoming_invoice=upcoming_invoice
            ),
        )

    def payment_active_or_trialing(self, status: str) -> bool:
        """
        Check status of subscription and returns bool
        :param status:
        :returns bool:
        """
        return status in ("active", "trialing")

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
