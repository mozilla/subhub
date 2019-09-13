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

from mock import patch
from mockito import when, mock, unstub

from hub.shared.tests.unit.utils import run_test, MockSqsClient, MockSnsClient
from hub.shared.cfg import CFG
from hub.shared.log import get_logger

logger = get_logger()

CWD = os.path.realpath(os.path.dirname(__file__))


def run_customer(mocker, data, filename):
    # using pytest mock
    mocker.patch.object(flask, "g")
    flask.g.return_value = ""

    run_test(filename, cwd=CWD)


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


def test_stripe_hub_customer_deleted(mocker):
    data = {
        "event_id": "evt_00000000000000",
        "event_type": "customer.deleted",
        "email": "jon@tester.com",
        "customer_id": "cus_00000000000000",
        "name": "Jon Tester",
        "user_id": "user123",
    }
    basket_url = CFG.SALESFORCE_BASKET_URI + CFG.BASKET_API_KEY
    response = mock({"status_code": 200, "text": "Ok"}, spec=requests.Response)
    when(boto3).client(
        "sqs",
        region_name=CFG.AWS_REGION,
        aws_access_key_id=CFG.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=CFG.AWS_SECRET_ACCESS_KEY,
    ).thenReturn(MockSnsClient)
    when(requests).post(basket_url, json=data).thenReturn(response)
    filename = "customer-deleted.json"
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


def test_stripe_hub_customer_subscription_updated_cancel(mocker):

    data = {
        "event_id": "evt_00000000000000",
        "eventId": "evt_00000000000000",
        "event_type": "customer.subscription_cancelled",
        "customer_id": "cus_00000000000000",
        "subscription_id": "sub_00000000000000",
        "subscriptionId": "sub_00000000000000",
        "plan_amount": 500,
        "canceled_at": 1519680008,
        "cancel_at": 1521854209,
        "cancel_at_period_end": True,
        "nickname": "subhub",
        "messageCreatedAt": int(time.time()),
        "invoice_id": "in_test123",
        "uid": "user123",
        "latest_invoice": "in_test123",
    }
    customer_response = mock(
        {
            "id": "cus_00000000000000",
            "object": "customer",
            "account_balance": 0,
            "created": 1563287210,
            "currency": "usd",
            "metadata": {"userid": "user123"},
        },
        spec=stripe.Customer,
    )

    when(stripe.Customer).retrieve(id="cus_00000000000000").thenReturn(
        customer_response
    )
    invoice_response = mock(
        {"invoice_number": "in_123", "charge": "ch_123"}, spec=stripe.Invoice
    )
    when(stripe.Invoice).retrieve(id="in_test123").thenReturn(invoice_response)
    invoice_response = mock(
        {"number": "in_123", "charge": "ch_123"}, spec=stripe.Invoice
    )
    when(stripe.Invoice).retrieve(id="in_test123").thenReturn(invoice_response)
    charge_response = mock(
        {"payment_method_details": {"card": {"last4": "9999", "brand": "visa"}}},
        spec=stripe.Invoice,
    )
    when(stripe.Charge).retrieve(id="ch_123").thenReturn(charge_response)

    basket_url = CFG.SALESFORCE_BASKET_URI + CFG.BASKET_API_KEY
    response = mock({"status_code": 200, "text": "Ok"}, spec=requests.Response)
    when(boto3).client("sns", region_name=CFG.AWS_REGION).thenReturn(MockSnsClient)
    when(requests).post(basket_url, json=data).thenReturn(response)
    filename = "customer-subscription-updated.json"
    run_customer(mocker, data, filename)
    unstub()


def test_stripe_hub_customer_subscription_updated_no_cancel(mocker):
    customer_response = mock(
        {
            "id": "cus_00000000000000",
            "object": "customer",
            "account_balance": 0,
            "created": 1519435009,
            "currency": "usd",
            "metadata": {"userid": "user123"},
            "latest_invoice": "in_123",
            "current_period_start": 1521854209,
            "current_period_end": 1519435009,
        },
        spec=stripe.Customer,
    )
    when(stripe.Customer).retrieve(id="cus_00000000000000").thenReturn(
        customer_response
    )
    invoice_response = mock(
        {"number": "in_123", "charge": "ch_123"}, spec=stripe.Invoice
    )
    when(stripe.Invoice).retrieve(id="in_test123").thenReturn(invoice_response)
    charge_response = mock(
        {"payment_method_details": {"card": {"last4": "9999", "brand": "visa"}}},
        spec=stripe.Invoice,
    )
    when(stripe.Charge).retrieve(id="ch_123").thenReturn(charge_response)
    data = {
        "eventId": "evt_00000000000000",
        "event_type": "customer.subscription_cancelled",
        "uid": "user123",
        "active": True,
        "subscriptionId": "sub_00000000000000",
        "subscription_id": "sub_00000000000000",
        "productName": "subhub",
        "eventCreatedAt": 1519435009,
        "messageCreatedAt": int(time.time()),
        "invoice_id": "in_test123",
        "plan_amount": 500,
        "customer_id": "cus_00000000000000",
        "nickname": "subhub",
        "created": 1519363457,
        "canceled_at": 1519680008,
        "cancel_at": None,
        "event_id": "evt_00000000000000",
        "cancel_at_period_end": False,
        "currency": "USD",
        "customer": "cus_00000000000000",
        "current_period_start": 1563287210,
        "current_period_end": 1563287210,
        "invoice_number": "in_123",
        "brand": "visa",
        "last4": "9999",
        "charge": "ch_123",
    }
    logger.info("created payload", data=data)
    basket_url = CFG.SALESFORCE_BASKET_URI + CFG.BASKET_API_KEY
    response = mock({"status_code": 200, "text": "Ok"}, spec=requests.Response)
    when(boto3).client("sns", region_name=CFG.AWS_REGION).thenReturn(MockSnsClient)
    when(requests).post(basket_url, json=data).thenReturn(response)
    filename = "customer-subscription-updated-no-cancel.json"
    run_customer(mocker, data, filename)
    unstub()


@patch("stripe.Product.retrieve")
def test_stripe_hub_customer_subscription_deleted(mock_product, mocker):
    fh = open("tests/unit/fixtures/stripe_prod_test1.json")
    prod_test1 = json.loads(fh.read())
    fh.close()
    mock_product.return_value = prod_test1
    data = {
        "active": False,
        "subscriptionId": "sub_00000000000000",
        "productName": "jollybilling",
        "eventId": "evt_00000000000000",
        "event_id": "evt_00000000000000",
        "eventCreatedAt": 1326853478,
        "messageCreatedAt": int(time.time()),
    }
    customer_response = mock(
        {
            "id": "cus_00000000000000",
            "object": "customer",
            "account_balance": 0,
            "created": 1563287210,
            "currency": "usd",
            "metadata": {"userid": "user123"},
        },
        spec=stripe.Customer,
    )
    when(stripe.Customer).retrieve(id="cus_00000000000000").thenReturn(
        customer_response
    )
    when(boto3).client("sns", region_name=CFG.AWS_REGION).thenReturn(MockSnsClient)
    filename = "customer-subscription-deleted.json"
    run_customer(mocker, data, filename)
    unstub()
