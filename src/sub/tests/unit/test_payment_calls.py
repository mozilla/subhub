# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import uuid
import pytest
import stripe

from flask import g
from stripe.error import InvalidRequestError
from shared.exceptions import ClientError
from unittest.mock import Mock, MagicMock, PropertyMock

from src.sub import payments
from src.sub.customer import (
    create_customer,
    subscribe_customer,
    existing_or_new_customer,
)
from src.sub.tests.unit.utils import MockSubhubUser
from src.shared.log import get_logger
from src.shared.cfg import CFG


logger = get_logger()


def test_create_customer_invalid_origin_system():
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


def test_create_customer_tok_visa():
    """
    GIVEN create a stripe customer
    WHEN provided a test visa token and test fxa
    THEN validate the customer metadata is correct
    """
    customer = create_customer(
        g.subhub_account,
        user_id="test_mozilla",
        source_token="tok_visa",
        email="test_visa@tester.com",
        origin_system="Test_system",
        display_name="John Tester",
    )
    pytest.customer = customer
    assert customer["metadata"]["userid"] == "test_mozilla"


def test_create_customer_tok_mastercard():
    """
    GIVEN create a stripe customer
    WHEN provided a test mastercard token and test userid
    THEN validate the customer metadata is correct
    """
    customer = create_customer(
        g.subhub_account,
        user_id="test_mozilla",
        source_token="tok_mastercard",
        email="test_mastercard@tester.com",
        origin_system="Test_system",
        display_name="John Tester",
    )
    assert customer["metadata"]["userid"] == "test_mozilla"


def test_create_customer_tok_invalid():
    """
    GIVEN create a stripe customer
    WHEN provided an invalid test token and test userid
    THEN validate the customer metadata is correct
    """
    with pytest.raises(InvalidRequestError):
        customer = create_customer(
            g.subhub_account,
            user_id="test_mozilla",
            source_token="tok_invalid",
            email="test_invalid@tester.com",
            origin_system="Test_system",
            display_name="John Tester",
        )


def test_create_customer_tok_avsFail():
    """
    GIVEN create a stripe customer
    WHEN provided an invalid test token and test userid
    THEN validate the customer metadata is correct
    """
    customer = create_customer(
        g.subhub_account,
        user_id="test_mozilla",
        source_token="tok_avsFail",
        email="test_avsfail@tester.com",
        origin_system="Test_system",
        display_name="John Tester",
    )
    assert customer["metadata"]["userid"] == "test_mozilla"


def test_create_customer_tok_avsUnchecked():
    """
    GIVEN create a stripe customer
    WHEN provided an invalid test token and test userid
    THEN validate the customer metadata is correct
    """
    customer = create_customer(
        g.subhub_account,
        user_id="test_mozilla",
        source_token="tok_avsUnchecked",
        email="test_avsunchecked@tester.com",
        origin_system="Test_system",
        display_name="John Tester",
    )
    assert customer["metadata"]["userid"] == "test_mozilla"


def test_subscribe_customer(create_customer_for_processing):
    """
    GIVEN create a subscription
    WHEN provided a customer and plan
    THEN validate subscription is created
    """
    customer = create_customer_for_processing
    subscription = subscribe_customer(customer, "plan_EtMcOlFMNWW4nd")
    assert subscription["plan"]["active"]


def test_subscribe_customer_invalid_plan(create_customer_for_processing):
    """
    GIVEN create a subscription
    WHEN provided a customer and plan
    THEN validate subscription is created
    """
    customer = create_customer_for_processing
    try:
        subscribe_customer(customer, "plan_notvalid")
    except Exception as e:
        exception = e
    assert isinstance(exception, InvalidRequestError)
    assert "Unable to create plan" in exception.user_message


def test_create_subscription_with_valid_data():
    """
    GIVEN create a subscription
    WHEN provided a api_token, userid, pmt_token, plan_id, cust_id
    THEN validate subscription is created
    """
    uid = uuid.uuid4()
    subscription, code = payments.subscribe_to_plan(
        "validcustomer",
        {
            "pmt_token": "tok_visa",
            "plan_id": "plan_EtMcOlFMNWW4nd",
            "email": "valid@{}customer.com".format(uid),
            "origin_system": "Test_system",
            "display_name": "Jon Tester",
        },
    )
    assert 201 == code
    payments.cancel_subscription(
        "validcustomer", subscription["subscriptions"][0]["subscription_id"]
    )
    g.subhub_account.remove_from_db("validcustomer")


def test_subscribe_customer_existing(create_customer_for_processing):
    """
    GIVEN create a subscription
    WHEN provided a customer and plan
    THEN validate subscription is created
    """
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
    subscription2, code2 = payments.subscribe_to_plan(
        "validcustomer",
        {
            "pmt_token": "tok_visa",
            "plan_id": "plan_EtMcOlFMNWW4nd",
            "email": f"valid@{uid}customer.com",
            "origin_system": "Test_system",
            "display_name": "Jon Tester",
        },
    )
    assert 409 == code2
    payments.cancel_subscription(
        "validcustomer", subscription["subscriptions"][0]["subscription_id"]
    )
    g.subhub_account.remove_from_db("validcustomer")


def test_create_subscription_with_invalid_payment_token():
    """
    GIVEN a api_token, userid, invalid pmt_token, plan_id, email
    WHEN the pmt_token is invalid
    THEN a StripeError should be raised
    """
    exception = None
    try:
        subscription, code = payments.subscribe_to_plan(
            "invalid_test",
            {
                "pmt_token": "tok_invalid",
                "plan_id": "plan_EtMcOlFMNWW4nd",
                "email": "invalid_test@test.com",
                "origin_system": "Test_system",
                "display_name": "Jon Tester",
            },
        )
    except Exception as e:
        exception = e

    g.subhub_account.remove_from_db("invalid_test")

    assert isinstance(exception, InvalidRequestError)
    assert "Unable to create customer." in exception.user_message


def test_create_subscription_with_invalid_plan_id(app):
    """
    GIVEN a api_token, userid, pmt_token, plan_id, email
    WHEN the plan_id provided is invalid
    THEN a StripeError is raised
    """
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

    g.subhub_account.remove_from_db("invalid_plan")

    assert isinstance(exception, InvalidRequestError)
    assert "No such plan:" in exception.user_message


def test_list_all_plans_valid():
    """
    GIVEN should list all available plans
    WHEN provided an api_token,
    THEN validate able to list all available plans
    """
    plans, code = payments.list_all_plans()
    assert len(plans) > 0
    assert 200 == code


def test_cancel_subscription_with_valid_data(app, create_subscription_for_processing):
    """
    GIVEN should cancel an active subscription
    WHEN provided a api_token, and subscription id
    THEN validate should cancel subscription
    """
    subscription, code = create_subscription_for_processing
    cancelled, code = payments.cancel_subscription(
        "process_test", subscription["subscriptions"][0]["subscription_id"]
    )
    assert cancelled["message"] == "Subscription cancellation successful"
    assert 201 == code
    g.subhub_account.remove_from_db("process_test")


def test_delete_customer(app, create_subscription_for_processing):
    """
    GIVEN should cancel an active subscription,
    delete customer from payment provider and database
    WHEN provided a user id
    THEN validate user is deleted from payment provider and database
    """
    message, code = payments.delete_customer("process_test")
    assert message["message"] == "Customer deleted successfully"
    deleted_message, code = payments.subscription_status("process_test")
    assert "Customer does not exist" in deleted_message["message"]


def test_delete_customer_bad_user(app, create_subscription_for_processing):
    """
    GIVEN should cancel an active subscription,
    delete customer from payment provider and database
    WHEN provided a user id
    THEN validate user is deleted from payment provider and database
    """
    message, code = payments.delete_customer("process_test2")
    assert message["message"] == "Customer does not exist."
    assert code == 404


def test_delete_user_from_db(app, create_subscription_for_processing):
    """
    GIVEN should delete user from user table
    WHEN provided with a valid user id
    THEN add to deleted users table
    """
    deleted_user = payments.delete_user_from_db("process_test")
    logger.info("deleted user from db", deleted_user=deleted_user)
    assert deleted_user is True


def test_delete_user_from_db2(app, create_subscription_for_processing):
    """
    GIVEN raise ClientError
    WHEN provided with an invalid user id
    THEN validate error message
    """
    uid = "process_test2"
    with pytest.raises(ClientError) as request_error:
        payments.delete_user_from_db("process_test2")
    msg = f"userid is None for customer {uid}"
    assert msg in str(request_error.value)


def test_add_user_to_deleted_users_record(app, create_customer_for_processing):
    """
    GIVEN Add user to deleted users record
    WHEN provided a user id, cust id and origin system
    THEN return subhud_deleted user
    """
    to_delete = g.subhub_account.get_user("process_customer")
    deleted_user = payments.add_user_to_deleted_users_record(
        user_id=to_delete.user_id,
        cust_id=to_delete.cust_id,
        origin_system=to_delete.origin_system,
    )
    assert deleted_user.user_id == "process_customer"
    assert deleted_user.origin_system == "Test_system"
    assert "cus_" in deleted_user.cust_id


def test_cancel_subscription_with_valid_data_multiple_subscriptions_remove_first():
    """
    GIVEN a user with multiple subscriptions
    WHEN the first subscription is cancelled
    THEN the specified subscription is cancelled
    """
    uid = uuid.uuid4()
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

    # cancel the first subscription created
    cancelled, code = payments.cancel_subscription(
        "valid_customer", subscription1["subscriptions"][0]["subscription_id"]
    )
    assert cancelled["message"] == "Subscription cancellation successful"
    assert 201 == code

    # clean up test data created
    cancelled, code = payments.cancel_subscription(
        "valid_customer", subscription2["subscriptions"][0]["subscription_id"]
    )
    g.subhub_account.remove_from_db("valid_customer")
    assert cancelled["message"] == "Subscription cancellation successful"
    assert 201 == code


def test_cancel_subscription_with_valid_data_multiple_subscriptions_remove_second():
    """
    GIVEN a user with multiple subscriptions
    WHEN the second subscription is cancelled
    THEN the specified subscription is cancelled
    """
    uid = uuid.uuid4()
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

    # cancel the second subscription created
    cancelled, code = payments.cancel_subscription(
        "valid_customer", subscription2["subscriptions"][0]["subscription_id"]
    )
    assert cancelled["message"] == "Subscription cancellation successful"
    assert 201 == code

    # clean up test data created
    cancelled, code = payments.cancel_subscription(
        "valid_customer", subscription1["subscriptions"][0]["subscription_id"]
    )
    g.subhub_account.remove_from_db("valid_customer")
    assert cancelled["message"] == "Subscription cancellation successful"
    assert 201 == code


def test_cancel_subscription_with_invalid_data(app, create_subscription_for_processing):
    subscription, code = create_subscription_for_processing
    if subscription.get("subscriptions"):
        cancelled, code = payments.cancel_subscription(
            "process_test",
            subscription["subscriptions"][0]["subscription_id"] + "invalid",
        )
        assert cancelled["message"] == "Subscription not available."
        assert 400 == code
    g.subhub_account.remove_from_db("process_test")


def test_cancel_subscription_already_cancelled(app, create_subscription_for_processing):
    subscription, code = create_subscription_for_processing
    cancelled, code = payments.cancel_subscription(
        "process_test", subscription["subscriptions"][0]["subscription_id"]
    )
    cancelled2, code2 = payments.cancel_subscription(
        "process_test", subscription["subscriptions"][0]["subscription_id"]
    )
    assert cancelled["message"] == "Subscription cancellation successful"
    assert 201 == code
    assert cancelled2["message"] == "Subscription cancellation successful"
    assert 201 == code2
    g.subhub_account.remove_from_db("process_test")


def test_cancel_subscription_with_invalid_subhub_user(app):
    """
    GIVEN an active subscription
    WHEN provided an api_token and an invalid userid
    THEN return customer not found error
    """
    cancelled, code = payments.cancel_subscription("invalid_user", "subscription_id")
    assert 404 == code
    assert cancelled["message"] == "Customer does not exist."


def test_cancel_subscription_with_invalid_stripe_customer(
    app, create_subscription_for_processing
):
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


def test_check_subscription_with_valid_parameters(
    app, create_subscription_for_processing
):
    """
    GIVEN should get a list of active subscriptions
    WHEN provided an api_token and a userid id
    THEN validate should return list of active subscriptions
    """
    subscription, code = create_subscription_for_processing
    sub_status, code = payments.subscription_status("process_test")
    assert 201 == code
    assert len(sub_status) > 0
    g.subhub_account.remove_from_db("process_test")


def test_update_payment_method_valid_parameters(
    app, create_subscription_for_processing
):
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


def test_update_payment_method_invalid_payment_token(
    app, create_subscription_for_processing
):
    """
    GIVEN api_token, userid, pmt_token
    WHEN invalid pmt_token
    THEN a StripeError exception is raised
    """
    exception = None
    try:
        updated_pmt, code = payments.update_payment_method(
            "process_test", {"pmt_token": "tok_invalid"}
        )
    except Exception as e:
        exception = e

    g.subhub_account.remove_from_db("process_test")

    assert isinstance(exception, InvalidRequestError)
    assert "No such token:" in exception.user_message


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
