# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import requests

from abc import ABC, abstractmethod
from typing import Dict
from attrdict import AttrDict

from hub.routes.pipeline import RoutesPipeline
from shared.cfg import CFG
from structlog import get_logger

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
    def send_to_salesforce(self, payload) -> None:
        logger.info("sending to salesforce", payload=payload)
        uri = CFG.SALESFORCE_BASKET_URI
        requests.post(uri, data=payload)

    @staticmethod
    def unhandled_event(payload) -> None:
        logger.info("Event not handled", payload=payload)

    @abstractmethod
    def run(self) -> None:
        raise NotImplementedError

    def create_data(self, **kwargs) -> Dict[str, str]:
        return dict(event_id=self.payload.id, event_type=self.payload.type, **kwargs)
