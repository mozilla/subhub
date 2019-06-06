import os
import json

from subhub.cfg import CFG
from subhub import secrets
from subhub.api.webhooks.stripe.pipeline import StripeWebhookEventPipeline

__location__ = os.path.realpath(os.path.dirname(__file__))


def run_test(filename):
    with open(os.path.join(__location__, filename)) as f:
        pipeline = StripeWebhookEventPipeline(json.load(f))
        pipeline.run()


class MockSqsClient:
    def list_queues(QueueNamePrefix={}):
        return {"QueueUrls": ["DevSub"]}

    def send_message(QueueUrl={}, MessageBody={}):
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}


class MockSubhubAccount:
    def subhub_account(self):
        pass


class MockSubhubUser:
    id = None
    custId = None
