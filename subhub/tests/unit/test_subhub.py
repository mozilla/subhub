#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from unittest.mock import Mock, patch

import connexion
from flask import g
import stripe.error

from subhub.app import create_app
from subhub.tests.unit.stripe.utils import MockSubhubUser


class MockCustomer:
    id = 123
    object = "customer"
    subscriptions = [{"data": "somedata"}]


def test_subhub():
    """
    something
    """
    app = create_app()
    assert isinstance(app, connexion.FlaskApp)


@patch("stripe.Customer")
def test_update_customer_payment_server_stripe_error_with_params(
    customer_mock, app, monkeypatch
):
    """
    GIVEN the route POST v1/customer/{id} is called
    WHEN the payment token provided is invalid
    THEN the StripeError should be handled by the app errorhandler
    """
    client = app.app.test_client()

    subhub_user = Mock(return_value=MockSubhubUser())

    customer_mock.retrieve.side_effect = stripe.error.InvalidRequestError(
        message="Customer instance has invalid ID", param="customer_id", code="invalid"
    )
    monkeypatch.setattr("flask.g.subhub_account.get_user", subhub_user)

    path = "v1/customer/123"
    data = {"pmt_token": "token"}

    response = client.post(
        path,
        headers={"Authorization": "fake_payment_api_key"},
        data=json.dumps(data),
        content_type="application/json",
    )

    data = json.loads(response.data)

    assert response.status_code == 500
    assert data["message"] == "Customer instance has invalid ID"


@patch("stripe.Subscription")
def test_customer_signup_server_stripe_error_with_params(
    subscription_mock, app, monkeypatch
):
    """
    GIVEN the route POST v1/customer/{id}/subcriptions is called
    WHEN the plan id provided is invalid
    THEN the StripeError should be handled by the app errorhandler
    """
    client = app.app.test_client()

    customer = Mock(return_value=MockCustomer())
    none = Mock(return_value=None)

    subscription_mock.create.side_effect = stripe.error.InvalidRequestError(
        message="No such plan: invalid", param="plan_id", code="invalid_plan"
    )
    monkeypatch.setattr("subhub.api.payments.has_existing_plan", none)
    monkeypatch.setattr("subhub.api.payments.existing_or_new_customer", customer)

    path = "v1/customer/process_test/subscriptions"
    data = {
        "pmt_token": "tok_visa",
        "plan_id": "invalid",
        "orig_system": "Test_system",
        "email": "subtest@example.com",
        "display_name": "John Tester",
    }

    response = client.post(
        path,
        headers={"Authorization": "fake_payment_api_key"},
        data=json.dumps(data),
        content_type="application/json",
    )

    data = json.loads(response.data)

    assert response.status_code == 500
    assert data["message"] == "No such plan: invalid"
    assert data["params"] == "plan_id"
    assert data["code"] == "invalid_plan"


@patch("stripe.Subscription")
def test_subscribe_card_declined_error_handler(subscription_mock, app, monkeypatch):
    """
    GIVEN a route that attempts to make a stripe payment
    WHEN the card is declined
    THEN the error thrown by stripe will be handled and return a 402
    """

    client = app.app.test_client()

    customer = Mock(return_value=MockCustomer())
    none = Mock(return_value=None)

    subscription_mock.create.side_effect = stripe.error.CardError(
        message="card declined", param="", code="generic_decline"
    )
    monkeypatch.setattr("subhub.api.payments.has_existing_plan", none)
    monkeypatch.setattr("subhub.api.payments.existing_or_new_customer", customer)

    path = "v1/customer/subtest/subscriptions"
    data = {
        "pmt_token": "tok_visa",
        "plan_id": "plan",
        "orig_system": "Test_system",
        "email": "subtest@example.com",
        "display_name": "John Tester",
    }

    response = client.post(
        path,
        headers={"Authorization": "fake_payment_api_key"},
        data=json.dumps(data),
        content_type="application/json",
    )

    assert response.status_code == 402


@patch("stripe.Customer")
def test_customer_unsubscribe_server_stripe_error_with_params(
    customer_mock, app, monkeypatch
):
    """
    GIVEN the route DELETE v1/customer/{id}/subcriptions/{sub_id} is called
    WHEN the stripe customer id on the user object is invalid
    THEN the StripeError should be handled by the app errorhandler
    """
    client = app.app.test_client()

    subhub_user = Mock(return_value=MockSubhubUser())

    customer_mock.retrieve.side_effect = stripe.error.InvalidRequestError(
        message="Customer instance has invalid ID", param="customer_id", code="invalid"
    )
    monkeypatch.setattr("flask.g.subhub_account.get_user", subhub_user)

    path = f"v1/customer/testuser/subscriptions/sub_123"

    response = client.delete(path, headers={"Authorization": "fake_payment_api_key"})

    data = json.loads(response.data)

    assert response.status_code == 500
    assert "Customer instance has invalid ID" in data["message"]
