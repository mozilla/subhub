import logging
import uuid
import json
from subhub.api.payments import subscribe_to_plan
from subhub.tests.unit.stripe.utils import MockSubhubAccount
from unittest.mock import Mock
import os

logging.basicConfig(level=logging.DEBUG)


class MockCustomer:
    id = None
    object = "customer"
    subscriptions = [{"data": "somedata"}]


def getFile(filename):
    with open(os.path.join(os.path.realpath(os.path.dirname(__file__)), filename)) as f:
        return json.load(f)


def test_subscribe_to_plan_returns_newest(monkeypatch):
    uid = uuid.uuid4()

    subhub_account = Mock(return_value=MockSubhubAccount())

    customer = Mock(return_value=MockCustomer())
    none = Mock(return_value=None)
    updated_customer = Mock(
        return_value={
            "subscriptions": {
                "data": [
                    getFile("subscription1.json"),
                    getFile("subscription2.json"),
                    getFile("subscription3.json"),
                ]
            }
        }
    )

    monkeypatch.setattr("flask.g", subhub_account)
    monkeypatch.setattr("subhub.api.payments.existing_or_new_customer", customer)
    monkeypatch.setattr("subhub.api.payments.has_existing_plan", none)
    monkeypatch.setattr("stripe.Subscription.create", Mock)
    monkeypatch.setattr("stripe.Customer.retrieve", updated_customer)

    data = json.dumps(
        {
            "pmt_token": "tok_visa",
            "plan_id": "plan_EtMcOlFMNWW4nd",
            "orig_system": "Test_system",
            "email": "subtest@tester.com",
        }
    )

    test_customer = subscribe_to_plan(uid, json.loads(data))

    assert test_customer[0]["subscriptions"][0]["current_period_start"] == 1516229999
