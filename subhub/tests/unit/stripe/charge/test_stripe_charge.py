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

from subhub.tests.unit.stripe.utils import run_test, MockSqsClient


def test_stripe_hub_succeeded(mocker):
    response = mockito.mock({"status_code": 200, "text": "Ok"}, spec=requests.Response)
    data = {
        "event_id": "evt_00000000000000",
        "event_type": "charge.succeeded",
        "charge_id": "evt_00000000000000",
        "invoice_id": None,
        "customer_id": None,
        "order_id": "6735",
        "card_last4": "4444",
        "card_brand": "mastercard",
        "card_exp_month": 8,
        "card_exp_year": 2019,
        "application_fee": None,
        "transaction_amount": 2000,
        "transaction_currency": "usd",
        "created_date": 1326853478,
    }

    # using mockito
    basket_url = CFG.SALESFORCE_BASKET_URI + CFG.BASKET_API_KEY
    mockito.when(requests).post(basket_url, json=data).thenReturn(response)
    mockito.when(boto3).client(
        "sqs",
        region_name=CFG.AWS_REGION,
        aws_access_key_id=CFG.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=CFG.AWS_SECRET_ACCESS_KEY,
    ).thenReturn(MockSqsClient)

    # using pytest mock
    mocker.patch.object(flask, "g")
    flask.g.return_value = ""
    flask.g.hub_table.get_event.return_value = ""

    # run the test
    run_test("charge/charge-succeeded.json")


def test_stripe_hub_badpayload():
    try:
        run_test("charge/badpayload.json")
    except ValueError as e:
        assert "this.will.break is not supported" == str(e)
