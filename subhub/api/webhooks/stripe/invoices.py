#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json

from subhub.api.webhooks.stripe.abstract import AbstractStripeWebhookEvent
from subhub.api.webhooks.routes.static import StaticRoutes

from subhub.log import get_logger

logger = get_logger()


class StripeInvoiceFinalized(AbstractStripeWebhookEvent):
    def run(self):
        data = self.create_data(
            invoice_id=self.payload.data.object.id,
            customer_id=self.payload.data.object.customer,
            subscription_id=self.payload.data.object.subscription,
            currency=self.payload.data.object.currency,
            charge_id=self.payload.data.object.charge,
            period_start=self.payload.data.object.period_start,
            period_end=self.payload.data.object.period_end,
            amount=self.payload.data.object.amount_paid,
            invoice_number=self.payload.data.object.number,
            description=self.payload.data.object.lines.data[0].description,
            application_fee_amount=self.payload.data.object.application_fee_amount,
            created=self.payload.data.object.created,
        )
        logger.info("invoice finalized}", data=data)
        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(data))


class StripeInvoicePaymentFailed(AbstractStripeWebhookEvent):
    def run(self):
        data = self.create_data(
            customer_id=self.payload.data.object.customer,
            subscription_id=self.payload.data.object.subscription,
            currency=self.payload.data.object.currency,
            charge_id=self.payload.data.object.charge,
            number=self.payload.data.object.number,
            amount_due=self.payload.data.object.amount_due,
            created=self.payload.data.object.created,
        )
        logger.info("invoice payment failed", data=data)
        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(data))
