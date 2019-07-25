#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import json

from subhub.cfg import CFG
from subhub import secrets
from subhub.hub.stripe.controller import StripeHubEventPipeline, event_process, view

__location__ = os.path.realpath(os.path.dirname(__file__))


def run_test(filename):
    with open(os.path.join(__location__, filename)) as f:
        pipeline = StripeHubEventPipeline(json.load(f))
        pipeline.run()


def run_view(request):
    view()


def run_event_process(event):
    return event_process(event)


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
