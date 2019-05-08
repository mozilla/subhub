import uuid

import pytest
import stripe
import stripe.error
from flask import g

from subhub.api import payments
from subhub.customer import create_customer, subscribe_customer


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
    )
    assert customer["metadata"]["userid"] == "test_mozilla"


def test_create_customer_tok_invalid():
    """
    GIVEN create a stripe customer
    WHEN provided an invalid test token and test userid
    THEN validate the customer metadata is correct
    """
    with pytest.raises(stripe.error.InvalidRequestError):
        customer = create_customer(
            g.subhub_account,
            user_id="test_mozilla",
            source_token="tok_invalid",
            email="test_invalid@tester.com",
            origin_system="Test_system",
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
    with pytest.raises(stripe.error.InvalidRequestError) as excinfo:
        subscribe_customer(customer, "plan_notvalid")
    assert "No such plan: plan_notvalid" in str(excinfo)


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
            "orig_system": "Test_system",
        },
    )
    assert 201 == code
    payments.cancel_subscription(
        "validcustomer", subscription["subscriptions"][0]["subscription_id"]
    )
    g.subhub_account.remove_from_db("validcustomer")


def test_create_subscription_with_invalid_payment_token():
    """
    GIVEN should not create a subscription
    WHEN provided a api_token, userid, invalid pmt_token, plan_id, email
    THEN validate subscription is created
    """
    with pytest.raises(stripe.error.InvalidRequestError) as excinfo:
        payments.subscribe_to_plan(
            "invalid_test",
            {
                "pmt_token": "tok_invalid",
                "plan_id": "plan_EtMcOlFMNWW4nd",
                "email": "invalid_test@test.com",
                "orig_system": "Test_system",
            },
        )

    g.subhub_account.remove_from_db("invalid_test")
    assert "No such token: tok_invalid" in str(excinfo)


def test_create_subscription_with_invalid_plan_id(app):
    """
    GIVEN should not create a subscription
    WHEN provided a api_token, userid, pmt_token, invalid plan_id, email
    THEN validate subscription is created
    """
    with pytest.raises(stripe.error.InvalidRequestError) as excinfo:
        payments.subscribe_to_plan(
            "invalid_plan",
            {
                "pmt_token": "tok_visa",
                "plan_id": "plan_abc123",
                "email": "invalid_plan@tester.com",
                "orig_system": "Test_system",
            },
        )
    g.subhub_account.remove_from_db("invalid_plan")
    assert "No such plan: plan_abc123" in str(excinfo)


def test_list_all_plans_valid():
    """
    GIVEN should list all available plans
    WHEN provided an api_token,
    THEN validate able to list all available plans
    """
    (plans, code) = payments.list_all_plans()
    assert len(plans) > 0
    assert 200 == code


def test_cancel_subscription_with_valid_data(app, create_subscription_for_processing):
    """
    GIVEN should cancel an active subscription
    WHEN provided a api_token, and subscription id
    THEN validate should cancel subscription
    """
    (subscription, code) = create_subscription_for_processing
    (cancelled, code) = payments.cancel_subscription(
        "process_test", subscription["subscriptions"][0]["subscription_id"]
    )
    assert cancelled["message"] == "Subscription cancellation successful"
    assert 201 == code
    g.subhub_account.remove_from_db("process_test")


def test_check_subscription_with_valid_parameters(
    app, create_subscription_for_processing
):
    """
    GIVEN should get a list of active subscriptions
    WHEN provided an api_token and a userid id
    THEN validate should return list of active subscriptions
    """
    (subscription, code) = create_subscription_for_processing
    (sub_status, code) = payments.subscription_status("process_test")
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
    (subscription, code) = create_subscription_for_processing
    (updated_pmt, code) = payments.update_payment_method(
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
    THEN do not update payment method for a customer
    """
    (updated_pmt, code) = payments.update_payment_method(
        "process_test", {"pmt_token": "tok_invalid"}
    )
    assert 400 == code
    assert "No such token:" in updated_pmt["message"]
    g.subhub_account.remove_from_db("process_test")
