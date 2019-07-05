#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import mockito
import requests
import boto3
import flask

from subhub.cfg import CFG
from subhub import secrets

from subhub.tests.unit.stripe.utils import run_test, MockSqsClient


def run_customer(mocker, data, filename):
    # using pytest mock
    mocker.patch.object(flask, "g")
    flask.g.return_value = ""

    run_test(filename)


def test_stripe_invoice_finalized(mocker):
    data = {
        "event_id": "evt_00000000000000",
        "event_type": "invoice.finalized",
        "customer_id": "cus_00000000000",
        "subscription_id": "sub_000000",
        "created": 1559568873,
        "period_start": 1559568873,
        "period_end": 1559568873,
        "amount_paid": 1000,
        "currency": "usd",
        "charge_id": "ch_0000000",
        "invoice_number": "C8828DAC-0001",
        "description": "1 Moz-Sub × Moz_Sub (at $10.00 / month)",
        "invoice_id": "in_0000000",
        "application_fee_amount": None,
    }
    basket_url = CFG.SALESFORCE_BASKET_URI + CFG.BASKET_API_KEY
    response = mockito.mock({"status_code": 200, "text": "Ok"}, spec=requests.Response)
    mockito.when(boto3).client("sqs", region_name=CFG.AWS_REGION).thenReturn(
        MockSqsClient
    )
    mockito.when(requests).post(basket_url, json=data).thenReturn(response)
    filename = "invoice/invoice-finalized.json"
    run_customer(mocker, data, filename)


def test_stripe_invoice_payment_failed(mocker):
    data = {
        "event_id": "evt_00000000000000",
        "event_type": "invoice.payment_failed",
        "customer_id": "cus_00000000000",
        "subscription_id": "sub_000000",
        "currency": "usd",
        "charge_id": "ch_000000",
        "invoice_number": "3D000-0003",
        "amount_due": 100,
        "created": 1558624628,
        "nickname": "Daily Subscription",
        "invoice_id": "in_000000",
    }
    basket_url = CFG.SALESFORCE_BASKET_URI + CFG.BASKET_API_KEY
    response = mockito.mock({"status_code": 200, "text": "Ok"}, spec=requests.Response)
    mockito.when(boto3).client("sqs", region_name=CFG.AWS_REGION).thenReturn(
        MockSqsClient
    )
    mockito.when(requests).post(basket_url, json=data).thenReturn(response)
    filename = "invoice/invoice-payment-failed.json"
    run_customer(mocker, data, filename)
