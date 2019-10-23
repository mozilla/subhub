# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import mock
import json
import mockito
import requests
import boto3
import flask

from hub.shared.cfg import CFG
from hub.shared import secrets
from hub.shared.tests.unit.utils import run_test, MockSqsClient

CWD = os.path.realpath(os.path.dirname(__file__))


def run_customer(mocker, data, filename):
    # using pytest mock
    mocker.patch.object(flask, "g")
    flask.g.return_value = ""

    run_test(filename, cwd=CWD)


@mock.patch("stripe.Product.retrieve")
def test_stripe_invoice_payment_failed(mock_product, mocker):
    fh = open("tests/unit/fixtures/stripe_prod_test1.json")
    prod_test1 = json.loads(fh.read())
    fh.close()
    mock_product.return_value = prod_test1

    data = {
        "event_id": "evt_00000000000000",
        "event_type": "invoice.payment_failed",
        "customer_id": "cus_00000000000",
        "subscription_id": "sub_000000",
        "currency": "usd",
        "charge_id": "ch_000000",
        "amount_due": 100,
        "created": 1558624628,
        "nickname": "Project Guardian (Daily)",
    }
    basket_url = CFG.SALESFORCE_BASKET_URI + CFG.BASKET_API_KEY
    response = mockito.mock({"status_code": 200, "text": "Ok"}, spec=requests.Response)
    mockito.when(boto3).client("sqs", region_name=CFG.AWS_REGION).thenReturn(
        MockSqsClient
    )
    mockito.when(requests).post(basket_url, json=data).thenReturn(response)
    filename = "invoice-payment-failed.json"
    run_customer(mocker, data, filename)
