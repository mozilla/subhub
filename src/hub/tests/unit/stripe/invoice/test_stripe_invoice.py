# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import mock
import unittest
import json

from stripe.util import convert_to_stripe_object
from stripe.error import InvalidRequestError

from hub.vendor.invoices import StripeInvoicePaymentFailed
from shared.cfg import CFG


class StripeInvoicePaymentFailedTest(unittest.TestCase):
    def setUp(self) -> None:
        from shared.cfg import CFG

        with open(
            f"{CFG.REPO_ROOT}/src/hub/tests/unit/fixtures/stripe_prod_test1.json"
        ) as fh:
            prod_test1 = json.loads(fh.read())
        self.product = convert_to_stripe_object(prod_test1)

        with open(
            f"{CFG.REPO_ROOT}/src/hub/tests/unit/fixtures/stripe_in_payment_failed_event.json"
        ) as fh:
            self.payment_failed_event = json.loads(fh.read())

        with open(
            f"{CFG.REPO_ROOT}/src/hub/tests/unit/fixtures/stripe_in_payment_failed_event_sub_create.json"
        ) as fh:
            self.payment_failed_event_sub_create = json.loads(fh.read())

        product_patcher = mock.patch("stripe.Product.retrieve")
        run_pipeline_patcher = mock.patch("hub.routes.pipeline.RoutesPipeline.run")

        self.addCleanup(product_patcher.stop)
        self.addCleanup(run_pipeline_patcher.stop)

        self.mock_product = product_patcher.start()
        self.mock_run_pipeline = run_pipeline_patcher.start()

    def test_run_success(self):
        self.mock_product.return_value = self.product
        self.mock_run_pipeline.return_value = None

        did_run = StripeInvoicePaymentFailed(self.payment_failed_event).run()

        assert did_run

    def test_run_subscription_create(self):
        self.mock_product.return_value = self.product
        self.mock_run_pipeline.return_value = None

        did_run = StripeInvoicePaymentFailed(self.payment_failed_event_sub_create).run()

        assert did_run == False

    def test_create_payload(self):
        self.mock_product.return_value = self.product

        expected_payload = {
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
        actual_payload = StripeInvoicePaymentFailed(
            self.payment_failed_event
        ).create_payload()

        assert expected_payload == actual_payload

    def test_create_payload_nickname_error(self):
        self.mock_product.side_effect = InvalidRequestError(message="", param="")

        expected_payload = {
            "event_id": "evt_00000000000000",
            "event_type": "invoice.payment_failed",
            "customer_id": "cus_00000000000",
            "subscription_id": "sub_000000",
            "currency": "usd",
            "charge_id": "ch_000000",
            "amount_due": 100,
            "created": 1558624628,
            "nickname": "",
        }
        actual_payload = StripeInvoicePaymentFailed(
            self.payment_failed_event
        ).create_payload()

        assert expected_payload == actual_payload
