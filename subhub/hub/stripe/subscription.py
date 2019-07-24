#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json

from subhub.hub.stripe.abstract import AbstractStripeHubEvent
from subhub.hub.routes.static import StaticRoutes

from subhub.log import get_logger

logger = get_logger()


class StripeSubscriptionCreated(AbstractStripeHubEvent):
    def run(self):
        data = self.create_data(
            customer_id=self.payload.data.object.id,
            subscription_created=self.payload.data.items.data[0].created,
            current_period_start=self.payload.data.current_period_start,
            current_period_end=self.payload.data.current_period_end,
            plan_amount=self.payload.data.plan.amount,
            plan_currency=self.payload.data.plan.currency,
            plan_name=self.payload.data.plan.nickname,
            created=self.payload.data.object.created,
        )
        logger.info("subscription created", data=data)
        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(data))
