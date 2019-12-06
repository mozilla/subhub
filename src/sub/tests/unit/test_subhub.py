# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import os
import json
import unittest
from unittest.mock import Mock
import mock
import connexion

from flask import g
from stripe.util import convert_to_stripe_object
import stripe.error

from sub.app import create_app
from sub.shared.tests.unit.utils import MockSubhubUser
from sub.shared.db import SubHubAccountModel
from sub.tests.mock_customer import MockCustomer
from shared.log import get_logger

logger = get_logger()
DIRECTORY = os.path.dirname(__file__)


class MockDeletedCustomer:
    id = 123
    object = "customer"
    subscriptions = [{"data": "somedata"}]
    deleted = True

    def properties(self, cls):
        return [i for i in cls.__dict__.keys() if i[:1] != "_"]

    def get(self, key, default=None):
        properties = self.properties(MockDeletedCustomer)
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


@mock.patch("stripe.Product.retrieve")
@mock.patch("stripe.Plan.list")
def test_list_plans(mock_plans, mock_product, app):
    """
    GIVEN a valid token
    WHEN a request for plans is made
    THEN a success status of 200 is returned
    """
    with open(os.path.join(DIRECTORY, "fixtures/stripe_plan_test1.json")) as fh:
        plan_test1 = json.loads(fh.read())

    with open(os.path.join(DIRECTORY, "fixtures/stripe_plan_test2.json")) as fh:
        plan_test2 = json.loads(fh.read())

    with open(os.path.join(DIRECTORY, "fixtures/stripe_prod_test1.json")) as fh:
        prod_test1 = json.loads(fh.read())

    mock_plans.return_value = [plan_test1, plan_test2]
    mock_product.return_value = prod_test1

    client = app.app.test_client()

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


@mock.patch("stripe.Product.retrieve")
@mock.patch("sub.payments.find_newest_subscription")
@mock.patch("sub.payments.fetch_customer")
@mock.patch("stripe.Subscription.create")
@mock.patch("sub.payments.has_existing_plan")
@mock.patch("sub.payments.existing_or_new_customer")
def test_subscribe_success(
    mock_new_customer,
    mock_has_plan,
    mock_subscription,
    mock_fetch_customer,
    mock_new_sub,
    mock_product,
    app,
):
    """
    GIVEN a route that attempts to make a subscribe a customer
    WHEN valid data is provided
    THEN a success status of 201 will be returned
    """

    client = app.app.test_client()
    fh = open(os.path.join(DIRECTORY, "fixtures/stripe_cust_test1.json"))
    cust_test1 = json.loads(fh.read())
    fh.close()

    mock_new_customer.return_value = convert_to_stripe_object(cust_test1)
    mock_has_plan.return_value = False
    mock_fetch_customer.return_value = convert_to_stripe_object(cust_test1)

    with open(os.path.join(DIRECTORY, "fixtures/stripe_sub_test1.json")) as fh:
        sub_test1 = json.loads(fh.read())

    with open(os.path.join(DIRECTORY, "fixtures/stripe_plan_test1.json")) as fh:
        plan_test1 = json.loads(fh.read())

    sub_test1["plan"] = plan_test1
    mock_subscription.return_value = sub_test1
    mock_new_sub.return_value = {"data": [sub_test1]}

    with open(os.path.join(DIRECTORY, "fixtures/stripe_prod_test1.json")) as fh:
        prod_test1 = json.loads(fh.read())

    mock_product.return_value = prod_test1

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


@mock.patch("sub.payments.has_existing_plan")
@mock.patch("sub.payments.existing_or_new_customer")
def test_subscribe_customer_existing(mock_new_customer, mock_has_plan, app):
    """
    GIVEN a route that attempts to make a subscribe a customer
    WHEN the customer already exists
    THEN an error status of 409 will be returned
    """

    client = app.app.test_client()
    with open(os.path.join(DIRECTORY, "fixtures/stripe_cust_test1.json")) as fh:
        cust_test1 = json.loads(fh.read())

    mock_new_customer.return_value = convert_to_stripe_object(cust_test1)
    mock_has_plan.return_value = True

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
    with open(os.path.join(DIRECTORY, "fixtures/valid_plan_response.json")) as fh:
        valid_response = json.loads(fh.read())

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
    with open(os.path.join(DIRECTORY, "fixtures/invalid_plan_response.json")) as fh:
        invalid_response = json.loads(fh.read())

    mock_plans.return_value = invalid_response

    client = app.app.test_client()

    path = "v1/sub/plans"

    response = client.get(
        path,
        headers={"Authorization": "fake_payment_api_key"},
        content_type="application/json",
    )

    assert response.status_code == 500


class PatchCustomerSubscriptionTest(unittest.TestCase):
    """
    Tests the upgrade/downgrade subscription endpoint
    """

    def setUp(self) -> None:
        sub_app = create_app()
        with sub_app.app.app_context():
            g.subhub_account = sub_app.app.subhub_account
            g.subhub_deleted_users = sub_app.app.subhub_deleted_users

        self.client = sub_app.app.test_client()

        with open(os.path.join(DIRECTORY, "fixtures/stripe_cust_test1.json")) as fh:
            cust_test1 = json.loads(fh.read())
        self.customer = convert_to_stripe_object(cust_test1)

        with open(os.path.join(DIRECTORY, "fixtures/stripe_deleted_cust.json")) as fh:
            deleted_cust = json.loads(fh.read())
        self.deleted_customer = convert_to_stripe_object(deleted_cust)

        with open(os.path.join(DIRECTORY, "fixtures/stripe_plan_test2.json")) as fh:
            plan_test2 = json.loads(fh.read())
        self.plan2 = convert_to_stripe_object(plan_test2)

        with open(os.path.join(DIRECTORY, "fixtures/stripe_plan_test4.json")) as fh:
            plan_test4 = json.loads(fh.read())
        self.plan4 = convert_to_stripe_object(plan_test4)

        with open(os.path.join(DIRECTORY, "fixtures/stripe_plan_test5.json")) as fh:
            plan_test5 = json.loads(fh.read())
        self.plan5 = convert_to_stripe_object(plan_test5)

        with open(os.path.join(DIRECTORY, "fixtures/stripe_prod_test1.json")) as fh:
            prod1 = json.loads(fh.read())
        self.prod1_fpn = convert_to_stripe_object(prod1)

        with open(os.path.join(DIRECTORY, "fixtures/stripe_prod_test2.json")) as fh:
            prod2 = json.loads(fh.read())
        self.prod2_none = convert_to_stripe_object(prod2)

        with open(os.path.join(DIRECTORY, "fixtures/stripe_prod_test3.json")) as fh:
            prod3 = json.loads(fh.read())
        self.prod3_none = convert_to_stripe_object(prod3)

        with open(os.path.join(DIRECTORY, "fixtures/stripe_prod_test4.json")) as fh:
            prod4 = json.loads(fh.read())
        self.prod4_fpn = convert_to_stripe_object(prod4)

        with open(os.path.join(DIRECTORY, "fixtures/stripe_prod_test5.json")) as fh:
            prod5 = json.loads(fh.read())
        self.prod5_identity = convert_to_stripe_object(prod5)

        with open(os.path.join(DIRECTORY, "fixtures/stripe_sub_test1.json")) as fh:
            sub1 = json.loads(fh.read())
        sub1["plan"] = plan_test4
        self.subscription = convert_to_stripe_object(sub1)

        self.subhub_user = SubHubAccountModel(
            user_id="user_1",
            cust_id="cust_1",
            origin_system="fxa",
            customer_status="active",
        )

        retrieve_customer_patcher = mock.patch("stripe.Customer.retrieve")
        retrieve_plan_patcher = mock.patch("stripe.Plan.retrieve")
        retrieve_product_patcher = mock.patch("stripe.Product.retrieve")
        modify_subscription_patcher = mock.patch("stripe.Subscription.modify")
        get_subhub_user_patcher = mock.patch("shared.db.SubHubAccount.get_user")

        self.addCleanup(retrieve_customer_patcher.stop)
        self.addCleanup(retrieve_plan_patcher.stop)
        self.addCleanup(retrieve_product_patcher.stop)
        self.addCleanup(modify_subscription_patcher.stop)
        self.addCleanup(get_subhub_user_patcher.stop)

        self.retrieve_customer_mock = retrieve_customer_patcher.start()
        self.retrieve_plan_mock = retrieve_plan_patcher.start()
        self.retrieve_product_mock = retrieve_product_patcher.start()
        self.modify_subscription_mock = modify_subscription_patcher.start()
        self.get_subhub_user_mock = get_subhub_user_patcher.start()

    def test_success(self):
        self.get_subhub_user_mock.return_value = self.subhub_user
        self.retrieve_customer_mock.return_value = self.customer
        self.retrieve_plan_mock.return_value = self.plan4
        self.retrieve_product_mock.side_effect = [self.prod1_fpn, self.prod4_fpn]
        self.modify_subscription_mock.return_value = self.subscription

        expected_response_body = {
            "cancel_at_period_end": False,
            "current_period_end": 1570226953,
            "current_period_start": 1567634953,
            "ended_at": None,
            "plan_id": "plan_test4",
            "plan_metadata": {},
            "plan_name": "Project Guardian (Monthly)",
            "product_metadata": {"productSet": "FPN"},
            "status": "active",
            "subscription_id": "sub_test1",
        }

        data = {"plan_id": "plan_test4"}

        response = self.client.patch(
            "v1/sub/customer/user123/subscriptions/sub_test1",
            headers={"Authorization": "fake_payment_api_key"},
            data=json.dumps(data),
            content_type="application/json",
        )

        response_body = json.loads(response.data)
        assert response.status_code == 200
        assert response_body == expected_response_body

    def test_user_not_found(self):
        self.get_subhub_user_mock.return_value = None

        expected_response_body = {"errno": 4000, "message": "Customer not found"}
        data = {"plan_id": "plan_123"}

        response = self.client.patch(
            "v1/sub/customer/user123/subscriptions/sub_test1",
            headers={"Authorization": "fake_payment_api_key"},
            data=json.dumps(data),
            content_type="application/json",
        )

        response_body = json.loads(response.data)
        assert response.status_code == 404
        assert response_body == expected_response_body

    def test_customer_not_found_deleted(self):
        self.get_subhub_user_mock.return_value = self.subhub_user
        self.retrieve_customer_mock.return_value = self.deleted_customer

        expected_response_body = {"errno": 4000, "message": "Customer not found"}
        data = {"plan_id": "plan_123"}

        response = self.client.patch(
            "v1/sub/customer/user123/subscriptions/sub_test1",
            headers={"Authorization": "fake_payment_api_key"},
            data=json.dumps(data),
            content_type="application/json",
        )

        response_body = json.loads(response.data)
        assert response.status_code == 404
        assert response_body == expected_response_body

    def test_customer_not_found(self):
        self.get_subhub_user_mock.return_value = self.subhub_user
        self.retrieve_customer_mock.side_effect = stripe.error.InvalidRequestError(
            "message here", param="parameter", http_status=404
        )

        expected_response_body = {"errno": 4000, "message": "Customer not found"}
        data = {"plan_id": "plan_123"}

        response = self.client.patch(
            "v1/sub/customer/user123/subscriptions/sub_test1",
            headers={"Authorization": "fake_payment_api_key"},
            data=json.dumps(data),
            content_type="application/json",
        )

        response_body = json.loads(response.data)
        assert response.status_code == 404
        assert response_body == expected_response_body

    def test_customer_fetch_error(self):
        self.get_subhub_user_mock.return_value = self.subhub_user
        self.retrieve_customer_mock.side_effect = stripe.error.InvalidRequestError(
            "message here", param="parameter"
        )

        data = {"plan_id": "plan_123"}

        response = self.client.patch(
            "v1/sub/customer/user123/subscriptions/sub_test1",
            headers={"Authorization": "fake_payment_api_key"},
            data=json.dumps(data),
            content_type="application/json",
        )

        assert response.status_code == 500

    def test_subscription_not_found(self):
        self.get_subhub_user_mock.return_value = self.subhub_user
        self.retrieve_customer_mock.return_value = self.customer

        expected_response_body = {"errno": 4001, "message": "Subscription not found"}
        data = {"plan_id": "plan_123"}

        response = self.client.patch(
            "v1/sub/customer/user123/subscriptions/sub_123",
            headers={"Authorization": "fake_payment_api_key"},
            data=json.dumps(data),
            content_type="application/json",
        )

        response_body = json.loads(response.data)
        assert response.status_code == 404
        assert response_body == expected_response_body

    def test_same_plan(self):
        self.get_subhub_user_mock.return_value = self.subhub_user
        self.retrieve_customer_mock.return_value = self.customer

        expected_response_body = {"errno": 1003, "message": "The plans are the same"}
        data = {"plan_id": "plan_test1"}

        response = self.client.patch(
            "v1/sub/customer/user123/subscriptions/sub_test1",
            headers={"Authorization": "fake_payment_api_key"},
            data=json.dumps(data),
            content_type="application/json",
        )

        response_body = json.loads(response.data)
        assert response.status_code == 400
        assert response_body == expected_response_body

    def test_different_intervals(self):
        self.get_subhub_user_mock.return_value = self.subhub_user
        self.retrieve_customer_mock.return_value = self.customer
        self.retrieve_plan_mock.return_value = self.plan2

        expected_response_body = {
            "errno": 1002,
            "message": "The plans do not have the same interval",
        }
        data = {"plan_id": "plan_test2"}

        response = self.client.patch(
            "v1/sub/customer/user123/subscriptions/sub_test1",
            headers={"Authorization": "fake_payment_api_key"},
            data=json.dumps(data),
            content_type="application/json",
        )

        response_body = json.loads(response.data)
        assert response.status_code == 400
        assert response_body == expected_response_body

    def test_different_intervals_count(self):
        self.get_subhub_user_mock.return_value = self.subhub_user
        self.retrieve_customer_mock.return_value = self.customer
        self.retrieve_plan_mock.return_value = self.plan5

        expected_response_body = {
            "errno": 1002,
            "message": "The plans do not have the same interval",
        }
        data = {"plan_id": "plan_test2"}

        response = self.client.patch(
            "v1/sub/customer/user123/subscriptions/sub_test1",
            headers={"Authorization": "fake_payment_api_key"},
            data=json.dumps(data),
            content_type="application/json",
        )

        response_body = json.loads(response.data)
        assert response.status_code == 400
        assert response_body == expected_response_body

    def test_plan_not_found(self):
        self.get_subhub_user_mock.return_value = self.subhub_user
        self.retrieve_customer_mock.return_value = self.customer
        self.retrieve_plan_mock.side_effect = stripe.error.InvalidRequestError(
            "message", param="param", http_status=404
        )

        expected_response_body = {"errno": 4003, "message": "Plan not found"}
        data = {"plan_id": "plan_test2"}

        response = self.client.patch(
            "v1/sub/customer/user123/subscriptions/sub_test1",
            headers={"Authorization": "fake_payment_api_key"},
            data=json.dumps(data),
            content_type="application/json",
        )

        response_body = json.loads(response.data)
        assert response.status_code == 404
        assert response_body == expected_response_body

    def test_plan_fetch_error(self):
        self.get_subhub_user_mock.return_value = self.subhub_user
        self.retrieve_customer_mock.return_value = self.customer
        self.retrieve_plan_mock.side_effect = stripe.error.InvalidRequestError(
            "message", param="param"
        )

        data = {"plan_id": "plan_test2"}

        response = self.client.patch(
            "v1/sub/customer/user123/subscriptions/sub_test1",
            headers={"Authorization": "fake_payment_api_key"},
            data=json.dumps(data),
            content_type="application/json",
        )

        assert response.status_code == 500

    def test_different_product_sets(self):
        self.get_subhub_user_mock.return_value = self.subhub_user
        self.retrieve_customer_mock.return_value = self.customer
        self.retrieve_plan_mock.return_value = self.plan4
        self.retrieve_product_mock.side_effect = [self.prod1_fpn, self.prod5_identity]

        expected_response_body = {
            "errno": 1001,
            "message": "The plans are not a part of a tiered relationship",
        }
        data = {"plan_id": "plan_test2"}

        response = self.client.patch(
            "v1/sub/customer/user123/subscriptions/sub_test1",
            headers={"Authorization": "fake_payment_api_key"},
            data=json.dumps(data),
            content_type="application/json",
        )

        response_body = json.loads(response.data)
        assert response.status_code == 400
        assert response_body == expected_response_body

    def test_no_product_sets(self):
        self.get_subhub_user_mock.return_value = self.subhub_user
        self.retrieve_customer_mock.return_value = self.customer
        self.retrieve_plan_mock.return_value = self.plan4
        self.retrieve_product_mock.side_effect = [self.prod2_none, self.prod3_none]

        expected_response_body = {
            "errno": 1001,
            "message": "The plans are not a part of a tiered relationship",
        }
        data = {"plan_id": "plan_test2"}

        response = self.client.patch(
            "v1/sub/customer/user123/subscriptions/sub_test1",
            headers={"Authorization": "fake_payment_api_key"},
            data=json.dumps(data),
            content_type="application/json",
        )

        response_body = json.loads(response.data)
        assert response.status_code == 400
        assert response_body == expected_response_body

    def test_product_not_found(self):
        self.get_subhub_user_mock.return_value = self.subhub_user
        self.retrieve_customer_mock.return_value = self.customer
        self.retrieve_plan_mock.return_value = self.plan4
        self.retrieve_product_mock.side_effect = stripe.error.InvalidRequestError(
            "message", param="param", http_status=404
        )

        expected_response_body = {"errno": 4002, "message": "Product not found"}
        data = {"plan_id": "plan_test2"}

        response = self.client.patch(
            "v1/sub/customer/user123/subscriptions/sub_test1",
            headers={"Authorization": "fake_payment_api_key"},
            data=json.dumps(data),
            content_type="application/json",
        )

        response_body = json.loads(response.data)
        assert response.status_code == 404
        assert response_body == expected_response_body

    def test_product_fetch_error(self):
        self.get_subhub_user_mock.return_value = self.subhub_user
        self.retrieve_customer_mock.return_value = self.customer
        self.retrieve_plan_mock.return_value = self.plan4
        self.retrieve_product_mock.side_effect = stripe.error.InvalidRequestError(
            "message", param="param"
        )

        data = {"plan_id": "plan_test2"}

        response = self.client.patch(
            "v1/sub/customer/user123/subscriptions/sub_test1",
            headers={"Authorization": "fake_payment_api_key"},
            data=json.dumps(data),
            content_type="application/json",
        )

        assert response.status_code == 500
