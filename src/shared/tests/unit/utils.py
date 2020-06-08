# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import json

from flask import Response
from typing import Dict, Any

from hub.vendor.controller import StripeHubEventPipeline, event_process, view

CWD = os.path.realpath(os.path.dirname(__file__))


def run_test(filename, cwd=CWD) -> None:
    with open(os.path.join(cwd, filename)) as f:
        pipeline = StripeHubEventPipeline(json.load(f))
        pipeline.run()


def run_view(request) -> None:
    view()


def run_event_process(event) -> Response:
    return event_process(event)


class MockSqsClient:
    @staticmethod
    def list_queues(QueueNamePrefix=None) -> Any:  # type: ignore
        return {"QueueUrls": ["DevSub"]}

    @staticmethod
    def send_message(QueueUrl=None, MessageBody=None) -> Any:  # type: ignore
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}


class MockSnsClient:
    @staticmethod
    def publish(  # type: ignore
        Message: dict = None, MessageStructure: str = "json", TopicArn: str = None
    ) -> Dict[str, Dict[str, int]]:
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}
