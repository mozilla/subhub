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


def test_stripe_payment_intent_succeeded(mocker):
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
    }
    response = mockito.mock({"status_code": 200, "text": "Ok"}, spec=requests.Response)
    mockito.when(boto3).client("sqs", region_name=CFG.AWS_REGION).thenReturn(
        MockSqsClient
    )
    mockito.when(requests).post(CFG.SALESFORCE_BASKET_URI, data=data).thenReturn(
        response
    )
    filename = "payment/payment-intent-succeeded.json"
    run_customer(mocker, data, filename)
