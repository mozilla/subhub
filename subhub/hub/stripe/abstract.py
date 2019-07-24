#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from abc import ABC, abstractmethod
import requests
from attrdict import AttrDict
from subhub.hub.routes.pipeline import RoutesPipeline
from subhub.cfg import CFG

from subhub.log import get_logger

logger = get_logger()


class AbstractStripeHubEvent(ABC):
    def __init__(self, payload):
        self.payload = AttrDict(payload)

    @property
    def is_active_or_trialing(self):
        return self.payload.data.object.status in ("active", "trialing")

    @staticmethod
    def send_to_routes(report_routes, message_to_route):
        logger.info(
            "send to routes",
            report_routes=report_routes,
            message_to_route=message_to_route,
        )
        RoutesPipeline(report_routes, message_to_route).run()

    @staticmethod
    def send_to_salesforce(self, payload):
        logger.info("sending to salesforce", payload=payload)
        uri = CFG.SALESFORCE_BASKET_URI
        requests.post(uri, data=payload)

    @staticmethod
    def unhandled_event(payload):
        logger.info("Event not handled", payload=payload)

    def unhandled_event(self, payload):
        logger.info("Event not handled", payload=payload)

    @staticmethod
    def unhandled_event(payload):
        logger.info("Event not handled", payload=payload)

    @abstractmethod
    def run(self):
        raise NotImplementedError

    def create_data(self, **kwargs):
        return dict(event_id=self.payload.id, event_type=self.payload.type, **kwargs)
