import json
import requests

from subhub.api.webhooks.routes.abstract import AbstractRoute
from subhub.cfg import CFG

from subhub.log import get_logger

logger = get_logger()


class SalesforceRoute(AbstractRoute):
    def route(self):
        route_payload = json.loads(self.payload)
        requests.post(CFG.SALESFORCE_BASKET_URI, data=route_payload)
        self.report_route(route_payload, "salesforce")
        logger.info("sending to salesforce", payload=self.payload)
