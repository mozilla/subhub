# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json

from datetime import datetime

from stripe.error import InvalidRequestError
from stripe import Product, Customer, Subscription
from typing import Dict, Any

from src.hub.vendor.abstract import AbstractStripeHubEvent
from src.hub.routes.static import StaticRoutes
from src.hub.shared.vendor_utils import format_brand
from src.hub.shared.vendor import (
    retrieve_stripe_subscription,
    retrieve_stripe_invoice_upcoming,
    retrieve_stripe_invoice_upcoming_by_subscription,
    retrieve_stripe_invoice,
    retrieve_stripe_charge,
)
from src.hub.shared.log import get_logger

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
            Donation_Contact__c=self.payload.data.object.customer,
            PMT_Subscription_ID__c=self.payload.data.object.subscription,
            Currency__c=self.payload.data.object.currency,
            PMT_Transaction_ID__c=self.payload.data.object.charge,
            Amount=self.payload.data.object.amount_due,
            CloseDate=self.payload.data.object.created,
            Service_Plan__c=nickname,
        )


class StripeInvoicePaymentSucceeded(AbstractStripeHubEvent):
    def run(self) -> bool:
        """
        Parse the event data sent by Stripe contained within self.payload
        :return True to indicate successfully sent
        """
        invoice = self.payload.data.object
        logger.debug("invoice payment succeeded", payload=self.payload)
        subscription_id = invoice.subscription
        subscription = retrieve_stripe_subscription(subscription_id)
        if subscription:
            plan = subscription.get("plan")
            customer = subscription.get("customer")
            email = self.payload.data.object.get("customer_email")
            user_id = None
            metadata = customer.get("metadata")
            if metadata:
                user_id = metadata.get("userid")
            logger.debug(
                "invoice payment succeeded",
                billing_reason=invoice.billing_reason,
                customer=customer,
            )

            event_type = "customer.recurring_charge"
            if invoice.billing_reason == "subscription_create":
                event_type = "customer.subscription.created"

            data = self.create_payload(
                event_type, user_id, plan, customer, subscription, email
            )
            logger.debug("data", data=data)
            routes = [StaticRoutes.SALESFORCE_ROUTE]
            self.send_to_routes(routes, json.dumps(data))
            return True

        return False

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
        email: str,
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
            plan_nickname = plan.get("nickname")

            payload = dict(
                Event_Id__c=self.payload.id,
                Event_Name__c=event_type,
                FxA_Id__c=user_id,
                Donation_Contact__c=customer.get("id"),
                PMT_Subscription_ID__c=subscription.get("id"),
                Amount=plan.get("amount"),
                Service_Plan__c=plan_nickname,
                Email=email,
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
            Billing_Cycle_Start__c=subscription.get("current_period_start"),
            Billing_Cycle_End__c=subscription.get("current_period_end"),
            Next_Invoice_Date__c=next_invoice_date,
            PMT_Invoice_ID__c=subscription.get("latest_invoice"),
            CloseDate=subscription.get("created"),
            Currency__c=plan.get("currency"),
            Invoice_Number__c=invoice_number,
            Credit_Card_Type__c=brand,
            Last_4_Digits__c=last4,
            PMT_Transaction_ID__c=charge_id,
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
