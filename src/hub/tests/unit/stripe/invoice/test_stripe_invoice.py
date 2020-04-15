# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import mock
import unittest
import json
import time

from stripe.util import convert_to_stripe_object
from stripe.error import InvalidRequestError

from hub.vendor.invoices import (
    StripeInvoicePaymentFailed,
    StripeInvoicePaymentSucceeded,
)

from shared.log import get_logger

logger = get_logger()


class StripeInvoicePaymentFailedTest(unittest.TestCase):
    def setUp(self) -> None:
        with open("src/hub/tests/unit/fixtures/stripe_prod_test1.json") as fh:
            prod_test1 = json.loads(fh.read())
        self.product = convert_to_stripe_object(prod_test1)

        with open(
            "src/hub/tests/unit/fixtures/stripe_in_payment_failed_event.json"
        ) as fh:
            self.payment_failed_event = json.loads(fh.read())

        with open(
            "src/hub/tests/unit/fixtures/stripe_in_payment_failed_event_sub_create.json"
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
            "nickname": "Project Guardian",
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


class StripeInvoicePaymentSucceededTest(unittest.TestCase):
    def setUp(self) -> None:
        with open("src/hub/tests/unit/fixtures/stripe_sub_test_expanded.json") as fh:
            sub_test1 = json.loads(fh.read())
        self.subscription = convert_to_stripe_object(sub_test1)

        with open(
            "src/hub/tests/unit/fixtures/stripe_invoice_payment_succeeded_new_event.json"
        ) as fh:
            self.payment_succeeded_new_event = json.loads(fh.read())

        with open("src/hub/tests/unit/fixtures/stripe_in_test1.json") as fh:
            self.invoice = json.loads(fh.read())

        with open("src/hub/tests/unit/fixtures/stripe_sub_test4.json") as fh:
            self.subscription4 = json.loads(fh.read())

        with open("src/hub/tests/unit/fixtures/stripe_sub_test5.json") as fh:
            self.subscription5 = json.loads(fh.read())

        with open("src/hub/tests/unit/fixtures/stripe_sub_test6.json") as fh:
            self.subscription6 = json.loads(fh.read())

        with open("src/hub/tests/unit/fixtures/stripe_sub_test7.json") as fh:
            self.subscription7 = json.loads(fh.read())

        with open("src/hub/tests/unit/fixtures/stripe_sub_test8.json") as fh:
            self.subscription8 = json.loads(fh.read())

        with open("src/hub/tests/unit/fixtures/stripe_ch_test1.json") as fh:
            self.charge = json.loads(fh.read())

        subscription_patcher = mock.patch("stripe.Subscription.retrieve")
        invoice_patcher = mock.patch("stripe.Invoice.upcoming")
        invoice_retrieve_patcher = mock.patch("stripe.Invoice.retrieve")
        charge_retrieve_patcher = mock.patch("stripe.Charge.retrieve")
        run_pipeline_patcher = mock.patch("hub.routes.pipeline.RoutesPipeline.run")

        self.addCleanup(subscription_patcher.stop)
        self.addCleanup(invoice_patcher.stop)
        self.addCleanup(run_pipeline_patcher.stop)
        self.addCleanup(invoice_retrieve_patcher.stop)
        self.addCleanup(charge_retrieve_patcher.stop)

        self.mock_subscription = subscription_patcher.start()
        self.mock_invoice = invoice_patcher.start()
        self.mock_run_pipeline = run_pipeline_patcher.start()
        self.mock_retrieve_invoice = invoice_retrieve_patcher.start()
        self.mock_retrieve_charge = charge_retrieve_patcher.start()

    def test_run_success(self):
        self.mock_subscription.return_value = self.subscription
        self.mock_invoice.return_value = self.invoice
        self.mock_run_pipeline.return_value = None
        self.mock_retrieve_invoice.return_value = self.invoice
        self.mock_retrieve_charge.return_value = self.charge

        did_run = StripeInvoicePaymentSucceeded(self.payment_succeeded_new_event).run()

        assert did_run

    def test_run_new(self):
        self.subscription7["start_date"] = time.time()
        self.mock_subscription.return_value = self.subscription7
        self.mock_invoice.return_value = self.invoice
        self.mock_run_pipeline.return_value = None
        self.mock_retrieve_invoice.return_value = self.invoice
        self.mock_retrieve_charge.return_value = self.charge
        logger.error("run new ", success_event=type(self.payment_succeeded_new_event))
        self.payment_succeeded_new_event["data"]["object"]["created"] = time.time() - (
            24 * 60 * 60
        )

        did_run = StripeInvoicePaymentSucceeded(self.payment_succeeded_new_event).run()

        assert did_run
