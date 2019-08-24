# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
from unittest.mock import Mock, MagicMock
import mock

import connexion
import stripe.error

from sub.app import create_app
from sub.tests.unit.utils import MockSubhubUser

from sub.shared.log import get_logger

logger = get_logger()


class MockCustomer:
    id = 123
    object = "customer"
    subscriptions = [{"data": "somedata"}]

    def properties(self, cls):
        return [i for i in cls.__dict__.keys() if i[:1] != "_"]

    def get(self, key, default=None):
        properties = self.properties(MockCustomer)
        if key in properties:
            return key
        else:
            return default


def test_subhub():
    """
    something
    """
    app = create_app()
    assert isinstance(app, connexion.FlaskApp)


def test_list_plans(app, monkeypatch):
    """
    GIVEN a valid token
    WHEN a request for plans is made
    THEN a success status of 200 is returned
    """
    client = app.app.test_client()

    plans_data = [
        {
            "id": "plan_1",
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

    monkeypatch.setattr("stripe.Plan.list", plans)
    monkeypatch.setattr("stripe.Product.retrieve", product)

    path = "v1/sub/plans"

    response = client.get(
        path,
        headers={"Authorization": "fake_payment_api_key"},
        content_type="application/json",
    )

    assert response.status_code == 200


def test_update_customer_payment_server_stripe_error_with_params(app, monkeypatch):
    """
    GIVEN the route POST v1/sub/customer/{id} is called
    WHEN the payment token provided is invalid
    THEN the StripeError should be handled by the app errorhandler
    """
    client = app.app.test_client()

    user = Mock(return_value=MockSubhubUser())

    retrieve = Mock(
        side_effect=stripe.error.InvalidRequestError(
            message="Customer instance has invalid ID",
            param="customer_id",
            code="invalid",
        )
    )
    monkeypatch.setattr("flask.g.subhub_account.get_user", user)
    monkeypatch.setattr("stripe.Customer.retrieve", retrieve)

    path = "v1/sub/customer/123"
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


def test_customer_signup_server_stripe_error_with_params(app, monkeypatch):
    """
    GIVEN the route POST v1/sub/customer/{id}/subcriptions is called
    WHEN the plan id provided is invalid
    THEN the StripeError should be handled by the app errorhandler
    """
    client = app.app.test_client()

    customer = Mock(return_value=MockCustomer())
    none = Mock(return_value=None)

    create = Mock(
        side_effect=stripe.error.InvalidRequestError(
            message="No such plan: invalid", param="plan_id", code="invalid_plan"
        )
    )
    monkeypatch.setattr("sub.payments.has_existing_plan", none)
    monkeypatch.setattr("sub.payments.existing_or_new_customer", customer)
    monkeypatch.setattr("stripe.Subscription.create", create)

    path = "v1/sub/customer/process_test/subscriptions"
    data = {
        "pmt_token": "tok_visa",
        "plan_id": "invalid",
        "origin_system": "Test_system",
        "email": "subtest@example.com",
        "display_name": "John Tester",
    }

    response = client.post(
        path,
        headers={"Authorization": "fake_payment_api_key"},
        data=json.dumps(data),
        content_type="application/json",
    )

    loaded_data = json.loads(response.data)

    assert response.status_code == 500
    assert "No such plan" in loaded_data["message"]


def test_subscribe_success(app, monkeypatch):
    """
    GIVEN a route that attempts to make a subscribe a customer
    WHEN valid data is provided
    THEN a success status of 201 will be returned
    """

    client = app.app.test_client()

    subscription_data = {
        "id": "sub_123",
        "status": "active",
        "current_period_end": 1566833524,
        "current_period_start": 1564155124,
        "ended_at": None,
        "plan": {"id": "plan_123", "nickname": "Monthly VPN Subscription"},
        "cancel_at_period_end": False,
    }

    mock_false = Mock(return_value=False)

    customer = Mock(return_value=MockCustomer())

    customer_updated = MagicMock(
        return_value={"id": "cust_123", "subscriptions": {"data": [subscription_data]}}
    )

    create = Mock(return_value={"id": "sub_234"})

    user = Mock(return_value=MockSubhubUser())

    monkeypatch.setattr("flask.g.subhub_account.get_user", user)
    monkeypatch.setattr("stripe.Customer.retrieve", customer_updated)
    monkeypatch.setattr("sub.payments.has_existing_plan", mock_false)
    monkeypatch.setattr("sub.payments.existing_or_new_customer", customer)
    monkeypatch.setattr("stripe.Subscription.create", create)

    path = "v1/sub/customer/subtest/subscriptions"
    data = {
        "pmt_token": "tok_visa",
        "plan_id": "plan",
        "origin_system": "fake_origin1",
        "email": "subtest@example.com",
        "display_name": "John Tester",
    }

    response = client.post(
        path,
        headers={"Authorization": "fake_payment_api_key"},
        data=json.dumps(data),
        content_type="application/json",
    )
    logger.info("response data", data=response.data)
    assert response.status_code == 201


def test_subscribe_customer_existing(app, monkeypatch):
    """
    GIVEN a route that attempts to make a subscribe a customer
    WHEN the customer already exists
    THEN an error status of 409 will be returned
    """

    client = app.app.test_client()

    mock_true = Mock(return_value=True)

    monkeypatch.setattr("sub.payments.has_existing_plan", mock_true)

    path = "v1/sub/customer/subtest/subscriptions"
    data = {
        "pmt_token": "tok_visa",
        "plan_id": "plan",
        "origin_system": "Test_system",
        "email": "subtest@example.com",
        "display_name": "John Tester",
    }

    response = client.post(
        path,
        headers={"Authorization": "fake_payment_api_key"},
        data=json.dumps(data),
        content_type="application/json",
    )

    assert response.status_code == 409


def test_subscribe_card_declined_error_handler(app, monkeypatch):
    """
    GIVEN a route that attempts to make a stripe payment
    WHEN the card is declined
    THEN the error thrown by stripe will be handled and return a 402
    """

    client = app.app.test_client()

    customer = Mock(return_value=MockCustomer())
    none = Mock(return_value=None)

    create = Mock(
        side_effect=stripe.error.CardError(
            message="card declined", param="", code="generic_decline"
        )
    )
    monkeypatch.setattr("sub.payments.has_existing_plan", none)
    monkeypatch.setattr("sub.payments.existing_or_new_customer", customer)
    monkeypatch.setattr("stripe.Subscription.create", create)

    path = "v1/sub/customer/subtest/subscriptions"
    data = {
        "pmt_token": "tok_visa",
        "plan_id": "plan",
        "origin_system": "Test_system",
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


def test_customer_unsubscribe_server_stripe_error_with_params(app, monkeypatch):
    """
    GIVEN the route DELETE v1/sub/customer/{id}/subcriptions/{sub_id} is called
    WHEN the stripe customer id on the user object is invalid
    THEN the StripeError should be handled by the app errorhandler
    """
    client = app.app.test_client()

    subhub_user = Mock(return_value=MockSubhubUser())

    retrieve = Mock(
        side_effect=stripe.error.InvalidRequestError(
            message="Customer instance has invalid ID",
            param="customer_id",
            code="invalid",
        )
    )
    monkeypatch.setattr("flask.g.subhub_account.get_user", subhub_user)
    monkeypatch.setattr("stripe.Customer.retrieve", retrieve)

    path = f"v1/sub/customer/testuser/subscriptions/sub_123"

    response = client.delete(path, headers={"Authorization": "fake_payment_api_key"})

    data = json.loads(response.data)

    assert response.status_code == 500
    assert "Customer instance has invalid ID" in data["message"]


@mock.patch("sub.payments._get_all_plans")
def test_plan_response_valid(mock_plans, app):
    fh = open("tests/unit/fixtures/valid_plan_response.json")
    valid_response = json.loads(fh.read())
    fh.close()

    mock_plans.return_value = valid_response

    client = app.app.test_client()

    path = "v1/sub/plans"

    response = client.get(
        path,
        headers={"Authorization": "fake_payment_api_key"},
        content_type="application/json",
    )

    assert response.status_code == 200


@mock.patch("sub.payments._get_all_plans")
def test_plan_response_invalid(mock_plans, app):
    fh = open("tests/unit/fixtures/invalid_plan_response.json")
    invalid_response = json.loads(fh.read())
    fh.close()

    mock_plans.return_value = invalid_response

    client = app.app.test_client()

    path = "v1/sub/plans"

    response = client.get(
        path,
        headers={"Authorization": "fake_payment_api_key"},
        content_type="application/json",
    )

    assert response.status_code == 500
