# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import os
import json
from unittest import TestCase
from mock import patch

from stripe.error import APIError, APIConnectionError, InvalidRequestError
from stripe.util import convert_to_stripe_object

from sub.shared import vendor, utils

DIRECTORY = os.path.dirname(__file__)


class TestStripeCustomerCalls(TestCase):
    def setUp(self):
        with open(os.path.join(DIRECTORY, "fixtures/stripe_cust_test1.json")) as fh:
            customer = json.loads(fh.read())
        self.customer = convert_to_stripe_object(customer)

        with open(os.path.join(DIRECTORY, "fixtures/stripe_deleted_cust.json")) as fh:
            deleted_customer = json.loads(fh.read())
        self.deleted_customer = convert_to_stripe_object(deleted_customer)

        create_customer_patcher = patch("stripe.Customer.create")
        retrieve_customer_patcher = patch("stripe.Customer.retrieve")
        list_customer_patcher = patch("stripe.Customer.list")
        modify_customer_patcher = patch("stripe.Customer.modify")
        delete_customer_patcher = patch("stripe.Customer.delete")

        self.addCleanup(create_customer_patcher.stop)
        self.addCleanup(retrieve_customer_patcher.stop)
        self.addCleanup(list_customer_patcher.stop)
        self.addCleanup(modify_customer_patcher.stop)
        self.addCleanup(delete_customer_patcher.stop)

        self.create_customer_mock = create_customer_patcher.start()
        self.retrieve_customer_mock = retrieve_customer_patcher.start()
        self.list_customer_mock = list_customer_patcher.start()
        self.modify_customer_mock = modify_customer_patcher.start()
        self.delete_customer_mock = delete_customer_patcher.start()

    def test_create_success(self):
        self.create_customer_mock.side_effect = [APIError("message"), self.customer]

        customer = vendor.create_stripe_customer(  # nosec
            source_token="token",
            email="user@example.com",
            userid="user_123",
            name="Test User",
            idempotency_key=utils.get_indempotency_key(),
        )

        assert customer == self.customer  # nosec

    def test_create_error(self):
        self.create_customer_mock.side_effect = APIError("message")

        with self.assertRaises(APIError):
            vendor.create_stripe_customer(  # nosec
                source_token="token",
                email="user@example.com",
                userid="user_123",
                name="Test User",
                idempotency_key=utils.get_indempotency_key(),
            )

    def test_retrieve_success(self):
        self.retrieve_customer_mock.side_effect = [APIError("message"), self.customer]

        customer = vendor.retrieve_stripe_customer(customer_id="cust_123")

        assert customer == self.customer  # nosec

    def test_retrieve_error(self):
        self.retrieve_customer_mock.side_effect = APIError("message")

        with self.assertRaises(APIError):
            vendor.retrieve_stripe_customer(customer_id="cust_123")

    def test_list_success(self):
        self.list_customer_mock.side_effect = [APIError("message"), [self.customer]]

        customer_list = vendor.get_customer_list("user@example.com")

        assert customer_list == [self.customer]  # nosec

    def test_list_error(self):
        self.list_customer_mock.side_effect = APIError("message")

        with self.assertRaises(APIError):
            vendor.get_customer_list("user@example.com")

    def test_modify_success(self):
        self.modify_customer_mock.side_effect = [APIError("message"), self.customer]

        customer = vendor.modify_customer(  # nosec
            customer_id="cust_123",
            source_token="token",
            idempotency_key=utils.get_indempotency_key(),
        )

        assert customer == self.customer  # nosec

    def test_modify_error(self):
        self.modify_customer_mock.side_effect = APIError("message")

        with self.assertRaises(APIError):
            vendor.modify_customer(  # nosec
                customer_id="cust_123",
                source_token="token",
                idempotency_key=utils.get_indempotency_key(),
            )

    def test_delete_success(self):
        self.delete_customer_mock.side_effect = [
            APIError("message"),
            self.deleted_customer,
        ]

        deleted_customer = vendor.delete_stripe_customer(customer_id="cust_123")

        assert deleted_customer == self.deleted_customer  # nosec

    def test_delete_error(self):
        self.delete_customer_mock.side_effect = APIError("message")

        with self.assertRaises(APIError):
            vendor.delete_stripe_customer(customer_id="cust_123")


class TestStripeSubscriptionCalls(TestCase):
    def setUp(self) -> None:
        with open(os.path.join(DIRECTORY, "fixtures/stripe_sub_test1.json")) as fh:
            sub = json.loads(fh.read())

        with open(os.path.join(DIRECTORY, "fixtures/stripe_plan_test1.json")) as fh:
            plan = json.loads(fh.read())

        sub["plan"] = plan
        sub["items"] = {"object": "list", "data": [{"id": "si_test1", "plan": plan}]}

        self.subscription = convert_to_stripe_object(sub)

        self.list = [self.subscription]

        create_subcription_patcher = patch("stripe.Subscription.create")
        retrieve_subscription_patcher = patch("stripe.Subscription.retrieve")
        list_subscription_patcher = patch("stripe.Subscription.list")
        modify_subscription_patcher = patch("stripe.Subscription.modify")
        delete_subscription_patcher = patch("stripe.Subscription.delete")

        self.addCleanup(create_subcription_patcher.stop)
        self.addCleanup(retrieve_subscription_patcher.stop)
        self.addCleanup(list_subscription_patcher.stop)
        self.addCleanup(modify_subscription_patcher.stop)
        self.addCleanup(delete_subscription_patcher.stop)

        self.mock_create_subscription = create_subcription_patcher.start()
        self.mock_retrieve_subscription = retrieve_subscription_patcher.start()
        self.mock_list_subscription = list_subscription_patcher.start()
        self.mock_modify_subscription = modify_subscription_patcher.start()
        self.mock_delete_subscription = delete_subscription_patcher.start()

    def test_build_success(self):
        self.mock_create_subscription.side_effect = [
            APIError("message"),
            self.subscription,
        ]

        subscription = vendor.build_stripe_subscription(
            customer_id="cust_123",
            plan_id="plan_123",
            idempotency_key=utils.get_indempotency_key(),
        )

        assert subscription == self.subscription  # nosec

    def test_build_error(self):
        self.mock_create_subscription.side_effect = APIError("message")

        with self.assertRaises(APIError):
            vendor.build_stripe_subscription(
                customer_id="cust_123",
                plan_id="plan_123",
                idempotency_key=utils.get_indempotency_key(),
            )

    def test_update_success(self):
        self.mock_modify_subscription.side_effect = [
            APIError("message"),
            self.subscription,
        ]
        subscription = vendor.update_stripe_subscription(
            subscription=self.subscription,
            plan_id="plan_123",
            idempotency_key=utils.get_indempotency_key(),
        )
        assert subscription == self.subscription  # nosec

    def test_update_error(self):
        self.mock_modify_subscription.side_effect = APIError("message")

        with self.assertRaises(APIError):
            vendor.update_stripe_subscription(
                subscription=self.subscription,
                plan_id="plan_123",
                idempotency_key=utils.get_indempotency_key(),
            )

    def test_cancel_at_end_success(self):
        self.mock_modify_subscription.side_effect = [
            APIError("message"),
            self.subscription,
        ]

        subscription = vendor.cancel_stripe_subscription_period_end(
            subscription_id="sub_123", idempotency_key=utils.get_indempotency_key()
        )

        assert subscription == self.subscription  # nosec

    def test_cancel_at_end_error(self):
        self.mock_modify_subscription.side_effect = APIError("message")

        with self.assertRaises(APIError):
            vendor.cancel_stripe_subscription_period_end(
                subscription_id="sub_123", idempotency_key=utils.get_indempotency_key()
            )

    def test_cancel_immediately_success(self):
        self.mock_delete_subscription.side_effect = [
            APIError("message"),
            self.subscription,
        ]

        subscription = vendor.cancel_stripe_subscription_immediately(
            subscription_id="sub_123", idempotency_key=utils.get_indempotency_key()
        )

        assert subscription == self.subscription  # nosec

    def test_cancel_immediately_error(self):
        self.mock_delete_subscription.side_effect = APIError("message")

        with self.assertRaises(APIError):
            vendor.cancel_stripe_subscription_immediately(
                subscription_id="sub_123", idempotency_key=utils.get_indempotency_key()
            )

    def test_reactivate_success(self):
        self.mock_modify_subscription.side_effect = [
            APIError("message"),
            self.subscription,
        ]

        subscription = vendor.reactivate_stripe_subscription(
            subscription_id="sub_123", idempotency_key=utils.get_indempotency_key()
        )

        assert subscription == self.subscription  # nosec

    def test_reactivate_error(self):
        self.mock_modify_subscription.side_effect = APIError("message")

        with self.assertRaises(APIError):
            vendor.reactivate_stripe_subscription(
                subscription_id="sub_123", idempotency_key=utils.get_indempotency_key()
            )

    def test_list_success(self):
        self.mock_list_subscription.side_effect = [APIError("message"), self.list]

        subscription_list = vendor.list_customer_subscriptions(cust_id="cust_123")

        assert subscription_list == self.list  # nosec

    def test_list_error(self):
        self.mock_list_subscription.side_effect = APIError("message")

        with self.assertRaises(APIError):
            vendor.list_customer_subscriptions(cust_id="cust_123")


class TestStripeChargeCalls(TestCase):
    def setUp(self) -> None:
        with open(os.path.join(DIRECTORY, "fixtures/stripe_ch_test1.json")) as fh:
            charge = json.loads(fh.read())
        self.charge = convert_to_stripe_object(charge)

        with open(os.path.join(DIRECTORY, "fixtures/stripe_ch_test2.json")) as fh:
            charge2 = json.loads(fh.read())
        self.charge2 = convert_to_stripe_object(charge)

        retrieve_charge_patcher = patch("stripe.Charge.retrieve")
        self.addCleanup(retrieve_charge_patcher.stop)
        self.retrieve_charge_mock = retrieve_charge_patcher.start()

    def test_retrieve_success(self):
        self.retrieve_charge_mock.side_effect = [APIError("message"), self.charge]

        charge = vendor.retrieve_stripe_charge("in_test1")
        assert charge == self.charge  # nosec

    def test_retrieve_no_charge_id(self):
        self.retrieve_charge_mock.side_effect = [APIError("message"), self.charge2]

        charge = vendor.retrieve_stripe_charge("in_test1")
        assert charge == self.charge2  # nosec

    def test_retrieve_error(self):
        self.retrieve_charge_mock.side_effect = APIError("message")

        with self.assertRaises(APIError):
            vendor.retrieve_stripe_charge("in_test1")


class TestStripeInvoiceCalls(TestCase):
    def setUp(self) -> None:
        with open(os.path.join(DIRECTORY, "fixtures/stripe_in_test1.json")) as fh:
            invoice = json.loads(fh.read())
        self.invoice = convert_to_stripe_object(invoice)

        retrieve_invoice_patcher = patch("stripe.Invoice.retrieve")
        preview_invoice_patcher = patch("stripe.Invoice.upcoming")

        self.addCleanup(retrieve_invoice_patcher.stop)
        self.addCleanup(preview_invoice_patcher.stop)

        self.retrieve_invoice_mock = retrieve_invoice_patcher.start()
        self.preview_invoice_mock = preview_invoice_patcher.start()

    def test_retrieve_success(self):
        self.retrieve_invoice_mock.side_effect = [APIError("message"), self.invoice]

        invoice = vendor.retrieve_stripe_invoice("in_test1")
        assert invoice == self.invoice  # nosec

    def test_retrieve_error(self):
        self.retrieve_invoice_mock.side_effect = APIError("message")

        with self.assertRaises(APIError):
            vendor.retrieve_stripe_invoice("in_test1")

    def test_upcoming_by_subscription_success(self):
        self.preview_invoice_mock.side_effect = [APIError("message"), self.invoice]

        invoice = vendor.retrieve_stripe_invoice_upcoming_by_subscription(
            customer_id="cust_123", subscription_id="sub_123"
        )
        assert invoice == self.invoice  # nosec

    def test_upcoming_by_subscription_error(self):
        self.preview_invoice_mock.side_effect = APIError("message")

        with self.assertRaises(APIError):
            vendor.retrieve_stripe_invoice_upcoming_by_subscription(
                customer_id="cust_123", subscription_id="sub_123"
            )

    def test_upcoming_success(self):
        self.preview_invoice_mock.return_value = self.invoice

        invoice = vendor.retrieve_stripe_invoice_upcoming(customer="cust_123")
        assert invoice == self.invoice  # nosec

    def test_upcoming_error(self):
        self.preview_invoice_mock.side_effect = APIError("message")

        with self.assertRaises(APIError):
            vendor.retrieve_stripe_invoice_upcoming(customer="cust_123")


class TestStripePlanCalls(TestCase):
    def setUp(self) -> None:
        with open(os.path.join(DIRECTORY, "fixtures/stripe_plan_test1.json")) as fh:
            plan = json.loads(fh.read())
        self.plan = convert_to_stripe_object(plan)

        self.plan_list = [self.plan]

        retrieve_plan_patcher = patch("stripe.Plan.retrieve")
        list_plan_patcher = patch("stripe.Plan.list")
        self.addCleanup(retrieve_plan_patcher.stop)
        self.addCleanup(list_plan_patcher.stop)
        self.retrieve_plan_mock = retrieve_plan_patcher.start()
        self.list_plan_mock = list_plan_patcher.start()

    def test_retrieve_list_success(self):
        self.list_plan_mock.side_effect = [APIError("message"), self.plan_list]

        plan_list = vendor.retrieve_plan_list(1)
        assert plan_list == self.plan_list  # nosec

    def test_retrieve_list_error(self):
        self.list_plan_mock.side_effect = APIError("message")

        with self.assertRaises(APIError):
            vendor.retrieve_plan_list(1)

    def test_retrieve_success(self):
        self.retrieve_plan_mock.side_effect = [APIConnectionError("message"), self.plan]

        plan = vendor.retrieve_stripe_plan("plan_test1")

        assert plan == self.plan  # nosec

    def test_retrieve_error(self):
        self.retrieve_plan_mock.side_effect = InvalidRequestError(
            "message", param="plan_id"
        )

        with self.assertRaises(InvalidRequestError) as e:
            vendor.retrieve_stripe_plan("plan_test1")


class TestStripeProductCalls(TestCase):
    def setUp(self) -> None:
        with open(os.path.join(DIRECTORY, "fixtures/stripe_prod_test1.json")) as fh:
            prod = json.loads(fh.read())
        self.product = convert_to_stripe_object(prod)

        retrieve_product_patcher = patch("stripe.Product.retrieve")
        self.addCleanup(retrieve_product_patcher.stop)
        self.retrieve_product_mock = retrieve_product_patcher.start()

    def test_retrieve_success(self):
        self.retrieve_product_mock.side_effect = [
            APIConnectionError("message"),
            self.product,
        ]

        product = vendor.retrieve_stripe_product("prod_test1")

        assert product == self.product  # nosec

    def test_retrieve_error(self):
        self.retrieve_product_mock.side_effect = InvalidRequestError(
            "message", param="prod_id"
        )

        with self.assertRaises(InvalidRequestError):
            vendor.retrieve_stripe_product("prod_test1")
