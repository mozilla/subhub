# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from typing import Any, Dict, Optional, List

from hub.routes.firefox import FirefoxRoute
from hub.routes.salesforce import SalesforceRoute
from hub.routes.static import StaticRoutes
from hub.shared.exceptions import UnsupportedStaticRouteError, UnsupportedDataError


class RoutesPipeline:
    def __init__(self, report_routes, data) -> None:
        self.report_routes = report_routes
        self.data = data

    def run(self) -> Optional[Any]:
        for r in self.report_routes:
            if r == StaticRoutes.SALESFORCE_ROUTE:
                return self.send_to_salesforce(self.data)
            elif r == StaticRoutes.FIREFOX_ROUTE:
                return self.send_to_firefox(self.data)
            else:
                raise UnsupportedStaticRouteError(r, StaticRoutes)  # type: ignore

    def send_to_salesforce(self, data: Dict[str, Any]) -> int:
        salesforce_send = SalesforceRoute(data).route()
        return salesforce_send

    def send_to_firefox(self, data: Dict[str, Any]) -> Dict[str, Any]:
        firefox_send = FirefoxRoute(data).route()
        return firefox_send


class AllRoutes:
    def __init__(self, messages_to_routes: List[Dict[str, Any]]) -> None:
        self.messages_to_routes = messages_to_routes

    def run(self) -> Optional[Any]:
        for m in self.messages_to_routes:
            if m["route_type"] == "firefox_route":
                return self.send_to_firefox(data=m.get("data"))
            elif m["route_type"] == "salesforce_route":
                return self.send_to_salesforce(data=m.get("data"))
            else:
                raise UnsupportedDataError(  # type: ignore
                    m, m["route_type"], StaticRoutes
                )

    @staticmethod
    def send_to_salesforce(data: Dict[str, Any]) -> int:
        salesforce_send = SalesforceRoute(data).route()
        return salesforce_send

    @staticmethod
    def send_to_firefox(data: Dict[str, Any]) -> Dict[str, Any]:
        firefox_send = FirefoxRoute(data).route()
        return firefox_send
