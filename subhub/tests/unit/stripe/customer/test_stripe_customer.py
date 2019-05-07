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


def test_stripe_webhook_customer_updated(mocker):
    data = {
        "event_id": "evt_00000000000000",
        "event_type": "customer.updated",
        "email": "jon@tester.com",
        "stripe_id": "cus_00000000000000",
        "name": "Jon Tester",
    }
    response = mockito.mock({"status_code": 200, "text": "Ok"}, spec=requests.Response)
    mockito.when(boto3).client("sqs", region_name=CFG.AWS_REGION).thenReturn(
        MockSqsClient
    )
    mockito.when(requests).post(CFG.SALESFORCE_BASKET_URI, data=data).thenReturn(
        response
    )
    filename = "customer/customer-updated.json"
    run_customer(mocker, data, filename)


def test_stripe_webhook_customer_deleted(mocker):
    data = {
        "event_id": "evt_00000000000000",
        "event_type": "customer.deleted",
        "email": "jon@tester.com",
        "stripe_id": "cus_00000000000000",
        "name": "Jon Tester",
        "user_id": None,
    }
    response = mockito.mock({"status_code": 200, "text": "Ok"}, spec=requests.Response)
    mockito.when(boto3).client(
        "sqs",
        region_name=CFG.AWS_REGION,
        aws_access_key_id=CFG.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=CFG.AWS_SECRET_ACCESS_KEY,
    ).thenReturn(MockSqsClient)
    mockito.when(requests).post(CFG.SALESFORCE_BASKET_URI, data=data).thenReturn(
        response
    )
    filename = "customer/customer-deleted.json"
    run_customer(mocker, data, filename)


def test_stripe_webhook_customer_subscription_created(mocker):
    data = {
        "event_id": "evt_00000000000000",
        "event_type": "customer.subscription.created",
        "stripe_id": "sub_00000000000000",
        "customer_id": "cus_00000000000000",
        "current_period_start": 1519435009,
        "current_period_end": 1521854209,
        "canceled_at": 1519680008,
        "days_until_due": None,
        "default_payment_method": None,
        "plan_id": "subhub-plan-api_00000000000000",
        "plan_amount": 500,
        "plan_currency": "usd",
        "plan_interval": "month",
        "status": "canceled",
        "trial_start": None,
        "trial_end": None,
        "tax_percent": None,
        "application_fee_percent": None,
        "user_id": None,
    }
    mockito.when(boto3).client(
        "sqs",
        region_name=CFG.AWS_REGION,
        aws_access_key_id=CFG.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=CFG.AWS_SECRET_ACCESS_KEY,
    ).thenReturn(MockSqsClient)
    response = mockito.mock({"status_code": 200, "text": "Ok"}, spec=requests.Response)
    mockito.when(requests).post(CFG.SALESFORCE_BASKET_URI, data=data).thenReturn(
        response
    )
    filename = "customer/customer-subscription-created.json"
    run_customer(mocker, data, filename)


def test_stripe_webhook_customer_subscription_updated(mocker):
    data = {
        "event_id": "evt_00000000000000",
        "event_type": "customer_subscription_updated",
        "stripe_id": "cus_00000000000000",
        "created": 1519435009,
        "subscription_created": 1519435009,
        "current_period_start": 1519435009,
        "current_period_end": 1521854209,
        "plan_amount": 500,
        "plan_currency": "usd",
        "plan_name": "subhub",
    }
    mockito.when(boto3).client(
        "sqs",
        region_name=CFG.AWS_REGION,
        aws_access_key_id=CFG.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=CFG.AWS_SECRET_ACCESS_KEY,
    ).thenReturn(MockSqsClient)
    response = mockito.mock({"status_code": 200, "text": "Ok"}, spec=requests.Response)
    mockito.when(requests).post(CFG.SALESFORCE_BASKET_URI, data=data).thenReturn(
        response
    )
    filename = "customer/customer-subscription-updated.json"
    run_customer(mocker, data, filename)


def test_stripe_webhook_customer_subscription_deleted(mocker):
    data = {
        "event_id": "evt_00000000000000",
        "event_type": "customer_subscription_deleted",
        "stripe_id": "cus_00000000000000",
        "created": 1519435009,
        "subscription_created": 1519435009,
        "current_period_start": 1519435009,
        "current_period_end": 1521854209,
        "plan_amount": 500,
        "plan_currency": "usd",
        "plan_name": "jollybilling",
    }
    mockito.when(boto3).client(
        "sqs",
        region_name=CFG.AWS_REGION,
        aws_access_key_id=CFG.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=CFG.AWS_SECRET_ACCESS_KEY,
    ).thenReturn(MockSqsClient)
    response = mockito.mock({"status_code": 200, "text": "Ok"}, spec=requests.Response)
    mockito.when(requests).post(CFG.SALESFORCE_BASKET_URI, data=data).thenReturn(
        response
    )
    filename = "customer/customer-subscription-deleted.json"
    run_customer(mocker, data, filename)
