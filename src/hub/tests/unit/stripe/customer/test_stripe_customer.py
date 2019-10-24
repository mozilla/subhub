# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import time
import json
import boto3
import flask
import stripe
import requests
import connexion
from unittest import TestCase
from mock import patch

from flask import g
from mockito import when, mock, unstub
from stripe.util import convert_to_stripe_object
from stripe.error import InvalidRequestError

from hub.app import create_app
from hub.vendor.customer import StripeCustomerSubscriptionUpdated
from hub.shared.exceptions import ClientError
from hub.shared.tests.unit.utils import run_test, MockSqsClient, MockSnsClient
from hub.shared.cfg import CFG
from shared.log import get_logger

logger = get_logger()

CWD = os.path.realpath(os.path.dirname(__file__))


def run_customer(mocker, data, filename):
    # using pytest mock
    mocker.patch.object(flask, "g")
    flask.g.return_value = ""

    run_test(filename, cwd=CWD)


def test_subhub():
    """
    Create an instance of the hub app and validate it is a FlaskApp
    """
    app = create_app()
    logger.debug("g", g=dir(g))
    assert isinstance(app, connexion.FlaskApp)


def test_stripe_hub_customer_created(mocker):
    data = {
        "event_id": "evt_00000000000000",
        "event_type": "customer.created",
        "email": "user123@tester.com",
        "customer_id": "cus_00000000000000",
        "name": "Jon Tester",
        "user_id": "user123",
    }
    basket_url = CFG.SALESFORCE_BASKET_URI + CFG.BASKET_API_KEY
    response = mock({"status_code": 200, "text": "Ok"}, spec=requests.Response)
    when(boto3).client("sqs", region_name=CFG.AWS_REGION).thenReturn(MockSqsClient)
    when(requests).post(basket_url, json=data).thenReturn(response)
    filename = "customer-created.json"
    run_customer(mocker, data, filename)


def test_stripe_hub_customer_updated(mocker):
    data = {
        "event_id": "evt_00000000000000",
        "event_type": "customer.updated",
        "email": "jon@tester.com",
        "customer_id": "cus_00000000000000",
        "name": "Jon Tester",
    }
    basket_url = CFG.SALESFORCE_BASKET_URI + CFG.BASKET_API_KEY
    logger.info("basket url", url=basket_url)
    response = mock({"status_code": 200, "text": "Ok"}, spec=requests.Response)
    when(boto3).client("sqs", region_name=CFG.AWS_REGION).thenReturn(MockSqsClient)
    when(requests).post(basket_url, json=data).thenReturn(response)
    filename = "customer-updated.json"
    run_customer(mocker, data, filename)


@patch("stripe.Product.retrieve")
def test_stripe_hub_customer_source_expiring(mock_product, mocker):
    fh = open("tests/unit/fixtures/stripe_prod_test1.json")
    prod_test1 = json.loads(fh.read())
    fh.close()
    mock_product.return_value = prod_test1

    data = {
        "event_id": "evt_00000000000000",
        "event_type": "customer.source.expiring",
        "email": "tester@johnson.com",
        "nickname": "Project Guardian (Monthly)",
        "customer_id": "cus_00000000000000",
        "last4": "4242",
        "brand": "Visa",
        "exp_month": 5,
        "exp_year": 2019,
    }

    customer_response = mock(
        {
            "id": "cus_00000000000000",
            "object": "customer",
            "account_balance": 0,
            "created": 1563287210,
            "currency": "usd",
            "metadata": {"userid": "user123"},
            "email": "tester@johnson.com",
            "subscriptions": {
                "data": [
                    {
                        "id": "1",
                        "status": "active",
                        "plan": {
                            "nickname": "moz plan",
                            "product": "prod_test1",
                            "interval": "month",
                        },
                    },
                    {
                        "id": "2",
                        "status": "canceled",
                        "plan": {
                            "nickname": "fxa plan",
                            "product": "prod_test1",
                            "interval": "month",
                        },
                    },
                ]
            },
        },
        spec=stripe.Customer,
    )
    when(stripe.Customer).retrieve(id="cus_00000000000000").thenReturn(
        customer_response
    )
    basket_url = CFG.SALESFORCE_BASKET_URI + CFG.BASKET_API_KEY
    response = mock({"status_code": 200, "text": "Ok"}, spec=requests.Response)
    # when(boto3).client("sqs", region_name=CFG.AWS_REGION).thenReturn(MockSqsClient)
    when(requests).post(basket_url, json=data).thenReturn(response)
    filename = "customer-source-expiring.json"
    run_customer(mocker, data, filename)


def test_stripe_hub_customer_subscription_created(mocker):
    data = {
        "event_id": "evt_00000000000000",
        "event_type": "customer.created",
        "email": "user123@tester.com",
        "customer_id": "cus_00000000000000",
        "name": "Jon Tester",
        "user_id": "user123",
    }
    basket_url = CFG.SALESFORCE_BASKET_URI + CFG.BASKET_API_KEY
    response = mock({"status_code": 200, "text": "Ok"}, spec=requests.Response)
    when(boto3).client("sns", region_name=CFG.AWS_REGION).thenReturn(MockSqsClient)
    when(requests).post(basket_url, json=data).thenReturn(response)
    filename = "customer-created.json"
    run_customer(mocker, data, filename)
    unstub()


@patch("flask.g.subhub_deleted_users.find_by_cust")
@patch("stripe.Customer.retrieve", autospec=True)
@patch("stripe.Product.retrieve")
def test_stripe_hub_customer_subscription_deleted(
    mock_product, mock_cust, mock_deleted_user, mocker
):
    fh = open("tests/unit/fixtures/stripe_prod_test1.json")
    prod_test1 = json.loads(fh.read())
    fh.close()
    mock_product.return_value = prod_test1
    data = {
        "uid": "tester123",
        "active": False,
        "subscriptionId": "sub_00000000000000",
        "productId": "jollybilling-plan-api_00000000000000",
        "eventId": "evt_00000000000000",
        "eventCreatedAt": 1326853478,
        "messageCreatedAt": int(time.time()),
    }
    mock_cust.return_value = {
        "id": "cus_00000000000000",
        "object": "customer",
        "account_balance": 0,
        "created": 1563287210,
        "currency": "usd",
        "metadata": dict(userid="tester123"),
    }
    mock_deleted_user.return_value = {"user_id": "user123"}
    when(boto3).client("sns", region_name=CFG.AWS_REGION).thenReturn(MockSnsClient)
    filename = "customer-subscription-deleted.json"
    run_customer(mocker, data, filename)
    unstub()


class StripeCustomerSubscriptionUpdatedTest(TestCase):
    def setUp(self) -> None:
        with open("tests/unit/fixtures/stripe_cust_test1.json") as fh:
            cust_test1 = json.loads(fh.read())
        self.customer = convert_to_stripe_object(cust_test1)

        with open("tests/unit/fixtures/stripe_cust_no_metadata.json") as fh:
            cust_no_metadata = json.loads(fh.read())
        self.customer_missing_user = convert_to_stripe_object(cust_no_metadata)

        with open("tests/unit/fixtures/stripe_prod_test1.json") as fh:
            prod_test1 = json.loads(fh.read())
        self.product = convert_to_stripe_object(prod_test1)

        with open("tests/unit/fixtures/stripe_in_test1.json") as fh:
            invoice_test1 = json.loads(fh.read())
        self.invoice = convert_to_stripe_object(invoice_test1)

        with open("tests/unit/fixtures/stripe_in_test2.json") as fh:
            invoice_test2 = json.loads(fh.read())
        self.incomplete_invoice = convert_to_stripe_object(invoice_test2)

        with open("tests/unit/fixtures/stripe_ch_test1.json") as fh:
            charge_test1 = json.loads(fh.read())
        self.charge = convert_to_stripe_object(charge_test1)

        with open("tests/unit/fixtures/stripe_ch_test2.json") as fh:
            charge_test2 = json.loads(fh.read())
        self.incomplete_charge = convert_to_stripe_object(charge_test2)

        with open("tests/unit/fixtures/stripe_sub_updated_event_cancel.json") as fh:
            self.subscription_cancelled_event = json.loads(fh.read())

        with open("tests/unit/fixtures/stripe_sub_updated_event_charge.json") as fh:
            self.subscription_charge_event = json.loads(fh.read())

        with open("tests/unit/fixtures/stripe_sub_updated_event_reactivate.json") as fh:
            self.subscription_reactivate_event = json.loads(fh.read())

        with open("tests/unit/fixtures/stripe_sub_updated_event_no_trigger.json") as fh:
            self.subscription_updated_event_no_match = json.loads(fh.read())

        customer_patcher = patch("stripe.Customer.retrieve")
        product_patcher = patch("stripe.Product.retrieve")
        invoice_patcher = patch("stripe.Invoice.retrieve")
        charge_patcher = patch("stripe.Charge.retrieve")
        run_pipeline_patcher = patch("hub.routes.pipeline.RoutesPipeline.run")

        self.addCleanup(customer_patcher.stop)
        self.addCleanup(product_patcher.stop)
        self.addCleanup(invoice_patcher.stop)
        self.addCleanup(charge_patcher.stop)
        self.addCleanup(run_pipeline_patcher.stop)

        self.mock_customer = customer_patcher.start()
        self.mock_product = product_patcher.start()
        self.mock_invoice = invoice_patcher.start()
        self.mock_charge = charge_patcher.start()
        self.mock_run_pipeline = run_pipeline_patcher.start()

    def test_run_cancel(self):
        self.mock_customer.return_value = self.customer
        self.mock_product.return_value = self.product
        self.mock_run_pipeline.return_value = None

        did_route = StripeCustomerSubscriptionUpdated(
            self.subscription_cancelled_event
        ).run()
        assert did_route

    def test_run_charge(self):
        self.mock_customer.return_value = self.customer
        self.mock_product.return_value = self.product
        self.mock_invoice.return_value = self.invoice
        self.mock_charge.return_value = self.charge
        self.mock_run_pipeline.return_value = None

        did_route = StripeCustomerSubscriptionUpdated(
            self.subscription_charge_event
        ).run()
        assert did_route

    def test_run_reactivate(self):
        self.mock_customer.return_value = self.customer
        self.mock_product.return_value = self.product
        self.mock_invoice.return_value = self.invoice
        self.mock_charge.return_value = self.charge
        self.mock_run_pipeline.return_value = None

        did_route = StripeCustomerSubscriptionUpdated(
            self.subscription_reactivate_event
        ).run()
        assert did_route

    def test_run_no_action(self):
        self.mock_customer.return_value = self.customer

        did_route = StripeCustomerSubscriptionUpdated(
            self.subscription_updated_event_no_match
        ).run()
        assert did_route == False

    def test_get_user_id_missing(self):
        self.mock_customer.return_value = self.customer_missing_user

        with self.assertRaises(ClientError):
            StripeCustomerSubscriptionUpdated(
                self.subscription_updated_event_no_match
            ).get_user_id("cust_123")

    def test_get_user_id_fetch_error(self):
        self.mock_customer.side_effect = InvalidRequestError(
            message="invalid data", param="bad data"
        )

        with self.assertRaises(InvalidRequestError):
            StripeCustomerSubscriptionUpdated(
                self.subscription_updated_event_no_match
            ).get_user_id("cust_123")

    def test_create_payload_error(self):
        self.mock_product.side_effect = InvalidRequestError(
            message="invalid data", param="bad data"
        )

        with self.assertRaises(InvalidRequestError):
            StripeCustomerSubscriptionUpdated(
                self.subscription_updated_event_no_match
            ).create_payload(event_type="event.type", user_id="user_123")
