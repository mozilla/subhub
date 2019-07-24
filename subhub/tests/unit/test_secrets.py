#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import boto3

from mockito import when, mock, unstub

from subhub import secrets
from subhub.cfg import CFG
from subhub.exceptions import SecretStringMissingError


EXPECTED = {
    "STRIPE_API_KEY": "stripe_api_key_fake",
    "PAYMENT_API_KEY": "payment_api_key_fake",
    "SUPPORT_API_KEY": "support_api_key_fake",
    "HUB_API_KEY": "hub_api_key_fake",
    "SALESFORCE_BASKET_URI": "salesforce_basket_uri_fake",
    "FXA_SQS_URI": "fxa_sqs_uri_fake",
    "TOPIC_ARN_KEY": "topic_arn_key_fake",
    "BASKET_API_KEY": "basket_api_key_fake",
}


class MockSecretsManager:
    """
    This is the object for mocking the return values from boto3 for Secrets Manager
    """

    def get_secret_value(SecretId=None, VersionId=None, VersionStage=None):
        if SecretId in ("prod/subhub", "stage/subhub", "qa/subhub", "dev/subhub"):
            return {"Name": SecretId, "SecretString": json.dumps(EXPECTED)}
        return {"Name": SecretId}


def test_get_secret():
    """
    mock the boto3 return object and test expected vs actual
    """
    when(boto3).client(service_name="secretsmanager").thenReturn(MockSecretsManager)
    actual = secrets.get_secret("dev/subhub")
    assert actual == EXPECTED


def test_get_secret_exception():
    """
    if SecretString is not in returned value, throw exception; this exercises that
    """
    when(boto3).client(service_name="secretsmanager").thenReturn(MockSecretsManager)
    when(secrets).get_secret("bad_id").thenRaise(SecretStringMissingError)
