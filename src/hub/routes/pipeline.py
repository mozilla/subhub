# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from routes.firefox import FirefoxRoute
from routes.salesforce import SalesforceRoute
from routes.static import StaticRoutes
from src.shared.exceptions import UnsupportedStaticRouteError, UnsupportedDataError


class RoutesPipeline:
    def __init__(self, report_routes, data) -> None:
        self.report_routes = report_routes
        self.data = data

    def run(self) -> None:
        for r in self.report_routes:
            if r == StaticRoutes.SALESFORCE_ROUTE:
                SalesforceRoute(self.data).route()
            elif r == StaticRoutes.FIREFOX_ROUTE:
                FirefoxRoute(self.data).route()
            else:
                raise UnsupportedStaticRouteError(r, StaticRoutes)


class AllRoutes:
    def __init__(self, messages_to_routes) -> None:
        self.messages_to_routes = messages_to_routes

    def run(self) -> None:
        for m in self.messages_to_routes:
            if m["type"] == "firefox_route":
                FirefoxRoute(m["data"]).route()
            elif m["type"] == "salesforce_route":
                SalesforceRoute(m["data"]).route()
            else:
                raise UnsupportedDataError(m, m["type"], StaticRoutes)
