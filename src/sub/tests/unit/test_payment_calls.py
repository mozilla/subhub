# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import os

import pytest

from flask import g
from stripe import Customer
from stripe.error import InvalidRequestError
from unittest.mock import Mock, MagicMock, PropertyMock
from mockito import when, mock
from pynamodb.exceptions import DeleteError

from sub import payments
from sub.customer import create_customer, subscribe_customer, existing_or_new_customer
from sub.tests.unit.utils import MockSubhubUser
from sub.shared.log import get_logger

logger = get_logger()
THIS_PATH = os.path.join(os.path.realpath(os.path.dirname(__file__)))


class MockCustomer:
    id = 123
    object = "customer"
    subscriptions = [{"data": "somedata"}]
    metadata = {"userid": "123"}

    def properties(self, cls):
        return [i for i in cls.__dict__.keys() if i[:1] != "_"]

    def get(self, key, default=None):
        properties = self.properties(MockCustomer)
        logger.info("mock properties", properties=properties)
        if key in properties:
            return key
        else:
            return default

    def __iter__(self):
        yield "subscriptions", self.subscriptions


def get_file(filename, path=THIS_PATH, **overrides):
    with open(f"{path}/customer/{filename}") as f:
        obj = json.load(f)
        return dict(obj, **overrides)


def test_create_customer_invalid_origin_system(monkeypatch):
    """
    GIVEN create a stripe customer
    WHEN An invalid origin system is provided
    THEN An exception should be raised
    """
    origin_system = "NOT_VALID"
    with pytest.raises(InvalidRequestError) as request_error:
        create_customer(
            g.subhub_account,
            user_id="test_mozilla",
            source_token="tok_visa",
            email="test_visa@tester.com",
            origin_system=origin_system,
            display_name="John Tester",
        )
    msg = f"origin_system={origin_system} not one of allowed origin system values, please contact a system administrator in the #subscription-platform channel."
    assert msg == str(request_error.value)


def test_existing_or_new_customer_invalid_origin_system():
    """
    GIVEN create a stripe customer
    WHEN An invalid origin system is provided
    THEN An exception should be raised
    """
    origin_system = "NOT_VALID"
    with pytest.raises(InvalidRequestError) as request_error:
        existing_or_new_customer(
            g.subhub_account,
            user_id="test_mozilla",
            source_token="tok_visa",
            email="test_visa@tester.com",
            origin_system=origin_system,
            display_name="John Tester",
        )
    msg = f"origin_system={origin_system} not one of allowed origin system values, please contact a system administrator in the #subscription-platform channel."
    assert msg == str(request_error.value)


def test_create_customer(monkeypatch):
    """
    GIVEN create a stripe customer
    WHEN provided a test visa token and test fxa
    THEN validate the customer metadata is correct
    """
    mock_possible_customers = MagicMock()
    data = PropertyMock(return_value=[])
    type(mock_possible_customers).data = data

    mock_customer = MagicMock()
    id = PropertyMock(return_value="cust_123")
    type(mock_customer).id = id

    subhub_account = MagicMock()

    mock_user = MagicMock()
    user_id = PropertyMock(return_value="user_123")
    cust_id = PropertyMock(return_value="cust_123")
    type(mock_user).user_id = user_id
    type(mock_user).cust_id = cust_id

    mock_save = MagicMock(return_value=True)

    subhub_account.new_user = mock_user
    subhub_account.save_user = mock_save

    monkeypatch.setattr("stripe.Customer.list", mock_possible_customers)
    monkeypatch.setattr("stripe.Customer.create", mock_customer)

    customer = create_customer(
        subhub_account,
        user_id="user_123",
        source_token="tok_visa",
        email="test_visa@tester.com",
        origin_system="Test_system",
        display_name="John Tester",
    )

    assert customer is not None


def test_create_customer_tok_invalid(monkeypatch):
    """
    GIVEN create a stripe customer
    WHEN provided an invalid test token and test userid
    THEN validate the customer metadata is correct
    """
    mock_possible_customers = MagicMock()
    data = PropertyMock(return_value=[])
    type(mock_possible_customers).data = data

    mock_customer_error = Mock(
        side_effect=InvalidRequestError(
            message="Customer instance has invalid ID",
            param="customer_id",
            code="invalid",
        )
    )

    subhub_account = MagicMock()

    mock_user = MagicMock()
    user_id = PropertyMock(return_value="user_123")
    cust_id = PropertyMock(return_value="cust_123")
    type(mock_user).user_id = user_id
    type(mock_user).cust_id = cust_id

    mock_save = MagicMock(return_value=True)

    subhub_account.new_user = mock_user
    subhub_account.save_user = mock_save

    monkeypatch.setattr("stripe.Customer.list", mock_possible_customers)
    monkeypatch.setattr("stripe.Customer.create", mock_customer_error)

    with pytest.raises(InvalidRequestError):
        create_customer(
            subhub_account,
            user_id="test_mozilla",
            source_token="tok_invalid",
            email="test_invalid@tester.com",
            origin_system="Test_system",
            display_name="John Tester",
        )


def test_subscribe_customer(monkeypatch):
    """
    GIVEN create a subscription
    WHEN provided a customer and plan
    THEN validate subscription is created
    """
    mock_customer = MagicMock()
    id = PropertyMock(return_value="cust_123")
    type(mock_customer).id = id

    mock_subscription = MagicMock()

    monkeypatch.setattr("stripe.Subscription.create", mock_subscription)

    subscription = subscribe_customer(mock_customer, "plan_EtMcOlFMNWW4nd")
    assert subscription is not None


def test_subscribe_customer_invalid_data(monkeypatch):
    """
    GIVEN create a subscription
    WHEN provided a customer and plan
    THEN validate subscription is created
    """
    mock_customer = MagicMock()
    id = PropertyMock(return_value="cust_123")
    type(mock_customer).id = id

    mock_subscribe = Mock(side_effect=InvalidRequestError)

    monkeypatch.setattr("stripe.Subscription.create", mock_subscribe)

    with pytest.raises(InvalidRequestError):
        subscribe_customer(mock_customer, "invalid_plan_id")


def test_subscribe_customer_existing(app, monkeypatch):
    """
    GIVEN create a subscription
    WHEN provided a customer and plan
    THEN validate subscription is created
    """
    client = app.app.test_client()

    plans_data = [
        {
            "id": "plan_123",
            "product": "prod_1",
            "interval": "month",
            "amount": 25,
            "currency": "usd",
            "nickname": "Plan 1",
        },
        {
            "id": "plan_2",
            "product": "prod_1",
            "interval": "year",
            "amount": 250,
            "currency": "usd",
            "nickname": "Plan 2",
        },
    ]

    product_data = {"name": "Product 1"}

    plans = Mock(return_value=plans_data)

    product = Mock(return_value=product_data)

    subhub_account = MagicMock()

    get_user = MagicMock()
    user_id = PropertyMock(return_value="user123")
    cust_id = PropertyMock(return_value="cust123")
    type(get_user).user_id = user_id
    type(get_user).cust_id = cust_id

    subhub_account.get_user = get_user

    stripe_customer = Mock(
        return_value={
            "metadata": {"userid": "user123"},
            "subscriptions": {
                "data": [{"plan": {"id": "plan_123"}, "status": "active"}]
            },
            "sources": {
                "data": [
                    {
                        "funding": "blah",
                        "last4": "1234",
                        "exp_month": "02",
                        "exp_year": "2020",
                    }
                ]
            },
        }
    )
    mock_true = Mock(return_value=True)

    monkeypatch.setattr("stripe.Plan.list", plans)
    monkeypatch.setattr("stripe.Product.retrieve", product)
    monkeypatch.setattr("sub.payments.has_existing_plan", mock_true)
    monkeypatch.setattr("flask.g.subhub_account", subhub_account)
    monkeypatch.setattr("stripe.Customer.retrieve", stripe_customer)

    path = "v1/sub/customer/user123/subscriptions"
    data = {
        "pmt_token": "tok_visa",
        "plan_id": "plan_123",
        "origin_system": "Test_system",
        "email": "user123@example.com",
        "display_name": "John Tester",
    }

    response = client.post(
        path,
        headers={"Authorization": "fake_payment_api_key"},
        data=json.dumps(data),
        content_type="application/json",
    )
    logger.info("response data", data=response.data)
    assert response.status_code == 409


def test_cancel_subscription_no_subscription_found(monkeypatch):

    """
    GIVEN call to cancel subscription
    WHEN there is no active subscription
    THEN return the appropriate message
    Subscription.modify(sub_id, cancel_at_period_end=True)
    """
    with monkeypatch.context() as m:
        user = Mock(return_value=MockSubhubUser())
        subscription_data = {
            "id": "sub_123",
            "status": "deleted",
            "current_period_end": 1566833524,
            "current_period_start": 1564155124,
            "ended_at": None,
            "plan": {"id": "plan_123", "nickname": "Monthly VPN Subscription"},
            "cancel_at_period_end": False,
        }
        customer = MagicMock(
            return_value={
                "id": "123",
                "cust_id": "cust_123",
                "metadata": {"userid": "123"},
                "subscriptions": {"data": [subscription_data]},
            }
        )
        cancel_response = mock(
            {
                "id": "cus_tester3",
                "object": "customer",
                "subscriptions": {"data": []},
                "sources": {"data": [{"id": "sub_123", "cancel_at_period_end": True}]},
            },
            spec=Customer,
        )
        delete_response = mock(
            {"id": "cus_tester3", "object": "customer", "sources": []}, spec=Customer
        )
        when(Customer).delete_source("cus_tester3", "src_123").thenReturn(
            delete_response
        )
        m.setattr("flask.g.subhub_account.get_user", user)
        m.setattr("stripe.Customer.retrieve", customer)
        m.setattr("sub.customer.fetch_customer", customer)
        m.setattr("sub.payments.retrieve_stripe_subscriptions", cancel_response)
        cancel_sub, code = payments.cancel_subscription("123", "sub_123")
        logger.info("cancel sub", cancel_sub=cancel_sub)
        assert "Subscription not available." in cancel_sub["message"]
        assert code == 400


def test_cancel_subscription_without_valid_user(monkeypatch):
    """
    GIVEN call to cancel subscription
    WHEN an invalid customer is sent
    THEN return the appropriate message
    """
    customer = Mock(return_value=None)
    monkeypatch.setattr("sub.customer.fetch_customer", customer)
    cancel_sub, code = payments.cancel_subscription("bob_123", "sub_123")
    assert "Customer does not exist." in cancel_sub["message"]
    assert code == 404


def test_delete_user_from_db(app, create_subscription_for_processing):
    """
    GIVEN should delete user from user table
    WHEN provided with a valid user id
    THEN add to deleted users table
    """
    deleted_user = payments.delete_user("process_test", "sub_id", "origin")
    logger.info("deleted user from db", deleted_user=deleted_user)
    assert isinstance(deleted_user, MagicMock)


def test_delete_user_from_db2(app, create_subscription_for_processing, monkeypatch):
    """
    GIVEN raise DeleteError
    WHEN an entry cannot be removed from the database
    THEN validate error message
    """
    subhub_account = MagicMock()
    subhub_account.remove_from_db.return_value = False

    delete_error = False
    monkeypatch.setattr("flask.g.subhub_account", subhub_account)
    monkeypatch.setattr("sub.shared.db.SubHubAccount.remove_from_db", delete_error)

    du = payments.delete_user("process_test_2", "sub_id", "origin")
    assert du is False


def test_add_user_to_deleted_users_record(monkeypatch):
    """
    GIVEN Add user to deleted users record
    WHEN provided a user id, cust id and origin system
    THEN return subhud_deleted user
    """
    customer = Mock(
        return_value={
            "user_id": "process_customer",
            "cust_id": "cus_123",
            "origin_system": "Test_system",
        }
    )
    monkeypatch.setattr("flask.g.subhub_account.get_user", customer)
    to_delete = g.subhub_account.get_user("process_customer")
    logger.info("delete", deleted_user=to_delete)
    deleted_user = payments.add_user_to_deleted_users_record(
        user_id=to_delete["user_id"],
        cust_id=to_delete["cust_id"],
        origin_system=to_delete["origin_system"],
    )
    assert deleted_user.user_id == "process_customer"
    assert deleted_user.origin_system == "Test_system"
    assert "cus_" in deleted_user.cust_id


def test_cancel_subscription_with_invalid_subhub_user(monkeypatch):
    """
    GIVEN an active subscription
    WHEN provided an api_token and an invalid userid
    THEN return customer not found error
    """
    cancelled, code = payments.cancel_subscription("invalid_user", "subscription_id")
    assert 404 == code
    assert cancelled["message"] == "Customer does not exist."


def test_update_payment_method_missing_stripe_customer(monkeypatch):
    """
    GIVEN api_token, userid, pmt_token
    WHEN provided user with missing stripe customer id
    THEN return missing customer
    """
    subhub_account = MagicMock()

    get_user = MagicMock()
    user_id = PropertyMock(return_value=None)
    cust_id = PropertyMock(return_value=None)
    type(get_user).user_id = user_id
    type(get_user).cust_id = cust_id

    subhub_account.get_user = get_user
    monkeypatch.setattr("sub.customer.fetch_customer", subhub_account)

    updated_pmt, code = payments.update_payment_method(
        "process_test1", {"pmt_token": "tok_invalid"}
    )
    assert 404 == code


def test_customer_update_success(monkeypatch):

    subhub_account = MagicMock()

    get_user = MagicMock()
    user_id = PropertyMock(return_value="user123")
    cust_id = PropertyMock(return_value="cust123")
    type(get_user).user_id = user_id
    type(get_user).cust_id = cust_id

    subhub_account.get_user = get_user

    stripe_customer = Mock(
        return_value={
            "metadata": {"userid": "user123"},
            "subscriptions": {"data": []},
            "sources": {
                "data": [
                    {
                        "funding": "blah",
                        "last4": "1234",
                        "exp_month": "02",
                        "exp_year": "2020",
                    }
                ]
            },
        }
    )

    monkeypatch.setattr("flask.g.subhub_account", subhub_account)
    monkeypatch.setattr("stripe.Customer.retrieve", stripe_customer)

    data, code = payments.customer_update("user123")
    assert 200 == code


def test_reactivate_subscription_success(monkeypatch):
    """
    GIVEN a user with active subscriptions
    WHEN a user attempts to reactivate a subscription flagged for cancellation
    THEN the subscription is updated
    """
    uid = "subhub_user"
    cust_id = "cust_1"
    sub_id = "sub_123"

    subhub_user = Mock(return_value=MockSubhubUser())
    subhub_user.cust_id = cust_id
    subhub_user.id = uid

    stripe_customer = Mock(
        return_value={
            "subscriptions": {
                "data": [
                    {
                        "id": "sub_121",
                        "status": "active",
                        "cancel_at_period_end": False,
                    },
                    {"id": sub_id, "status": "active", "cancel_at_period_end": True},
                ]
            }
        }
    )

    none = Mock(return_value=None)

    monkeypatch.setattr("flask.g.subhub_account.get_user", subhub_user)
    monkeypatch.setattr("stripe.Customer.retrieve", stripe_customer)
    monkeypatch.setattr("stripe.Subscription.modify", none)

    response, code = payments.reactivate_subscription(uid, sub_id)

    assert 200 == code
    assert "Subscription reactivation was successful." == response["message"]


def test_reactivate_subscription_already_active(monkeypatch):
    """
    GIVEN a user with active subscriptions
    WHEN a user attempts to reactivate a subscription not flagged for cancellation
    THEN the subscription does not change states
    """

    uid = "subhub_user"
    cust_id = "cust_1"
    sub_id = "sub_123"

    subhub_user = Mock(return_value=MockSubhubUser())
    subhub_user.cust_id = cust_id
    subhub_user.id = uid

    stripe_customer = Mock(
        return_value={
            "subscriptions": {
                "data": [
                    {
                        "id": "sub_121",
                        "status": "active",
                        "cancel_at_period_end": False,
                    },
                    {"id": sub_id, "status": "active", "cancel_at_period_end": False},
                ]
            }
        }
    )

    none = Mock(return_value=None)

    monkeypatch.setattr("flask.g.subhub_account.get_user", subhub_user)
    monkeypatch.setattr("stripe.Customer.retrieve", stripe_customer)
    monkeypatch.setattr("stripe.Subscription.modify", none)

    response, code = payments.reactivate_subscription(uid, sub_id)

    assert 200 == code
    assert "Subscription is already active." == response["message"]


def test_reactivate_subscription_no_subscriptions(monkeypatch):
    """
    GIVEN a user with no active subscriptions
    WHEN a user attempts to reactivate a subscription
    THEN a subscription not found error is returned
    """

    uid = "subhub_user"
    cust_id = "cust_1"
    sub_id = "sub_123"

    subhub_user = Mock(return_value=MockSubhubUser())
    subhub_user.cust_id = cust_id
    subhub_user.id = uid

    stripe_customer = Mock(return_value={"subscriptions": {"data": []}})

    none = Mock(return_value=None)

    monkeypatch.setattr("flask.g.subhub_account.get_user", subhub_user)
    monkeypatch.setattr("stripe.Customer.retrieve", stripe_customer)
    monkeypatch.setattr("stripe.Subscription.modify", none)

    response, code = payments.reactivate_subscription(uid, sub_id)

    assert 404 == code
    assert "Current subscription not found." == response["message"]


def test_reactivate_subscription_bad_subscription_id(monkeypatch):
    """
    GIVEN a user with active subscriptions
    WHEN a user attempts to reactivate an invalid subscription
    THEN a subscription not found error is returned
    """

    uid = "subhub_user"
    cust_id = "cust_1"
    sub_id = "sub_123"

    subhub_user = Mock(return_value=MockSubhubUser())
    subhub_user.cust_id = cust_id
    subhub_user.id = uid

    stripe_customer = Mock(
        return_value={
            "subscriptions": {
                "data": [
                    {
                        "id": "sub_121",
                        "status": "active",
                        "cancel_at_period_end": False,
                    },
                    {
                        "id": "sub_122",
                        "status": "active",
                        "cancel_at_period_end": False,
                    },
                ]
            }
        }
    )

    none = Mock(return_value=None)

    monkeypatch.setattr("flask.g.subhub_account.get_user", subhub_user)
    monkeypatch.setattr("stripe.Customer.retrieve", stripe_customer)
    monkeypatch.setattr("stripe.Subscription.modify", none)

    response, code = payments.reactivate_subscription(uid, sub_id)

    assert 404 == code
    assert "Current subscription not found." == response["message"]


def test_reactivate_subscription_bad_user_id(monkeypatch):
    """
    GIVEN an invalid user id
    WHEN a user attempts to reactivate an invalid subscription
    THEN a customer not found error is returned
    """

    uid = "subhub_user"
    sub_id = "sub_123"

    none = Mock(return_value=None)

    monkeypatch.setattr("flask.g.subhub_account.get_user", none)

    response, code = payments.reactivate_subscription(uid, sub_id)

    assert 404 == code
    assert "Customer does not exist." == response["message"]
