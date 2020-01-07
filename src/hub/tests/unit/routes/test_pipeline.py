# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import time
import json

from unittest import TestCase
from mock import patch
from typing import NamedTuple

import pytest

from hub.routes.pipeline import RoutesPipeline, AllRoutes
from hub.routes.static import StaticRoutes
from hub.routes.firefox import FirefoxRoute
from hub.shared.exceptions import UnsupportedStaticRouteError, UnsupportedDataError
from shared.log import get_logger

logger = get_logger()


class MockClient:
    client_type = "sns"

    def publish(self, TopicArn, Message, MessageStructure):
        if TopicArn is None:
            raise ClientError(
                operation_name="test", error_response={"error": "test error"}
            )
        return dict(MessageId="Test123", ResponseMetadata=dict(HTTPStatusCode=200))


class AllRoutesTest(TestCase):
    def setUp(self) -> None:
        run_pipeline_patcher = patch("hub.routes.pipeline.AllRoutes.run")
        pipeline_patcher = patch("hub.routes.pipeline.AllRoutes")
        sns_client_patch = patch("boto3.client")
        salesforce_route_patcher = patch("hub.routes.salesforce.SalesforceRoute.route")
        salesforce_send_patcher = patch(
            "hub.routes.pipeline.AllRoutes.send_to_salesforce"
        )
        expected_data = dict(
            route_type="salesforce_route", data={"event_id": "some_event"}
        )
        self.expected_salesforce_data = [expected_data]

        self.addCleanup(pipeline_patcher.stop)
        self.addCleanup(run_pipeline_patcher.stop)
        self.addCleanup(sns_client_patch.stop)
        self.addCleanup(salesforce_route_patcher.stop)
        self.addCleanup(salesforce_send_patcher.stop)

        self.mock_pipeline = pipeline_patcher.start()
        self.mock_run_pipeline = run_pipeline_patcher.start()
        self.sns_client = sns_client_patch.start()
        self.salesforce_route = salesforce_route_patcher.start()
        self.salesforce_send = salesforce_send_patcher.start()

    def test_salesforce_route(self):
        self.salesforce_send.return_value = 200
        route = AllRoutes(self.expected_salesforce_data)
        route_ran = route.run()
        assert route_ran

    def test_invalid_route(self):
        report_route = ["invalid_route"]
        self.mock_run_pipeline.return_value = UnsupportedStaticRouteError(
            report_route, StaticRoutes
        )
        expected_data = [dict(route_type="invalid_route", data=None)]
        route = AllRoutes(expected_data)
        with pytest.raises(UnsupportedDataError):
            route.run()


class RouteTest(TestCase):
    def setUp(self) -> None:
        run_pipeline_patcher = patch("hub.routes.pipeline.RoutesPipeline.run")
        pipeline_patcher = patch("hub.routes.pipeline.RoutesPipeline")
        sns_client_patch = patch("boto3.client")
        salesforce_route_patcher = patch("hub.routes.salesforce.SalesforceRoute.route")
        salesforce_send_patcher = patch(
            "hub.routes.pipeline.RoutesPipeline.send_to_salesforce"
        )

        self.addCleanup(pipeline_patcher.stop)
        self.addCleanup(run_pipeline_patcher.stop)
        self.addCleanup(sns_client_patch.stop)
        self.addCleanup(salesforce_route_patcher.stop)
        self.addCleanup(salesforce_send_patcher.stop)

        self.mock_pipeline = pipeline_patcher.start()
        self.mock_run_pipeline = run_pipeline_patcher.start()
        self.sns_client = sns_client_patch.start()
        self.salesforce_route = salesforce_route_patcher.start()
        self.salesforce_send = salesforce_send_patcher.start()

    def test_salesforce_route(self):
        expected_data = {"event_id": "some_event"}
        report_route = ["salesforce_route"]
        self.salesforce_send.return_value = 200
        route = RoutesPipeline(report_route, json.dumps(expected_data))
        route_ran = route.run()
        assert route_ran

    def test_invalid_route(self):
        expected_data = {"some": "value"}
        report_route = ["invalid_route"]
        self.mock_run_pipeline.return_value = UnsupportedStaticRouteError(
            report_route, StaticRoutes
        )
        route = RoutesPipeline(report_route, expected_data)
        with pytest.raises(UnsupportedStaticRouteError):
            route.run()


class FirefoxRouteTest(TestCase):
    def setUp(self) -> None:
        sns_client_patch = patch("boto3.client")

        self.addCleanup(sns_client_patch.stop)

        self.sns_client = sns_client_patch.start()

    def test_firefox_route(self):
        expected_data = {"event_id": "some_event"}
        report_route = ["firefox_route"]
        self.sns_client.return_value = MockClient()
        route = RoutesPipeline(report_route, json.dumps(expected_data))
        route_ran = route.run()
        assert route_ran["ResponseMetadata"]["HTTPStatusCode"] == 200


class FirefoxAllRouteTest(TestCase):
    def setUp(self) -> None:
        self.expected_firefox_data = [
            dict(route_type="firefox_route", data=dict(event_id="some_event"))
        ]

        sns_client_patch = patch("boto3.client")

        self.addCleanup(sns_client_patch.stop)

        self.sns_client = sns_client_patch.start()

    def test_firefox_route(self):
        self.sns_client.return_value = MockClient()
        route = AllRoutes(self.expected_firefox_data)
        route_ran = route.run()
        assert route_ran["ResponseMetadata"]["HTTPStatusCode"] == 200
