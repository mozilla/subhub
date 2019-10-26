# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json

from stripe.error import InvalidRequestError
from stripe import Product
from typing import Dict, Any

from hub.vendor.abstract import AbstractStripeHubEvent
from hub.routes.static import StaticRoutes
from hub.shared.utils import format_plan_nickname
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
            nickname = format_plan_nickname(
                product_name=product["name"],
                plan_interval=invoice_data[0]["plan"]["interval"],
            )
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
