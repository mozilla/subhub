from abc import ABC, abstractmethod
import requests

from attrdict import AttrDict
from subhub.api.webhooks.routes.pipeline import RoutesPipeline
from subhub.cfg import CFG

from subhub.log import get_logger

logger = get_logger()


class AbstractStripeWebhookEvent(ABC):
    def __init__(self, payload):
        self.payload = AttrDict(payload)

    @staticmethod
    def send_to_routes(report_routes, message_to_route):
        logger.info(
            "send to routes",
            report_routes=report_routes,
            message_to_route=message_to_route,
        )
        RoutesPipeline(report_routes, message_to_route).run()

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
