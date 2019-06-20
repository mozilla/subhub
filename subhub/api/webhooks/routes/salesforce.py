import json
import requests

from subhub.api.webhooks.routes.abstract import AbstractRoute
from subhub.cfg import CFG

from subhub.log import get_logger

logger = get_logger()


class SalesforceRoute(AbstractRoute):
    def route(self):
        route_payload = json.loads(self.payload)
        basket_url = CFG.SALESFORCE_BASKET_URI + CFG.BASKET_API_KEY
        requests.post(basket_url, json=route_payload)
        self.report_route(route_payload, "salesforce")
        logger.info("sending to salesforce", payload=self.payload)
