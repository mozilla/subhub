from subhub.api.webhooks.routes.firefox import FirefoxRoute
from subhub.api.webhooks.routes.salesforce import SalesforceRoute
from subhub.api.webhooks.routes.static import StaticRoutes


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
