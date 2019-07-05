#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import requests

from subhub.webhooks.routes.abstract import AbstractRoute
from subhub.cfg import CFG

from subhub.log import get_logger

logger = get_logger()


class SalesforceRoute(AbstractRoute):
    def route(self):
        route_payload = json.loads(self.payload)
        logger.info("route payload", route_payload=route_payload)
        basket_url = CFG.SALESFORCE_BASKET_URI + CFG.BASKET_API_KEY
        logger.info("basket url", basket_url=basket_url)
        request_post = requests.post(basket_url, json=route_payload)
        self.report_route(route_payload, "salesforce")
        logger.info(
            "sending to salesforce", payload=self.payload, request_post=request_post
        )
