import logging
from abc import ABC, abstractmethod
import requests

from attrdict import AttrDict
from subhub.api.webhooks.routes.pipeline import RoutesPipeline
from subhub.cfg import CFG
from subhub import secrets

logger = logging.getLogger("webhook_abstract")
log_handle = logging.StreamHandler()
log_handle.setLevel(logging.INFO)
logformat = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log_handle.setFormatter(logformat)
logger.addHandler(log_handle)


class AbstractStripeWebhookEvent(ABC):
    def __init__(self, payload):
        assert isinstance(payload, dict)
        self.payload = AttrDict(payload)

    @staticmethod
    def send_to_routes(report_routes, messageToRoute):
        logger.info(f"report routes {report_routes} message {messageToRoute}")
        RoutesPipeline(report_routes, messageToRoute).run()

    def send_to_salesforce(self, payload):
        logger.info(f"sending to salesforce : {payload}")
        uri = CFG.SALESFORCE_BASKET_URI
        requests.post(uri, data=payload)

    @staticmethod
    def unhandled_event(payload):
        print(f"unhandled event {payload}")
        logger.info(f"Event not handled: {payload['id']} ")
        pass

    def unhandled_event(self, payload):
        logging.info(f"Event not handled: {payload}")

    @staticmethod
    def unhandled_event(payload):
        logger.info(f"Event not handled: {payload['id']} {payload['type']}")
        pass

    @abstractmethod
    def run(self):
        pass

    def create_data(self, **kwargs):
        return dict(event_id=self.payload.id, event_type=self.payload.type, **kwargs)
