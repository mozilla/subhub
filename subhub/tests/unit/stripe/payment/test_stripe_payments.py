#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import mockito
import requests
import boto3
import flask

import stripe.error
from mockito import when, mock, unstub

from subhub.cfg import CFG
from subhub import secrets

from subhub.tests.unit.stripe.utils import run_test, MockSqsClient


def run_customer(mocker, data, filename):
    # using pytest mock
    mocker.patch.object(flask, "g")
    flask.g.return_value = ""

    run_test(filename)


def test_stripe_payment_intent_succeeded(mocker):
    invoice_response = mock(
        {
            "id": "in_000000",
            "object": "customer",
            "account_balance": 0,
            "created": 1563287210,
            "currency": "usd",
            "subscription": "sub_000000",
            "period_start": 1563287210,
            "period_end": 1563287210,
        },
        spec=stripe.Invoice,
    )
    when(stripe.Invoice).retrieve(id="in_000000").thenReturn(invoice_response)
    data = {
        "event_id": "evt_00000000000000",
        "event_type": "payment_intent.succeeded",
        "brand": "Visa",
        "last4": "4242",
        "exp_month": 6,
        "exp_year": 2020,
        "charge_id": "ch_000000",
        "invoice_id": "in_000000",
        "customer_id": "cus_000000",
        "amount_paid": 1000,
        "created": 1559568879,
        "subscription_id": "sub_000000",
        "period_start": 1563287210,
        "period_end": 1563287210,
        "currency": "usd",
    }
    basket_url = CFG.SALESFORCE_BASKET_URI + CFG.BASKET_API_KEY
    response = mockito.mock({"status_code": 200, "text": "Ok"}, spec=requests.Response)
    mockito.when(boto3).client("sqs", region_name=CFG.AWS_REGION).thenReturn(
        MockSqsClient
    )
    mockito.when(requests).post(basket_url, json=data).thenReturn(response)
    filename = "payment/payment-intent-succeeded.json"
    run_customer(mocker, data, filename)
    unstub()
