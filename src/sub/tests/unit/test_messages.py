# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json

from unittest import TestCase

from mock import patch, PropertyMock, MagicMock, DEFAULT, Mock
from boto3 import client
from botocore.exceptions import ClientError

from sub.messages import AbstractRoute, Message
from sub.shared.cfg import CFG


class MockClient:
    client_type = "sns"

    def publish(self, TopicArn, Message, MessageStructure):
        if TopicArn is None:
            raise ClientError(
                operation_name="test", error_response={"error": "test error"}
            )
        return dict(MessageId="Test123", ResponseMetadata=dict(HTTPStatusCode=200))


class TestMessages(TestCase):
    def setUp(self) -> None:
        sns_client_patch = patch("boto3.client")
        self.addCleanup(sns_client_patch.stop)
        self.sns_client = sns_client_patch.start()

    def test_abstract(self):
        payload = {"id": 123}
        ar = AbstractRoute(json.dumps(payload))
        assert ar

    def test_sns(self):
        self.sns_client.return_value = MockClient()
        sns = Message({"id": 123}).route()
        assert sns["ResponseMetadata"]["HTTPStatusCode"] == 200

    def test_route_fail(self):
        sns = Message({"id": 123}).route()
        assert sns["ResponseMetadata"]["HTTPStatusCode"] == 500

    def test_client_error(self):
        my_client = client("sns", region_name=CFG.AWS_REGION)
        with self.assertRaises(ClientError):
            Message({"id": "123"}).publish_sns_message(my_client, "", {"id": "123"})
