# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import json

from flask import Response
from typing import Dict, Any

from hub.vendor.controller import StripeHubEventPipeline, event_process, view

__location__ = os.path.realpath(os.path.dirname(__file__))


def run_test(filename) -> None:
    with open(os.path.join(__location__, filename)) as f:
        pipeline = StripeHubEventPipeline(json.load(f))
        pipeline.run()


def run_view(request) -> None:
    view()


def run_event_process(event) -> Response:
    return event_process(event)


class MockSqsClient:
    def list_queues(QueueNamePrefix=None) -> Any:  # type: ignore
        return {"QueueUrls": ["DevSub"]}

    def send_message(QueueUrl=None, MessageBody=None) -> Any:  # type: ignore
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}


class MockSnsClient:
    def publish(  # type: ignore
        Message: dict = None, MessageStructure: str = "json", TopicArn: str = None
    ) -> Dict[str, Dict[str, int]]:
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}


class MockSubhubAccount:
    def subhub_account(self) -> None:
        pass


class MockSubhubUser:
    id = "123"
    cust_id = "cust_123"
