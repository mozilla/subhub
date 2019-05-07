import logging
import json
import requests

from subhub.api.webhooks.routes.abstract import AbstractRoute
from subhub.cfg import CFG
from subhub import secrets


logger = logging.getLogger("salesforce_route")
log_handle = logging.StreamHandler()
log_handle.setLevel(logging.INFO)
logformat = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log_handle.setFormatter(logformat)
logger.addHandler(log_handle)


class SalesforceRoute(AbstractRoute):
    def route(self):
        route_payload = json.loads(self.payload)
        uri = CFG.SALESFORCE_BASKET_URI
        requests.post(uri, data=route_payload)
        logger.info("start report")
        self.report_route(route_payload, "salesforce")
        logger.info(f"sending to salesforce : {self.payload}")
