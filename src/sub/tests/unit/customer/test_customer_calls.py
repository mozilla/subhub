# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import uuid
import json

from unittest.mock import Mock, MagicMock, PropertyMock
from stripe import Customer

from sub.payments import subscribe_to_plan, customer_update, create_update_data
from sub.shared.tests.unit.utils import MockSubhubAccount
from sub.tests.mock_customer import MockCustomer
from shared.log import get_logger

logger = get_logger()


UID = str(uuid.uuid4())
THIS_PATH = os.path.join(os.path.realpath(os.path.dirname(__file__)))


def get_file(filename, path=THIS_PATH, **overrides):
    with open(f"{path}/{filename}") as f:
        obj = json.load(f)
        return dict(obj, **overrides)


# def test_subscribe_to_plan_returns_newest(monkeypatch):
#     subhub_account = MagicMock()
#
#     get_user = MagicMock()
#     user_id = PropertyMock(return_value=UID)
#     cust_id = PropertyMock(return_value="cust123")
#     type(get_user).user_id = user_id
#     type(get_user).cust_id = cust_id
#
#     subhub_account.get_user = get_user
#
#     customer = Mock(return_value=MockCustomer())
#     none = Mock(return_value=None)
#     updated_customer = Mock(
#         return_value={
#             "subscriptions": {
#                 "data": [
#                     get_file("subscription1.json"),
#                     get_file("subscription2.json"),
#                     get_file("subscription3.json"),
#                 ]
#             },
#             "sources": {"data": [{"country": "US"}]},
#         }
#     )
#
#     product = Mock(return_value={"name": "Mozilla Product", "metadata": {}})
#
#     monkeypatch.setattr("flask.g.subhub_account", subhub_account)
#     monkeypatch.setattr("sub.payments.existing_or_new_customer", customer)
#     monkeypatch.setattr("sub.payments.has_existing_plan", none)
#     monkeypatch.setattr("sub.payments.check_customer_country", True)
#     monkeypatch.setattr("stripe.Subscription.create", Mock)
#     monkeypatch.setattr("stripe.Customer.retrieve", updated_customer)
#     monkeypatch.setattr("stripe.Product.retrieve", product)
#
#     data = json.dumps(
#         {
#             "pmt_token": "tok_visa",
#             "plan_id": "plan_EtMcOlFMNWW4nd",
#             "origin_system": "Test_system",
#             "email": "subtest@tester.com",
#             "display_name": "John Tester",
#         }
#     )
#
#     test_customer = subscribe_to_plan(UID, json.loads(data))
#
#     assert test_customer[0]["subscriptions"][0]["current_period_start"] == 1_516_229_999
#     updated_customer.assert_called()


def test_customer_update_subscription_active(monkeypatch):
    updated_customer = Mock(
        return_value={
            "metadata": {"userid": str(UID)},
            "sources": {
                "data": [
                    {
                        "funding": "100",
                        "last4": "6655",
                        "exp_month": "03",
                        "exp_year": "2019",
                    }
                ]
            },
            "subscriptions": {"data": [get_file("subscription_active.json")]},
        }
    )

    charge_retrieve = {"failure_code": "somecode", "failure_message": "somemessage"}

    invoice_retrieve = {"charge": "true"}

    subhub_account = Mock(return_value=MockSubhubAccount())

    product = Mock(return_value={"name": "Mozilla Product", "metadata": {}})

    monkeypatch.setattr("flask.g.subhub_account", subhub_account)
    monkeypatch.setattr("stripe.Customer.retrieve", updated_customer)
    monkeypatch.setattr("stripe.Invoice.retrieve", invoice_retrieve)
    monkeypatch.setattr("stripe.Charge.retrieve", charge_retrieve)
    monkeypatch.setattr("stripe.Product.retrieve", product)

    customer_update(str(UID))

    updated_customer.assert_called()


def test_customer_update_subscription_cancel_at_period_end(monkeypatch):
    updated_customer = Mock(
        return_value={
            "metadata": {"userid": str(UID)},
            "sources": {
                "data": [
                    {
                        "funding": "100",
                        "last4": "6655",
                        "exp_month": "03",
                        "exp_year": "2019",
                    }
                ]
            },
            "subscriptions": {
                "data": [
                    get_file("subscription_active.json", cancel_at_period_end=True)
                ]
            },
        }
    )

    subhub_account = Mock(return_value=MockSubhubAccount())

    product = Mock(return_value={"name": "Mozilla Product", "metadata": {}})

    monkeypatch.setattr("flask.g.subhub_account", subhub_account)
    monkeypatch.setattr("stripe.Customer.retrieve", updated_customer)
    monkeypatch.setattr("stripe.Product.retrieve", product)

    result = customer_update(str(UID))

    updated_customer.assert_called()
    assert result[0]["subscriptions"][0]["cancel_at_period_end"] == True


def test_customer_update_subscription_incomplete_charge_null(monkeypatch):
    customer_update_subscription_incomplete(monkeypatch, False)


def customer_update_subscription_incomplete(monkeypatch, charge):
    updated_customer = Mock(
        return_value={
            "metadata": {"userid": str(UID)},
            "sources": {
                "data": [
                    {
                        "funding": "100",
                        "last4": "6655",
                        "exp_month": "03",
                        "exp_year": "2019",
                    }
                ]
            },
            "subscriptions": {
                "data": [
                    get_file("subscription_incomplete.json", cancel_at_period_end=True)
                ]
            },
        },
        wraps=Customer,
    )

    charge_retrieve = Mock(
        return_value={"failure_code": "somecode", "failure_message": "somemessage"}
    )

    invoice_retrieve = Mock(return_value={"charge": charge})
    subhub_account = Mock(return_value=MockSubhubAccount())
    product = Mock(return_value={"name": "Mozilla Product", "metadata": {}})

    monkeypatch.setattr("stripe.Invoice.retrieve", invoice_retrieve)
    monkeypatch.setattr("flask.g.subhub_account", subhub_account)
    monkeypatch.setattr("stripe.Customer.retrieve", updated_customer)
    monkeypatch.setattr("stripe.Charge.retrieve", charge_retrieve)
    monkeypatch.setattr("stripe.Product.retrieve", product)

    result = customer_update(str(UID))

    updated_customer.assert_called()
    invoice_retrieve.assert_called()
    assert result[0]["subscriptions"][0]["cancel_at_period_end"] is True
