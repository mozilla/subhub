#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json

import stripe
from stripe.error import InvalidRequestError

from subhub.hub.stripe.abstract import AbstractStripeHubEvent
from subhub.hub.routes.static import StaticRoutes
from subhub.log import get_logger

logger = get_logger()


class StripePaymentIntentSucceeded(AbstractStripeHubEvent):
    def run(self):
        logger.info("payment intent succeeded", payload=self.payload)
        try:
            invoice_id = self.payload.data.object.invoice
            invoice = stripe.Invoice.retrieve(id=invoice_id)
            subscription_id = invoice.subscription
            period_start = invoice.period_start
            period_end = invoice.period_end
            logger.info("subscription id", subscription_id=subscription_id)
            charges = self.payload.data.object.charges
            data = self.create_data(
                subscription_id=subscription_id,
                period_end=period_end,
                period_start=period_start,
                brand=charges.data[0].payment_method_details.card.brand,
                last4=charges.data[0].payment_method_details.card.last4,
                exp_month=charges.data[0].payment_method_details.card.exp_month,
                exp_year=charges.data[0].payment_method_details.card.exp_year,
                charge_id=charges.data[0].id,
                invoice_id=self.payload.data.object.invoice,
                customer_id=self.payload.data.object.customer,
                amount_paid=sum([p.amount - p.amount_refunded for p in charges.data]),
                created=self.payload.data.object.created,
                currency=self.payload.data.object.currency,
            )
            routes = [StaticRoutes.SALESFORCE_ROUTE]
            self.send_to_routes(routes, json.dumps(data))
        except InvalidRequestError as e:
            logger.error("Unable to find invoice", error=e)
            raise InvalidRequestError(message="Unable to find invoice", param=str(e))
