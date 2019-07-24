#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json

from stripe.error import InvalidRequestError

from subhub.hub.stripe.abstract import AbstractStripeHubEvent
from subhub.hub.routes.static import StaticRoutes
from subhub.log import get_logger

logger = get_logger()


class StripeInvoiceFinalized(AbstractStripeHubEvent):
    def run(self):
        data = self.create_data(
            customer_id=self.payload.data.object.customer,
            subscription_id=self.payload.data.object.subscription,
            created=self.payload.data.object.created,
            period_start=self.payload.data.object.period_start,
            period_end=self.payload.data.object.period_end,
            amount_paid=self.payload.data.object.amount_paid,
            currency=self.payload.data.object.currency,
            charge_id=self.payload.data.object.charge,
            invoice_number=self.payload.data.object.number,
            description=self.payload.data.object.lines.data[0].description,
            invoice_id=self.payload.data.object.id,
            application_fee_amount=self.payload.data.object.get(
                "application_fee_amount"
            ),
        )
        logger.info("invoice finalized}", data=data)
        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(data))


class StripeInvoicePaymentFailed(AbstractStripeHubEvent):
    def run(self):
        try:
            nickname_list = self.payload.data.object.lines.data
            nickname = nickname_list[0]["plan"]["nickname"]
        except InvalidRequestError as e:
            nickname = ""
            logger.error("payment failed error", error=e)
        data = self.create_data(
            customer_id=self.payload.data.object.customer,
            subscription_id=self.payload.data.object.subscription,
            currency=self.payload.data.object.currency,
            charge_id=self.payload.data.object.charge,
            invoice_number=self.payload.data.object.number,
            amount_due=self.payload.data.object.amount_due,
            created=self.payload.data.object.created,
            nickname=nickname,
            invoice_id=self.payload.data.object.id,
        )
        logger.info("invoice payment failed", data=data)
        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(data))
