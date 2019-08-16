# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import json

from sub.shared.cfg import CFG
from sub.shared import secrets

__location__ = os.path.realpath(os.path.dirname(__file__))


class MockSqsClient:
    def list_queues(QueueNamePrefix={}):
        return {"QueueUrls": ["DevSub"]}

    def send_message(QueueUrl={}, MessageBody={}):
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}


class MockSnsClient:
    def publish(
        Message: dict = None, MessageStructure: str = "json", TopicArn: str = None
    ):
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}


class MockSubhubAccount:
    def subhub_account(self):
        pass


class MockSubhubUser:
    id = "123"
    cust_id = "cust_123"
