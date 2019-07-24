#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json

from subhub.webhooks.stripe.abstract import AbstractStripeWebhookEvent
from subhub.webhooks.routes.static import StaticRoutes

from subhub.log import get_logger

logger = get_logger()


class StripePaymentIntentSucceeded(AbstractStripeWebhookEvent):
    def run(self):
        charges = self.payload.data.object.charges
        data = self.create_data(
            brand=charges.data[0].payment_method_details.card.brand,
            last4=charges.data[0].payment_method_details.card.last4,
            exp_month=charges.data[0].payment_method_details.card.exp_month,
            exp_year=charges.data[0].payment_method_details.card.exp_year,
            charge_id=charges.data[0].id,
            invoice_id=self.payload.data.object.invoice,
            customer_id=self.payload.data.object.customer,
            amount=sum([p.amount - p.amount_refunded for p in charges.data]),
            created=self.payload.data.object.created,
        )
        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(data))
