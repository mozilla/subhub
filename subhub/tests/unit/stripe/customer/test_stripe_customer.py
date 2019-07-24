#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import time

import boto3
import flask
import stripe
import requests

from mockito import when, mock, unstub

from subhub.tests.unit.stripe.utils import run_test, MockSqsClient, MockSnsClient
from subhub.cfg import CFG
from subhub.log import get_logger

logger = get_logger()


def run_customer(mocker, data, filename):
    # using pytest mock
    mocker.patch.object(flask, "g")
    flask.g.return_value = ""

    run_test(filename)


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
    filename = "customer/customer-created.json"
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
    filename = "customer/customer-deleted.json"
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
    filename = "customer/customer-updated.json"
    run_customer(mocker, data, filename)


def test_stripe_hub_customer_source_expiring(mocker):
    data = {
        "event_id": "evt_00000000000000",
        "event_type": "customer.source.expiring",
        "customer_id": "cus_00000000000000",
        "last4": "4242",
        "brand": "Visa",
        "exp_month": 5,
        "exp_year": 2019,
        "nickname": "moz plan",
        "email": "tester@johnson.com",
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
                    {"id": "1", "status": "active", "plan": {"nickname": "moz plan"}},
                    {"id": "2", "status": "canceled", "plan": {"nickname": "fxa plan"}},
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
    filename = "customer/customer-source-expiring.json"
    run_customer(mocker, data, filename)


def test_stripe_hub_customer_subscription_created(mocker):
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
    data = {
        "uid": "user123",
        "active": True,
        "subscriptionId": "sub_00000000000000",
        "subscription_id": "sub_00000000000000",
        "productName": "subhub",
        "eventId": "evt_00000000000000",
        "eventCreatedAt": 1326853478,
        "messageCreatedAt": int(time.time()),
        "invoice_id": "in_test123",
        "plan_amount": 500,
        "customer_id": "cus_00000000000000",
        "nickname": "subhub",
        "created": 1519363457,
        "canceled_at": 1519680008,
        "cancel_at": None,
        "event_type": "customer.subscription.created",
        "event_id": "evt_00000000000000",
        "cancel_at_period_end": False,
    }
    logger.info("created payload", data=data)
    basket_url = CFG.SALESFORCE_BASKET_URI + CFG.BASKET_API_KEY
    response = mock({"status_code": 200, "text": "Ok"}, spec=requests.Response)
    when(boto3).client("sns", region_name=CFG.AWS_REGION).thenReturn(MockSnsClient)
    when(requests).post(basket_url, json=data).thenReturn(response)
    filename = "customer/customer-subscription-created.json"
    run_customer(mocker, data, filename)
    unstub()


def test_stripe_hub_customer_subscription_updated_cancel(mocker):

    data = {
        "event_id": "evt_00000000000000",
        "eventId": "evt_00000000000000",
        "event_type": "customer.subscription.updated",
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

    basket_url = CFG.SALESFORCE_BASKET_URI + CFG.BASKET_API_KEY
    response = mock({"status_code": 200, "text": "Ok"}, spec=requests.Response)
    when(boto3).client("sns", region_name=CFG.AWS_REGION).thenReturn(MockSnsClient)
    when(requests).post(basket_url, json=data).thenReturn(response)
    filename = "customer/customer-subscription-updated.json"
    run_customer(mocker, data, filename)
    unstub()


def test_stripe_hub_customer_subscription_updated_no_cancel(mocker):
    data = {
        "event_id": "evt_00000000000000",
        "event_type": "customer.subscription.updated",
        "customer_id": "cus_00000000000000",
        "subscription_id": "sub_00000000000000",
        "subscriptionId": "sub_00000000000000",
        "plan_amount": 500,
        "canceled_at": 1519680008,
        "cancel_at": 1521854209,
        "cancel_at_period_end": False,
        "nickname": "subhub",
        "active": False,
        "productName": "subhub",
        "invoice_id": "in_test123",
        "created": 1519363457,
        "amount_paid": 500,
        "eventId": "evt_00000000000000",
        "messageCreatedAt": int(time.time()),
        "eventCreatedAt": 1326853478,
        "uid": "user123",
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

    basket_url = CFG.SALESFORCE_BASKET_URI + CFG.BASKET_API_KEY
    response = mock({"status_code": 200, "text": "Ok"}, spec=requests.Response)
    when(boto3).client("sns", region_name=CFG.AWS_REGION).thenReturn(MockSnsClient)
    when(requests).post(basket_url, json=data).thenReturn(response)
    filename = "customer/customer-subscription-updated-no-cancel.json"
    run_customer(mocker, data, filename)
    unstub()


def test_stripe_hub_customer_subscription_deleted(mocker):
    data = dict(
        active=False,
        subscriptionId="sub_00000000000000",
        productName="jollybilling",
        eventId="evt_00000000000000",
        event_id="evt_00000000000000",
        eventCreatedAt=1326853478,
        messageCreatedAt=int(time.time()),
    )
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
    basket_url = CFG.SALESFORCE_BASKET_URI + CFG.BASKET_API_KEY
    response = mock({"status_code": 200, "text": "Ok"}, spec=requests.Response)
    when(boto3).client("sns", region_name=CFG.AWS_REGION).thenReturn(MockSnsClient)
    when(requests).post(basket_url, json=data).thenReturn(response)
    filename = "customer/customer-subscription-deleted.json"
    run_customer(mocker, data, filename)
    unstub()
