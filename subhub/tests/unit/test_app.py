#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from flask import jsonify
from stripe.error import AuthenticationError, CardError, StripeError

from subhub.app import create_app
from subhub.app import server_stripe_error
from subhub.app import intermittent_stripe_error
from subhub.app import server_stripe_error_with_params
from subhub.app import server_stripe_card_error


def test_create_app():
    app = create_app()
    assert app


def test_intermittent_stripe_error():
    expected = jsonify({"message": "something"}), 503
    error = StripeError("something")
    actual = intermittent_stripe_error(error)
    assert actual[0].json == expected[0].json
    assert actual[1] == expected[1]


def test_server_stripe_error():
    expected = jsonify({"message": "something", "code": "500", "params": None}), 500
    error = AuthenticationError("something", code="500")
    actual = server_stripe_error(error)
    assert actual[0].json == expected[0].json
    assert actual[1] == expected[1]


def test_server_stripe_error_with_params():
    expected = jsonify({"message": "something", "params": "param1", "code": "500"}), 500
    error = CardError("something", "param1", "500")
    actual = server_stripe_error_with_params(error)
    assert actual[0].json == expected[0].json
    assert actual[1] == expected[1]


def test_server_stripe_card_error():
    expected = jsonify({"message": "something", "code": "402"}), 402
    error = CardError("something", "param1", "402")
    actual = server_stripe_card_error(error)
    assert actual[0].json == expected[0].json
    assert actual[1] == expected[1]
