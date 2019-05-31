#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json

import connexion
from flask import g

from subhub.app import create_app


def test_subhub():
    """
    something
    """
    app = create_app()
    assert isinstance(app, connexion.FlaskApp)


def test_update_customer_payment_stripe_error_handler(
    app, create_subscription_for_processing
):
    """
    GIVEN the route POST v1/customer/{id} is called
    WHEN the payment token provided is invalid
    THEN the StripeError should be handled by the app errorhandler
    """
    client = app.app.test_client()
    (subscription, code) = create_subscription_for_processing

    path = "v1/customer/process_test"
    data = {"pmt_token": "tok_invalid"}

    response = client.post(
        path,
        headers={"Authorization": "fake_payment_api_key"},
        data=json.dumps(data),
        content_type="application/json",
    )

    data = json.loads(response.data)
    g.subhub_account.remove_from_db("process_test")
    assert 500 == response.status_code
    assert "No such token: tok_invalid" == data["message"]


def test_customer_signup_stripe_error_handler(app, create_subscription_for_processing):
    """
    GIVEN the route POST v1/customer/{id}/subcriptions is called
    WHEN the plan id provided is invalid
    THEN the StripeError should be handled by the app errorhandler
    """
    client = app.app.test_client()
    (subscription, code) = create_subscription_for_processing

    path = "v1/customer/process_test/subscriptions"
    data = {
        "pmt_token": "tok_visa",
        "plan_id": "invalid",
        "orig_system": "Test_system",
        "email": "subtest@example.com",
    }

    response = client.post(
        path,
        headers={"Authorization": "fake_payment_api_key"},
        data=json.dumps(data),
        content_type="application/json",
    )

    data = json.loads(response.data)
    g.subhub_account.remove_from_db("process_test")
    assert 500 == response.status_code
    assert "No such plan: invalid" == data["message"]


def test_customer_unsubscribe_stripe_error_handler(
    app, create_subscription_for_processing
):
    """
    GIVEN the route DELETE v1/customer/{id}/subcriptions/{sub_id} is called
    WHEN the stripe customer id on the user object is invalid
    THEN the StripeError should be handled by the app errorhandler
    """
    client = app.app.test_client()
    (subscription, code) = create_subscription_for_processing

    subhub_user = g.subhub_account.get_user("process_test")
    subhub_user.custId = None
    g.subhub_account.save_user(subhub_user)

    subscription_id = subscription["subscriptions"][0]["subscription_id"]
    path = f"v1/customer/process_test/subscriptions/{subscription_id}"

    response = client.delete(path, headers={"Authorization": "fake_payment_api_key"})

    data = json.loads(response.data)
    g.subhub_account.remove_from_db("process_test")

    assert 500 == response.status_code
    assert "Customer instance has invalid ID" in data["message"]
