# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import uuid
import json
import asyncio

import pytest
import stripe

from flask import g
from stripe.error import InvalidRequestError
from stripe import Customer
from subhub.exceptions import ClientError
from subhub.app import create_app
from unittest.mock import Mock, MagicMock, PropertyMock, patch
from mockito import when, mock, unstub, ANY

from subhub.sub import payments
from subhub.customer import (
    create_customer,
    subscribe_customer,
    existing_or_new_customer,
)
from subhub.tests.unit.stripe.utils import MockSubhubUser
from subhub.log import get_logger
from subhub.cfg import CFG
from pynamodb.exceptions import DeleteError


logger = get_logger()


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


def test_create_subscription_with_valid_data(monkeypatch):
    """
    GIVEN create a subscription
    WHEN provided a api_token, userid, pmt_token, plan_id, cust_id
    THEN validate subscription is created
    """
    subs = Mock(return_value=({"subscriptions": [{"subscription_id": "sub_123"}]}, 201))
    monkeypatch.setattr("subhub.sub.payments.subscribe_to_plan", subs)
    uid = uuid.uuid4()
    subscription, code = payments.subscribe_to_plan(
        "validcustomer",
        {
            "pmt_token": "tok_visa",
            "plan_id": "plan_EtMcOlFMNWW4nd",
            "email": f"valid@{uid}customer.com",
            "origin_system": "Test_system",
            "display_name": "Jon Tester",
        },
    )
    assert 201 == code
    assert "sub_123" == subscription["subscriptions"][0]["subscription_id"]


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
    monkeypatch.setattr("subhub.sub.payments.has_existing_plan", mock_true)
    monkeypatch.setattr("flask.g.subhub_account", subhub_account)
    monkeypatch.setattr("stripe.Customer.retrieve", stripe_customer)

    path = "v1/customer/user123/subscriptions"
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


def test_create_subscription_with_invalid_plan_id(monkeypatch):
    """
    GIVEN a api_token, userid, pmt_token, plan_id, email
    WHEN the plan_id provided is invalid
    THEN a StripeError is raised
    """
    subs = Mock(
        side_effect=InvalidRequestError(
            message="No such plan:", param="plan", code="no_plan", http_status=404
        )
    )
    monkeypatch.setattr("subhub.sub.payments.subscribe_to_plan", subs)
    exception = None
    try:
        plan, code = payments.subscribe_to_plan(
            "invalid_plan",
            {
                "pmt_token": "tok_visa",
                "plan_id": "plan_abc123",
                "email": "invalid_plan@tester.com",
                "origin_system": "Test_system",
                "display_name": "Jon Tester",
            },
        )
    except Exception as e:
        exception = e

    assert isinstance(exception, InvalidRequestError)
    assert "No such plan:" in exception.user_message


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
        m.setattr("subhub.customer.fetch_customer", customer)
        m.setattr("subhub.sub.payments.retrieve_stripe_subscriptions", cancel_response)
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
    monkeypatch.setattr("subhub.customer.fetch_customer", customer)
    cancel_sub, code = payments.cancel_subscription("bob_123", "sub_123")
    assert "Customer does not exist." in cancel_sub["message"]
    assert code == 404


def test_cancel_subscription_with_valid_data(monkeypatch):
    """
    GIVEN should cancel an active subscription
    WHEN provided a api_token, and subscription id
    THEN validate should cancel subscription
    """
    user = Mock(return_value=MockSubhubUser())
    user.subscriptions = {"data": [{"id": "sub_123", "status": "active"}]}
    mod_user = Mock(return_value=MockSubhubUser())
    mod_user.subscriptions = {
        "data": [{"id": "sub_123", "status": "inactive", "cancel_at_period_end": True}]
    }
    subscription = {"subscriptions": [{"subscription_id": "sub_123"}]}
    to_cancel = Mock(
        return_value=({"message": "Subscription cancellation successful"}, 201)
    )

    monkeypatch.setattr("stripe.Subscription.modify", mod_user)
    monkeypatch.setattr("flask.g.subhub_account.get_user", user)
    monkeypatch.setattr("subhub.sub.payments.cancel_subscription", to_cancel)
    cancelled, code = payments.cancel_subscription(
        "process_test", subscription["subscriptions"][0]["subscription_id"]
    )
    assert cancelled["message"] == "Subscription cancellation successful"
    assert 201 == code


def test_delete_customer(monkeypatch):
    """
    GIVEN should cancel an active subscription,
    delete customer from payment provider and database
    WHEN provided a user id
    THEN validate user is deleted from payment provider and database
    """
    to_delete = Mock(return_value=({"message": "Customer deleted successfully"}, 201))
    monkeypatch.setattr("subhub.sub.payments.delete_customer", to_delete)
    message, code = payments.delete_customer("process_test")
    assert message["message"] == "Customer deleted successfully"
    to_search = Mock(return_value=({"message": "Customer does not exist"}, 404))
    monkeypatch.setattr("subhub.sub.payments.subscription_status", to_search)
    deleted_message, code = payments.subscription_status("process_test")
    assert "Customer does not exist" in deleted_message["message"]


def test_delete_customer_bad_user(monkeypatch):
    """
    GIVEN should cancel an active subscription,
    delete customer from payment provider and database
    WHEN provided a user id
    THEN validate user is deleted from payment provider and database
    """
    to_delete = Mock(return_value=({"message": "Customer does not exist."}, 404))
    monkeypatch.setattr("subhub.sub.payments.delete_customer", to_delete)
    message, code = payments.delete_customer("process_test2")
    assert message["message"] == "Customer does not exist."
    assert code == 404


def test_delete_user_from_db(monkeypatch):
    """
    GIVEN should delete user from user table
    WHEN provided with a valid user id
    THEN add to deleted users table
    """
    to_delete = Mock(return_value=True)
    monkeypatch.setattr("subhub.sub.payments.delete_user_from_db", to_delete)
    deleted_user = payments.delete_user_from_db("process_test")
    logger.info("deleted user from db", deleted_user=deleted_user)
    assert deleted_user is True


def test_delete_user_from_db2():
    """
    GIVEN raise DeleteError
    WHEN an entry cannot be removed from the database
    THEN validate error message
    """
    delete_error = Mock(side_effect=DeleteError())
    monkeypatch.setattr("subhub.db.SubHubAccount.remove_from_db", delete_error)

    with pytest.raises(DeleteError) as request_error:
        payments.delete_user("process_test_2", "sub_id", "origin")
    msg = "Error deleting item"
    assert msg in str(request_error.value)


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


def test_cancel_subscription_with_valid_data_multiple_subscriptions_remove_first(
    monkeypatch
):
    """
    GIVEN a user with multiple subscriptions
    WHEN the first subscription is cancelled
    THEN the specified subscription is cancelled
    """
    uid = uuid.uuid4()

    async def first_cancel():
        sub, code = await first_sub(uid)
        second_sub(uid)
        cancelled_subs = Mock(
            return_value=({"message": "Subscription cancellation successful"}, 201)
        )
        monkeypatch.setattr("sub.sub.payments.cancel_subscription", cancelled_subs)
        cancelled, code = payments.cancel_subscription(
            "valid_customer", sub["subscriptions"][0]["subscription_id"]
        )
        assert cancelled["message"] == "Subscription cancellation successful"
        assert 201 == code
        monkeypatch.undo()

    async def first_sub(uid):
        first_subscription = Mock(
            return_value=({"subscriptions": [{"subscription_id": "sub_1"}]})
        )
        monkeypatch.setattr("subhub.sub.payments.subscribe_to_plan", first_subscription)
        subscription1, code1 = payments.subscribe_to_plan(
            "valid_customer",
            {
                "pmt_token": "tok_visa",
                "plan_id": "plan_EtMcOlFMNWW4nd",
                "email": f"valid@{uid}customer.com",
                "origin_system": "Test_system",
                "display_name": "Jon Tester",
            },
        )
        monkeypatch.undo()
        return subscription1, code1

    async def second_sub(uid):
        second_subscription = Mock(
            return_value=({"subscriptions": [{"subscription_id": "sub_2"}]})
        )
        monkeypatch.setattr(
            "subhub.sub.payments.subscribe_to_plan", second_subscription
        )
        subscription2, code2 = payments.subscribe_to_plan(
            "valid_customer",
            {
                "pmt_token": "tok_visa",
                "plan_id": "plan_F4G9jB3x5i6Dpj",
                "email": f"valid@{uid}customer.com",
                "origin_system": "Test_system",
                "display_name": "Jon Tester",
            },
        )
        monkeypatch.undo()
        return subscription2, code2

    async def second_cancel():
        await second_sub()
        subscription2, code2 = await second_sub(uid)
        cancelled, code = payments.cancel_subscription(
            "valid_customer", subscription2["subscriptions"][0]["subscription_id"]
        )
        g.subhub_account.remove_from_db("valid_customer")
        assert cancelled["message"] == "Subscription cancellation successful"
        assert 201 == code

    first_cancel()


def test_cancel_subscription_with_valid_data_multiple_subscriptions_remove_second(
    monkeypatch
):
    """
    GIVEN a user with multiple subscriptions
    WHEN the second subscription is cancelled
    THEN the specified subscription is cancelled
    """
    uid = uuid.uuid4()

    async def first_cancel():
        sub, code = await first_sub(uid)
        cancelled_subs = Mock(
            return_value=({"message": "Subscription cancellation successful"}, 201)
        )
        monkeypatch.setattr("sub.sub.payments.cancel_subscription", cancelled_subs)
        cancelled, code = payments.cancel_subscription(
            "valid_customer", sub["subscriptions"][0]["subscription_id"]
        )
        assert cancelled["message"] == "Subscription cancellation successful"
        assert 201 == code
        monkeypatch.undo()

    async def first_sub(uid):
        first_subscription = Mock(
            return_value=({"subscriptions": [{"subscription_id": "sub_1"}]})
        )
        monkeypatch.setattr("subhub.sub.payments.subscribe_to_plan", first_subscription)
        subscription1, code1 = payments.subscribe_to_plan(
            "valid_customer",
            {
                "pmt_token": "tok_visa",
                "plan_id": "plan_EtMcOlFMNWW4nd",
                "email": f"valid@{uid}customer.com",
                "origin_system": "Test_system",
                "display_name": "Jon Tester",
            },
        )
        monkeypatch.undo()
        return subscription1, code1

    async def second_sub(uid):

        second_subscription = Mock(
            return_value=({"subscriptions": [{"subscription_id": "sub_2"}]})
        )
        monkeypatch.setattr(
            "subhub.sub.payments.subscribe_to_plan", second_subscription
        )
        subscription2, code2 = payments.subscribe_to_plan(
            "valid_customer",
            {
                "pmt_token": "tok_visa",
                "plan_id": "plan_F4G9jB3x5i6Dpj",
                "email": f"valid@{uid}customer.com",
                "origin_system": "Test_system",
                "display_name": "Jon Tester",
            },
        )
        monkeypatch.undo()
        return subscription2, code2

    async def second_cancel():
        await first_cancel()
        await second_sub()
        subscription2, code2 = await second_sub(uid)
        cancelled, code = payments.cancel_subscription(
            "valid_customer", subscription2["subscriptions"][0]["subscription_id"]
        )
        g.subhub_account.remove_from_db("valid_customer")
        assert cancelled["message"] == "Subscription cancellation successful"
        assert 201 == code

    second_cancel()


def test_cancel_subscription_with_invalid_data(monkeypatch):
    cancelled_subs = Mock(
        return_value=({"message": "Subscription not available."}, 400)
    )
    subscription = {"subscriptions": [{"subscription_id": "sub_123"}]}
    monkeypatch.setattr("subhub.sub.payments.cancel_subscription", cancelled_subs)
    if subscription.get("subscriptions"):
        cancelled, code = payments.cancel_subscription(
            "process_test",
            subscription["subscriptions"][0]["subscription_id"] + "invalid",
        )
        assert cancelled["message"] == "Subscription not available."
        assert 400 == code
    g.subhub_account.remove_from_db("process_test")


def test_cancel_subscription_already_cancelled(monkeypatch):
    async def first_subscription():
        cancelled_subs = Mock(
            return_value=({"message": "Subscription cancellation successful"}, 201)
        )
        monkeypatch.setattr("subhub.sub.payments.cancel_subscription", cancelled_subs)
        cancelled, code = payments.cancel_subscription("process_test", "sub_1")

        monkeypatch.undo()
        assert cancelled["message"] == "Subscription cancellation successful"
        assert 201 == code

    async def second_subscription():
        await first_subscription()
        cancelled_subs2 = Mock(
            return_value=({"message": "Subscription not available."}, 400)
        )
        monkeypatch.setattr("subhub.sub.payments.cancel_subscription", cancelled_subs2)
        cancelled2, code2 = payments.cancel_subscription("process_test", "sub_")
        assert cancelled2["message"] == "Subscription cancellation successful"
        assert 201 == code2

    second_subscription()


def test_cancel_subscription_with_invalid_subhub_user(monkeypatch):
    """
    GIVEN an active subscription
    WHEN provided an api_token and an invalid userid
    THEN return customer not found error
    """
    cancelled, code = payments.cancel_subscription("invalid_user", "subscription_id")
    assert 404 == code
    assert cancelled["message"] == "Customer does not exist."



def test_cancel_subscription_with_invalid_stripe_customer(monkeypatch):
    """
    GIVEN an userid and subscription id
    WHEN the user has an invalid stripe customer id
    THEN a StripeError is raised
    """
    subscription, code = create_subscription_for_processing

    subhub_user = g.subhub_account.get_user("process_test")
    subhub_user.cust_id = None
    g.subhub_account.save_user(subhub_user)

    exception = None
    try:
        cancelled, code = payments.cancel_subscription(
            "process_test", subscription["subscriptions"][0]["subscription_id"]
        )
    except Exception as e:
        exception = e

    g.subhub_account.remove_from_db("process_test")

    assert isinstance(exception, InvalidRequestError)
    assert "Customer instance has invalid ID" in exception.user_message


def test_check_subscription_with_valid_parameters(monkeypatch):
    """
    GIVEN should get a list of active subscriptions
    WHEN provided an api_token and a userid id
    THEN validate should return list of active subscriptions
    """
    subscription, code = create_subscription_for_processing
    sub_status, code = payments.subscription_status("process_test")
    assert 200 == code
    assert len(sub_status) > 0
    g.subhub_account.remove_from_db("process_test")


def test_update_payment_method_valid_parameters(monkeypatch):
    """
    GIVEN api_token, userid, pmt_token
    WHEN all parameters are valid
    THEN update payment method for a customer
    """
    subscription, code = create_subscription_for_processing
    updated_pmt, code = payments.update_payment_method(
        "process_test", {"pmt_token": "tok_mastercard"}
    )
    assert 201 == code
    g.subhub_account.remove_from_db("process_test")


def test_update_payment_method_invalid_payment_token(monkeypatch):
    """
    GIVEN api_token, userid, pmt_token
    WHEN invalid pmt_token
    THEN a StripeError exception is raised
    """
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
    m.setattr("subhub.customer.fetch_customer", customer)
    exception = None
    try:
        updated_pmt, code = payments.update_payment_method(
            "process_test", {"pmt_token": "tok_invalid"}
        )
    except Exception as e:
        exception = e
    print(f"invalid payment token {updated_pmt} {code}")

    assert "Customer mismatch." in updated_pmt["message"]


def test_update_payment_method_missing_stripe_customer(monkeypatch):
    """
    GIVEN api_token, userid, pmt_token
    WHEN provided user with missing stripe customer id
    THEN return missing customer
    """
    subhub_account = MagicMock()

    get_user = MagicMock()
    user_id = PropertyMock(return_value="process_test")
    cust_id = PropertyMock(return_value=None)
    type(get_user).user_id = user_id
    type(get_user).cust_id = cust_id

    subhub_account.get_user = get_user

    updated_pmt, code = payments.update_payment_method(
        "process_test", {"pmt_token": "tok_invalid"}
    )
    assert 404 == code


def test_update_payment_method_invalid_stripe_customer(
    app, create_subscription_for_processing
):
    """
    GIVEN api_token, userid, pmt_token
    WHEN provided invalid stripe data
    THEN a StripeError is raised
    """

    subscription, code = create_subscription_for_processing
    subhub_user = g.subhub_account.get_user("process_test")
    subhub_user.cust_id = "bad_id"
    g.subhub_account.save_user(subhub_user)

    exception = None
    try:
        updated_pmt, code = payments.update_payment_method(
            "process_test", {"pmt_token": "tok_invalid"}
        )
    except Exception as e:
        exception = e

    g.subhub_account.remove_from_db("process_test")

    assert isinstance(exception, InvalidRequestError)
    assert "No such customer:" in exception.user_message


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
