# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import json
from unittest import TestCase
from mock import patch

from stripe.util import convert_to_stripe_object
from stripe.error import InvalidRequestError

from sub.customer import (
    create_customer,
    search_customers,
    existing_or_new_customer,
    fetch_customer,
    existing_payment_source,
    subscribe_customer,
    has_existing_plan,
    _validate_origin_system,
)
from sub.shared.db import SubHubAccountModel
from sub.shared.cfg import CFG
from sub.shared.exceptions import IntermittentError, ServerError


class CustomerTest(TestCase):
    def setUp(self) -> None:

        with open("src/sub/tests/unit/fixtures/stripe_cust_test1.json") as fh:
            cust_test1 = json.loads(fh.read())
        self.customer1 = convert_to_stripe_object(cust_test1)

        with open("src/sub/tests/unit/fixtures/stripe_cust_test2.json") as fh:
            cust_test2 = json.loads(fh.read())
        self.customer2 = convert_to_stripe_object(cust_test2)

        with open("src/sub/tests/unit/fixtures/stripe_cust_test4_no_subs.json") as fh:
            cust_test1_no_subs = json.loads(fh.read())
        self.customer_no_subs = convert_to_stripe_object(cust_test1_no_subs)

        with open(
            "src/sub/tests/unit/fixtures/stripe_cust_test5_no_sources.json"
        ) as fh:
            cust_test1_no_sources = json.loads(fh.read())
        self.customer_no_sources = convert_to_stripe_object(cust_test1_no_sources)

        with open("src/sub/tests/unit/fixtures/stripe_deleted_cust.json") as fh:
            deleted_cust = json.loads(fh.read())
        self.deleted_customer = convert_to_stripe_object(deleted_cust)

        with open("src/sub/tests/unit/fixtures/stripe_cust_list.json") as fh:
            cust_list = json.loads(fh.read())
        self.empty_customer_list = convert_to_stripe_object(cust_list)

        cust_list["data"].append(cust_test2)
        cust_list["data"].append(cust_test1)
        self.customer_list = convert_to_stripe_object(cust_list)

        with open("src/sub/tests/unit/fixtures/stripe_sub_test1.json") as fh:
            sub_test1 = json.loads(fh.read())
        self.subscription1 = convert_to_stripe_object(sub_test1)

        self.subhub_user = SubHubAccountModel(
            user_id="user_1",
            cust_id="cust_1",
            origin_system="fxa",
            customer_status="active",
        )

        list_stripe_customer_patcher = patch("stripe.Customer.list")
        retrieve_stripe_customer_patcher = patch("stripe.Customer.retrieve")
        modify_stripe_customer_patcher = patch("stripe.Customer.modify")
        create_stripe_customer_patcher = patch("stripe.Customer.create")
        delete_stripe_customer_patcher = patch("stripe.Customer.delete")
        create_stripe_subscription_patcher = patch("stripe.Subscription.create")
        subhub_account_patcher = patch("shared.db.SubHubAccount", autospec=True)

        self.addCleanup(list_stripe_customer_patcher.stop)
        self.addCleanup(retrieve_stripe_customer_patcher.stop)
        self.addCleanup(modify_stripe_customer_patcher.stop)
        self.addCleanup(create_stripe_customer_patcher.stop)
        self.addCleanup(delete_stripe_customer_patcher.stop)
        self.addCleanup(create_stripe_subscription_patcher.stop)
        self.addCleanup(subhub_account_patcher.stop)

        self.list_stripe_customer_mock = list_stripe_customer_patcher.start()
        self.retrieve_stripe_customer_mock = retrieve_stripe_customer_patcher.start()
        self.modify_stripe_customer_mock = modify_stripe_customer_patcher.start()
        self.create_stripe_customer_mock = create_stripe_customer_patcher.start()
        self.delete_stripe_customer_mock = delete_stripe_customer_patcher.start()
        self.create_stripe_subscription_mock = (
            create_stripe_subscription_patcher.start()
        )
        self.subhub_account_mock = subhub_account_patcher.start()

    def test_create_customer_brand_new(self):
        subhub_account = self.subhub_account_mock("table", "region")
        subhub_account.get_user.return_value = None
        subhub_account.new_user.return_value = self.subhub_user
        subhub_account.save_user.return_value = self.subhub_user

        self.list_stripe_customer_mock.return_value = self.empty_customer_list
        self.create_stripe_customer_mock.return_value = self.customer_no_subs

        customer = create_customer(
            subhub_account,
            "user123",
            "test@example.com",
            "token",
            CFG.ALLOWED_ORIGIN_SYSTEMS[0],
            "test name",
        )

        assert customer == self.customer_no_subs

    def test_create_customer_not_saved(self):
        subhub_account = self.subhub_account_mock("table", "region")
        subhub_account.get_user.return_value = None
        subhub_account.new_user.return_value = self.subhub_user
        subhub_account.save_user.return_value = False

        self.list_stripe_customer_mock.return_value = self.empty_customer_list
        self.create_stripe_customer_mock.return_value = self.customer_no_subs
        self.delete_stripe_customer_mock.return_value = self.deleted_customer

        with self.assertRaises(IntermittentError):
            create_customer(
                subhub_account,
                "user123",
                "test@example.com",
                "token",
                CFG.ALLOWED_ORIGIN_SYSTEMS[0],
                "test name",
            )

    def test_create_customer_modify_source(self):
        subhub_account = self.subhub_account_mock("table", "region")
        subhub_account.get_user.return_value = None

        self.list_stripe_customer_mock.return_value = self.customer_list
        self.modify_stripe_customer_mock.return_value = self.customer_no_subs

        customer = create_customer(
            subhub_account,
            "user123",
            "test@example.com",
            "token",
            CFG.ALLOWED_ORIGIN_SYSTEMS[0],
            "test name",
        )

        assert customer == self.customer_no_subs

    def test_search_customers_match(self):
        self.list_stripe_customer_mock.return_value = self.customer_list
        customer = search_customers("test@example.com", "user123")
        assert customer is not None

    def test_search_customers_bad_match(self):
        self.list_stripe_customer_mock.return_value = self.customer_list

        with self.assertRaises(ServerError):
            search_customers("test@example.com", "user1")

    def test_search_customers_no_match(self):
        self.list_stripe_customer_mock.return_value = self.empty_customer_list
        customer = search_customers("test@example.com", "user_1")
        assert customer is None

    def test_existing_or_new_customer_return_existing(self):
        self.retrieve_stripe_customer_mock.return_value = self.customer1
        subhub_account = self.subhub_account_mock("table", "region")
        subhub_account.get_user.return_value = self.subhub_user

        customer = existing_or_new_customer(
            subhub_account,
            "user123",
            "test@example.com",
            "token",
            CFG.ALLOWED_ORIGIN_SYSTEMS[0],
            "test name",
        )

        assert customer == self.customer1

    def test_existing_or_new_customer_return_new(self):
        subhub_account = self.subhub_account_mock("table", "region")
        subhub_account.get_user.return_value = None
        self.list_stripe_customer_mock.return_value = self.empty_customer_list
        self.create_stripe_customer_mock.return_value = self.customer_no_subs

        customer = existing_or_new_customer(
            subhub_account,
            "user123",
            "test@example.com",
            "token",
            CFG.ALLOWED_ORIGIN_SYSTEMS[0],
            "test name",
        )

        assert customer == self.customer_no_subs

    def test_fetch_customer_success(self):
        self.retrieve_stripe_customer_mock.return_value = self.customer1
        subhub_account = self.subhub_account_mock("table", "region")
        subhub_account.get_user.return_value = self.subhub_user

        customer = fetch_customer(subhub_account, "user_1")

        assert customer == self.customer1

    def test_fetch_customer_failure(self):
        subhub_account = self.subhub_account_mock("table", "region")
        subhub_account.get_user.return_value = None

        customer = fetch_customer(subhub_account, "user_1")
        assert customer is None

    def test_existing_payment_source_no_change(self):
        customer = existing_payment_source(self.customer1, "token")
        assert customer == self.customer1

    def test_existing_payment_source_add_source(self):
        self.modify_stripe_customer_mock.return_value = self.customer1
        customer = existing_payment_source(self.customer_no_sources, "token")
        assert customer == self.customer1

    def test_existing_payment_source_deleted_customer(self):
        customer = existing_payment_source(self.deleted_customer, "token")
        assert customer == self.deleted_customer

    def test_subscribe_customer(self):
        self.create_stripe_subscription_mock.return_value = self.subscription1
        sub = subscribe_customer(self.customer1, "plan_test1")
        assert sub == self.subscription1

    def test_has_existing_plan_found(self):
        has_plan = has_existing_plan(self.customer1, "plan_test1")
        assert has_plan

    def test_has_existing_plan_not_found(self):
        has_plan = has_existing_plan(self.customer1, "plan")
        assert has_plan == False

    def test_has_existing_plan_no_subs(self):
        has_plan = has_existing_plan(self.customer_no_subs, "plan_test1")
        assert has_plan == False

    def test_validate_origin_system_no_error(self):
        for origin_system in CFG.ALLOWED_ORIGIN_SYSTEMS:
            _validate_origin_system(origin_system)
        assert True

    def test_validate_origin_system_invalid(self):
        with self.assertRaises(InvalidRequestError):
            _validate_origin_system("bad_origin_system")
