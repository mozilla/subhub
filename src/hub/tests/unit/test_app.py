# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import json
from unittest import TestCase
from mock import patch

from flask import jsonify
from stripe.error import AuthenticationError, CardError, StripeError
from hub.shared.exceptions import SubHubError

from hub.app import create_app
from hub.app import server_stripe_error
from hub.app import intermittent_stripe_error
from hub.app import server_stripe_error_with_params
from hub.app import server_stripe_card_error
from shared.cfg import CFG
from shared.log import get_logger

logger = get_logger()


def test_create_app():
    app = create_app()
    assert app
    # subhub_error = app.display_subhub_errors("bad things")
    print(f"subhub error {dir(app)} app= {app}")


def test_intermittent_stripe_error():
    expected = jsonify({"message": "something"}), 503
    error = StripeError("something")
    actual = intermittent_stripe_error(error)
    assert actual[0].json == expected[0].json
    assert actual[1] == expected[1]


def test_server_stripe_error():
    expected = (
        jsonify({"message": "Internal Server Error", "code": "500", "params": None}),
        500,
    )
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


class TestApp(TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.client = self.app.app.test_client()

    def test_custom_404(self):
        path = "/v1/versions"
        response = self.client.get(path)
        self.assertEqual(response.status_code, 404)
        # self.assertIn(path, response.data)
        print(f"path {path} data {response}")

    # def test_subhub_error(self):
    #     with pytest.raises(SubHubError) as subhub_error:
    #         expected = jsonify({"message": "something"}), 503
    #         error = StripeError("something")
    #         actual = intermittent_stripe_error(error)
    #         assert actual[0].json == expected[0].json
    #         assert actual[1] == expected[1]
    #         assert actual[0]["status_code"] == expected[0]["status_code"]
