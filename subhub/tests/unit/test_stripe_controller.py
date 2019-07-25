#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import flask
from flask import Response

from mockito import when, mock, unstub

from subhub.tests.unit.stripe.utils import run_event_process
from subhub.log import get_logger

logger = get_logger()


def run_webhook(mocker, data):
    mocker.patch.object(flask, "g")
    flask.g.return_value = ""
    return run_event_process(data)


def test_controller_view(mocker):
    data = {
        "event_id": "evt_00000000000000",
        "type": "payment_intent.succeeded",
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
    webhook = run_webhook(mocker, data)
    assert isinstance(webhook, Response)
    unstub()


def test_controller_view_bad_data(mocker):
    data = "imalittleteapot"
    webhook = run_webhook(mocker, data)
    assert isinstance(webhook, Response)
    unstub()
