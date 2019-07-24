#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from subhub.hub.routes.firefox import FirefoxRoute
from subhub.hub.routes.salesforce import SalesforceRoute
from subhub.hub.routes.static import StaticRoutes


class RoutesPipeline:
    def __init__(self, report_routes, data):
        self.report_routes = report_routes
        self.data = data

    def run(self):
        for r in self.report_routes:
            if r == StaticRoutes.SALESFORCE_ROUTE:
                SalesforceRoute(self.data).route()
            elif r == StaticRoutes.FIREFOX_ROUTE:
                FirefoxRoute(self.data).route()
            else:
                raise Exception("We do no support " + str(r))
