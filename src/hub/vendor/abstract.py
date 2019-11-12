# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import requests
import json

from abc import ABC, abstractmethod
from typing import Dict
from attrdict import AttrDict

from hub.routes.pipeline import RoutesPipeline, AllRoutes
from shared.cfg import CFG
from shared.log import get_logger

logger = get_logger()


class AbstractStripeHubEvent(ABC):
    def __init__(self, payload) -> None:
        self.payload = AttrDict(payload)

    @property
    def is_active_or_trialing(self) -> bool:
        return self.payload.data.object.status in ("active", "trialing")

    @staticmethod
    def send_to_routes(report_routes, message_to_route) -> None:
        logger.info(
            "send to routes",
            report_routes=report_routes,
            message_to_route=message_to_route,
        )
        RoutesPipeline(report_routes, message_to_route).run()

    @staticmethod
    def send_to_all_routes(messages_to_routes) -> None:
        logger.info("send to all routes", messages_to_routes=messages_to_routes)
        AllRoutes(messages_to_routes).run()

    @staticmethod
    def send_to_salesforce(self, payload) -> None:
        logger.info("sending to salesforce", payload=payload)
        uri = CFG.SALESFORCE_BASKET_URI
        requests.post(uri, data=payload)

    @staticmethod
    def unhandled_event(payload) -> None:
        logger.info("Event not handled", payload=payload)

    @abstractmethod
    def run(self) -> bool:
        raise NotImplementedError

    def create_data(self, **kwargs) -> Dict[str, str]:
        return dict(event_id=self.payload.id, event_type=self.payload.type, **kwargs)

    def customer_event_to_all_routes(self, data_projection, data) -> None:
        subsets = []
        for route in data_projection:
            try:
                logger.debug("sending to", key=route)
                subset = dict((k, data[k]) for k in data_projection[route] if k in data)
                payload = {"type": route, "data": json.dumps(subset)}
                subsets.append(payload)
                logger.info("subset", subset=subset)
                logger.debug("sent to", key=route)
            except Exception as e:
                # log something and maybe change the exception type.
                logger.error("projection exception", error=e)
        else:
            self.send_to_all_routes(subsets)
