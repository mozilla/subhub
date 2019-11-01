# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json

from sub.payments import (
    subscribe_to_plan,
    find_newest_subscription,
    cancel_subscription,
    delete_customer,
    delete_user,
    support_status,
    subscription_status,
    update_payment_method,
    customer_update,
    create_update_data,
)

from unittest import TestCase
from unittest.mock import DEFAULT
from mock import patch, PropertyMock, MagicMock
from stripe.util import convert_to_stripe_object
from stripe import Customer

from shared.log import get_logger

logger = get_logger()


class TestPayments(TestCase):
    def setUp(self) -> None:
        from shared.cfg import CFG

        with open(
            f"{CFG.REPO_ROOT}/src/sub/tests/unit/fixtures/stripe_cust_test1.json"
        ) as fh:
            cust_test1 = json.loads(fh.read())
            fh.close()
        self.valid_customer = convert_to_stripe_object(cust_test1)

        with open(
            f"{CFG.REPO_ROOT}/src/sub/tests/unit/fixtures/stripe_cust_test2.json"
        ) as fh:
            cust_test2 = json.loads(fh.read())
            fh.close()
        self.valid_customer_no_metadata = convert_to_stripe_object(cust_test2)

        with open(
            f"{CFG.REPO_ROOT}/src/sub/tests/unit/fixtures/stripe_cust_test3.json"
        ) as fh:
            cust_test3 = json.loads(fh.read())
            fh.close()
        self.valid_customer3 = convert_to_stripe_object(cust_test3)

        with open(
            f"{CFG.REPO_ROOT}/src/sub/tests/unit/fixtures/stripe_deleted_cust.json"
        ) as fh:
            deleted_cust = json.loads(fh.read())
            fh.close()
        self.deleted_cust = convert_to_stripe_object(deleted_cust)

        with open(
            f"{CFG.REPO_ROOT}/src/sub/tests/unit/fixtures/stripe_prod_test1.json"
        ) as fh:
            prod_test1 = json.loads(fh.read())
            fh.close()
        self.product = convert_to_stripe_object(prod_test1)

        with open(
            f"{CFG.REPO_ROOT}/src/sub/tests/unit/fixtures/stripe_in_test1.json"
        ) as fh:
            invoice_test1 = json.loads(fh.read())
            fh.close()
        self.invoice = convert_to_stripe_object(invoice_test1)

        with open(
            f"{CFG.REPO_ROOT}/src/sub/tests/unit/fixtures/stripe_ch_test1.json"
        ) as fh:
            charge_test1 = json.loads(fh.read())
            fh.close()
        self.charge = convert_to_stripe_object(charge_test1)

        with open(
            f"{CFG.REPO_ROOT}/src/sub/tests/unit/fixtures/stripe_sub_test1.json"
        ) as fh:
            subscription_test1 = json.loads(fh.read())
            fh.close()
        self.subscription_test1 = convert_to_stripe_object(subscription_test1)

        with open(
            f"{CFG.REPO_ROOT}/src/sub/tests/unit/fixtures/stripe_sub_test3.json"
        ) as fh:
            subscription_test3 = json.loads(fh.read())
            fh.close()
        self.subscription_test3 = convert_to_stripe_object(subscription_test3)

        with open(
            f"{CFG.REPO_ROOT}/src/sub/tests/unit/fixtures/stripe_sub_cancelled.json"
        ) as fh:
            subscription_test_cancelled = json.loads(fh.read())
            fh.close()
        self.subscription_test_cancelled = convert_to_stripe_object(
            subscription_test_cancelled
        )

        with open(
            f"{CFG.REPO_ROOT}/src/sub/tests/unit/fixtures/stripe_sub_test_none.json"
        ) as fh:
            subscription_none = json.loads(fh.read())
            fh.close()
        self.subscription_none = subscription_none

        with open(
            f"{CFG.REPO_ROOT}/src/sub/tests/unit/fixtures/sns_message.json"
        ) as fh:
            sns_message_payload = json.loads(fh.read())
            fh.close()
        self.sns_message_payload = sns_message_payload

        with open(
            f"{CFG.REPO_ROOT}/src/sub/tests/unit/fixtures/stripe_subscriptions_no_data.json"
        ) as fh:
            subscription_no_data = json.loads(fh.read())
            fh.close()
        self.subscription_no_data = subscription_no_data

        with open(
            f"{CFG.REPO_ROOT}/src/sub/tests/unit/fixtures/subhub_valid_sub_test.json"
        ) as fh:
            valid_sub_test = json.loads(fh.read())
            fh.close()
        self.valid_sub_test = convert_to_stripe_object(valid_sub_test)

        with open(
            f"{CFG.REPO_ROOT}/src/sub/tests/unit/fixtures/valid_plan_response.json"
        ) as fh:
            valid_plan_response = json.loads(fh.read())
            fh.close()
        self.valid_plan_response = convert_to_stripe_object(valid_plan_response)

        with open(
            f"{CFG.REPO_ROOT}/src/sub/tests/unit/fixtures/subhub_account_user.json"
        ) as fh:
            subhub_user_account = json.loads(fh.read())
            fh.close()
        self.subhub_user_account = subhub_user_account

        with open(
            f"{CFG.REPO_ROOT}/src/sub/tests/unit/fixtures/subhub_return_data.json"
        ) as fh:
            subhub_return_data = json.loads(fh.read())
            fh.close()
        self.subhub_return_data = subhub_return_data

        self.false_existing_plan = None

        self.true_existing_plan = True

        valid_customer_patch = patch("sub.customer.existing_or_new_customer")
        deleted_customer_patch = patch("sub.customer.existing_or_new_customer")
        has_existing_plan_patch = patch("sub.payments.has_existing_plan")
        build_subscription_patch = patch("sub.shared.vendor.build_stripe_subscription")
        fetch_customer_patch = patch("sub.payments.fetch_customer")
        find_newest_subscription_patch = patch("sub.payments.find_newest_subscription")
        retrieve_stripe_subscriptions_patch = patch(
            "sub.payments.retrieve_stripe_subscriptions"
        )
        create_customer_patch = patch("sub.customer.create_customer")
        create_return_data_patch = patch("sub.payments.create_return_data")

        stripe_subscription_create_patch = patch("stripe.Subscription.create")
        stripe_customer_retrieve_patch = patch("stripe.Customer.retrieve")
        stripe_product_retrieve_patch = patch("stripe.Product.retrieve")
        stripe_cancel_subscription_patch = patch("stripe.Subscription.modify")
        stripe_delete_customer_patch = patch("stripe.Customer.delete")
        stripe_cancel_subscription_immediately_patch = patch(
            "stripe.Subscription.delete"
        )
        stripe_list_subscriptions_patch = patch("stripe.Subscription.list")
        stripe_modify_customer_patch = patch("stripe.Customer.modify")
        stripe_retrieve_invoice_patch = patch("stripe.Invoice.retrieve")
        stripe_retrieve_charge_patch = patch("stripe.Charge.retrieve")

        subhub_user_account_patch = patch("shared.db.SubHubAccount.get_user")
        subhub_deleted_user_save_patch = patch(
            "shared.db.SubHubDeletedAccount.save_user"
        )
        subhub_user_remove_patch = patch("shared.db.SubHubAccount.remove_from_db")

        sns_message_patch = patch("sub.payments.Message.route")
        subhub_delete_user_patch = patch("sub.payments.delete_user")
        add_user_to_deleted_users_record_patch = patch(
            "sub.payments.add_user_to_deleted_users_record"
        )
        subscription_status_patch = patch("sub.payments.subscription_status")
        vendor_modify_customer_patch = patch("sub.shared.vendor.modify_customer")

        self.addCleanup(valid_customer_patch.stop)
        self.addCleanup(deleted_customer_patch.stop)
        self.addCleanup(has_existing_plan_patch.stop)
        self.addCleanup(build_subscription_patch.stop)
        self.addCleanup(fetch_customer_patch.stop)
        self.addCleanup(find_newest_subscription_patch.stop)
        self.addCleanup(retrieve_stripe_subscriptions_patch.stop)
        self.addCleanup(create_customer_patch.stop)
        self.addCleanup(stripe_product_retrieve_patch.stop)
        self.addCleanup(stripe_subscription_create_patch.stop)
        self.addCleanup(stripe_customer_retrieve_patch.stop)
        self.addCleanup(stripe_cancel_subscription_patch.stop)
        self.addCleanup(subhub_user_account_patch.stop)
        self.addCleanup(stripe_cancel_subscription_immediately_patch.stop)
        self.addCleanup(sns_message_patch.stop)
        self.addCleanup(stripe_delete_customer_patch.stop)
        self.addCleanup(subhub_delete_user_patch.stop)
        self.addCleanup(add_user_to_deleted_users_record_patch.stop)
        self.addCleanup(subhub_deleted_user_save_patch.stop)
        self.addCleanup(subhub_user_remove_patch.stop)
        self.addCleanup(subscription_status_patch.stop)
        self.addCleanup(stripe_list_subscriptions_patch.stop)
        self.addCleanup(create_return_data_patch.stop)
        self.addCleanup(stripe_modify_customer_patch.stop)
        self.addCleanup(vendor_modify_customer_patch.stop)
        self.addCleanup(stripe_retrieve_invoice_patch.stop)
        self.addCleanup(stripe_retrieve_charge_patch.stop)

        self.mock_valid_customer = valid_customer_patch.start()
        self.mock_deleted_customer = deleted_customer_patch.start()
        self.mock_existing_plan = has_existing_plan_patch.start()
        self.mock_build_subscription = build_subscription_patch.start()
        self.mock_fetch_customer = fetch_customer_patch.start()
        self.mock_find_newest_subscription = find_newest_subscription_patch.start()
        self.mock_create_customer = create_customer_patch.start()
        self.mock_stripe_retrieve_product = stripe_product_retrieve_patch.start()
        self.mock_retrieve_stripe_subscriptions = (
            retrieve_stripe_subscriptions_patch.start()
        )
        self.mock_stripe_build_subscription = stripe_subscription_create_patch.start()
        self.mock_stripe_customer_retrieve = stripe_customer_retrieve_patch.start()
        self.mock_stripe_modify_subscription = stripe_cancel_subscription_patch.start()
        self.mock_subhub_user_account = subhub_user_account_patch.start()
        self.mock_stripe_cancel_sub_now = (
            stripe_cancel_subscription_immediately_patch.start()
        )
        self.mock_sns_message_route = sns_message_patch.start()
        self.mock_stripe_delete_customer = stripe_delete_customer_patch.start()
        self.mock_subhub_delete_user = subhub_delete_user_patch.start()
        self.mock_add_user_to_deleted_users_record = (
            add_user_to_deleted_users_record_patch.start()
        )
        self.mock_subhub_deleted_user_save = subhub_deleted_user_save_patch.start()
        self.mock_subhub_user_remove = subhub_user_remove_patch.start()
        self.mock_subscription_status = subscription_status_patch.start()
        self.mock_stripe_list_subscriptions = stripe_list_subscriptions_patch.start()
        self.mock_create_return_data = create_return_data_patch.start()
        self.mock_stripe_modify_customer = stripe_modify_customer_patch.start()
        self.mock_vendor_modify_customer = vendor_modify_customer_patch.start()
        self.mock_stripe_retrieve_invoice = stripe_retrieve_invoice_patch.start()
        self.mock_stripe_retrieve_charge = stripe_retrieve_charge_patch.start()

    def test_valid_subscription(self):
        self.mock_valid_customer.return_value = self.valid_customer
        self.mock_existing_plan.return_value = self.false_existing_plan
        self.mock_build_subscription.return_value = self.subscription_test1
        self.mock_fetch_customer.return_value = self.valid_customer
        self.mock_create_customer.return_value = self.valid_customer
        self.mock_stripe_retrieve_product.return_value = self.product
        self.mock_stripe_customer_retrieve.return_value = self.valid_customer
        created_sub = subscribe_to_plan(
            self.valid_sub_test["user_id"], self.valid_sub_test
        )
        assert created_sub[1] == 201

    def test_invalid_subscription(self):
        self.mock_deleted_customer.return_value = self.deleted_cust
        self.mock_existing_plan.return_value = None
        self.mock_build_subscription.return_value = self.subscription_test1
        self.mock_fetch_customer.return_value = self.deleted_cust
        self.mock_create_customer.return_value = self.deleted_cust
        self.mock_stripe_retrieve_product.return_value = self.product
        self.mock_stripe_customer_retrieve.return_value = self.deleted_cust

        created_sub = subscribe_to_plan(
            self.valid_sub_test["user_id"], self.valid_sub_test
        )
        assert created_sub[1] == 400

    def test_existing_plan_subscription(self):
        self.mock_valid_customer.return_value = self.valid_customer
        self.mock_existing_plan.return_value = self.true_existing_plan
        created_sub = subscribe_to_plan(
            self.valid_sub_test["user_id"], self.valid_sub_test
        )
        assert created_sub[1] == 409

    def test_no_newest_subscription(self):
        subs = find_newest_subscription(None)
        assert subs is None

    def test_newest_sub_continue(self):
        subs = find_newest_subscription(self.subscription_no_data)
        logger.info("find subs", subs=subs, data=subs["data"])
        for sub in subs["data"]:
            assert sub is None

    def test_cancel_subscription(self):
        self.mock_fetch_customer.return_value = self.valid_customer3
        self.mock_retrieve_stripe_subscriptions.return_value = [self.subscription_test3]
        self.mock_stripe_modify_subscription.return_value = self.subscription_test3
        cancelled = cancel_subscription("cus_test3", "sub_test3")
        assert cancelled[1] == 201

    def test_delete_customer(self):
        first_account_mock = MagicMock()
        first_account_mock.return_value.user_id = "user123"
        first_account_mock.return_value.cust_id = "cus_test1"
        first_account_mock.return_value.origin_system = "fake_origin1"
        self.mock_subhub_user_account.side_effect = [first_account_mock, None]
        self.mock_stripe_retrieve_product.return_value = self.product
        self.mock_stripe_customer_retrieve.return_value = self.valid_customer
        self.mock_stripe_cancel_sub_now.return_value = self.subscription_test_cancelled
        self.mock_sns_message_route.return_value = self.sns_message_payload
        self.mock_stripe_delete_customer.return_value = self.deleted_cust
        self.mock_subhub_delete_user.return_value = True
        deleted_customer = delete_customer("user123")
        assert deleted_customer[1] == 200

    def test_delete_customer_none(self):
        self.mock_subhub_user_account.return_value = None
        deleted_customer = delete_customer("user123")
        assert deleted_customer[1] == 404

    def test_delete_customer_fail(self):
        first_account_mock = MagicMock()
        first_account_mock.return_value.user_id = "user123"
        first_account_mock.return_value.cust_id = "cus_test1"
        first_account_mock.return_value.origin_system = "fake_origin1"
        self.mock_subhub_user_account.side_effect = [first_account_mock, None]
        self.mock_stripe_retrieve_product.return_value = self.product
        self.mock_stripe_customer_retrieve.return_value = self.valid_customer
        self.mock_stripe_cancel_sub_now.return_value = self.subscription_test_cancelled
        self.mock_sns_message_route.return_value = self.sns_message_payload
        self.mock_stripe_delete_customer.return_value = None
        # self.mock_subhub_delete_user.return_value = True
        deleted_customer = delete_customer("user123")
        assert deleted_customer[1] == 400

    def test_delete_user(self):
        self.mock_add_user_to_deleted_users_record.return_value = "user"
        self.mock_subhub_deleted_user_save.return_value = True
        self.mock_subhub_user_remove.return_value = True
        deleted_user = delete_user(
            user_id="user123",
            cust_id="cus_test1",
            origin_system="fake_origin1",
            subscription_info=[{"sub": "123"}],
        )
        assert deleted_user is True

    def test_delete_user_fail(self):
        self.mock_add_user_to_deleted_users_record.return_value = "user"
        self.mock_subhub_deleted_user_save.return_value = False
        deleted_user = delete_user(
            user_id="user123",
            cust_id="cus_test1",
            origin_system="fake_origin1",
            subscription_info=[{"sub": "123"}],
        )
        assert deleted_user is False

    def test_support_status(self):
        self.mock_subscription_status.return_value = (
            dict(message="subscription successful"),
            200,
        )
        support_status_test = support_status("user123")
        assert support_status_test[1] == 200

    def test_subscription_status(self):
        self.mock_subhub_user_account.return_value.user_id = "user123"
        self.mock_subhub_user_account.return_value.cust_id = "cus_test1"
        self.mock_subhub_user_account.return_value.origin_system = "fake_origin1"
        self.mock_stripe_list_subscriptions.return_value = [self.subscription_test1]
        self.mock_create_return_data.return_data = self.subhub_return_data
        sub_status = subscription_status("user123")
        assert sub_status[1] == 200

    def test_subscription_status_no_cust(self):
        self.mock_subhub_user_account.return_value = None
        sub_status = subscription_status("user123")
        assert sub_status[1] == 404

    def test_subscription_status_no_subscriptions(self):
        self.mock_subhub_user_account.return_value.user_id = "user123"
        self.mock_subhub_user_account.return_value.cust_id = "cus_test1"
        self.mock_subhub_user_account.return_value.origin_system = "fake_origin1"
        self.mock_stripe_list_subscriptions.return_value = []
        sub_status = subscription_status("user123")
        assert sub_status[1] == 403

    def test_update_payment_method_metadata(self):
        self.mock_fetch_customer.return_value = self.valid_customer
        self.mock_stripe_modify_customer.return_value = self.valid_customer
        updated_payment_method = update_payment_method(
            "user123", {"pmt_token": "tok_mastercard"}
        )
        assert updated_payment_method[1] == 201

    def test_update_payment_method_mismatch(self):
        self.mock_fetch_customer.return_value = self.valid_customer_no_metadata
        updated_payment_method = update_payment_method(
            "user123", {"pmt_token": "tok_mastercard"}
        )
        assert updated_payment_method[1] == 400

    def test_update_payment_method_no_cust(self):
        self.mock_fetch_customer.return_value = None
        updated_payment_method = update_payment_method(
            "user123", {"pmt_token": "tok_visa"}
        )
        assert updated_payment_method[1] == 404

    def test_customer_update_none(self):
        self.mock_fetch_customer.return_value = None
        customer_updated = customer_update("user123")
        assert customer_updated[1] == 404

    def test_customer_update_mismatch(self):
        self.mock_fetch_customer.return_value = self.valid_customer
        customer_updated = customer_update("user321")
        logger.info("customer mismatch", customer_updated=customer_updated)
        assert customer_updated[1] == 400

    def test_create_update_data_intents(self):
        self.mock_stripe_retrieve_invoice.return_value = self.invoice
        self.mock_stripe_retrieve_charge.return_value = self.charge
        self.mock_stripe_retrieve_product.return_value = self.product
        created_update_data = create_update_data(self.valid_customer3)

        logger.info("created update data", created_update_data=created_update_data)
        assert created_update_data["payment_type"] == "credit"
