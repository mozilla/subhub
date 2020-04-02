# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import time
import json
from unittest import TestCase
from mock import patch

from stripe.util import convert_to_stripe_object
from stripe.error import InvalidRequestError

from hub.vendor.customer import (
    StripeCustomerCreated,
    StripeCustomerDeleted,
    StripeCustomerSourceExpiring,
    StripeCustomerSubscriptionUpdated,
    StripeCustomerSubscriptionDeleted,
    StripeCustomerUpdated,
)
from hub.shared.exceptions import ClientError
from hub.shared.db import SubHubDeletedAccountModel

from shared.log import get_logger

logger = get_logger()


class StripeCustomerCreatedTest(TestCase):
    def setUp(self) -> None:
        fixture_dir = "src/hub/tests/unit/fixtures/"
        with open(f"{fixture_dir}stripe_cust_created_event.json") as fh:
            self.customer_created_event = json.loads(fh.read())

        with open(f"{fixture_dir}stripe_cust_created_event_missing_name.json") as fh:
            self.customer_created_event_missing_name = json.loads(fh.read())

        run_pipeline_patcher = patch("hub.routes.pipeline.RoutesPipeline.run")
        self.addCleanup(run_pipeline_patcher.stop)
        self.mock_run_pipeline = run_pipeline_patcher.start()

    def test_run(self):
        self.mock_run_pipeline.return_value = None
        did_run = StripeCustomerCreated(self.customer_created_event).run()
        assert did_run

    def test_create_payload(self):
        expected_payload = {
            "event_id": "evt_00000000000000",
            "event_type": "customer.created",
            "email": "user123@tester.com",
            "customer_id": "cus_00000000000000",
            "name": "Jon Tester",
            "user_id": "user123",
        }
        actual_payload = StripeCustomerCreated(
            self.customer_created_event
        ).create_payload()

        assert actual_payload == expected_payload

    def test_create_payload_missing_name(self):
        expected_payload = {
            "event_id": "evt_00000000000000",
            "event_type": "customer.created",
            "email": "user123@tester.com",
            "customer_id": "cus_00000000000000",
            "name": "",
            "user_id": "user123",
        }
        actual_payload = StripeCustomerCreated(
            self.customer_created_event_missing_name
        ).create_payload()

        assert actual_payload == expected_payload


class StripeCustomerUpdatedTest(TestCase):
    def setUp(self) -> None:
        fixture_dir = "src/hub/tests/unit/fixtures/"
        with open(f"{fixture_dir}stripe_cust_updated_event.json") as fh:
            self.customer_updated_event = json.loads(fh.read())

        with open(f"{fixture_dir}stripe_cust_updated_event_missing_name.json") as fh:
            self.customer_updated_event_missing_name = json.loads(fh.read())

        run_pipeline_patcher = patch("hub.routes.pipeline.RoutesPipeline.run")
        self.addCleanup(run_pipeline_patcher.stop)
        self.mock_run_pipeline = run_pipeline_patcher.start()

    def test_run(self):
        self.mock_run_pipeline.return_value = None
        did_run = StripeCustomerCreated(self.customer_updated_event).run()
        assert did_run

    def test_create_payload(self):
        expected_payload = {
            "event_id": "evt_00000000000000",
            "event_type": "customer.updated",
            "email": "user123@tester.com",
            "customer_id": "cus_00000000000000",
            "name": "Jon Tester",
            "user_id": "user123",
            "deleted": "true",
            "subscriptions": [{"id": "sub_00000000000000"}],
        }
        actual_payload = StripeCustomerUpdated(
            self.customer_updated_event
        ).parse_payload()
        print(f"payload subs {expected_payload['subscriptions']}")

        assert actual_payload == expected_payload

    def test_create_payload_missing_name(self):
        expected_payload = {
            "event_id": "evt_00000000000000",
            "event_type": "customer.updated",
            "email": "user123@tester.com",
            "customer_id": "cus_00000000000000",
            "name": "",
            "user_id": "user123",
            "deleted": True,
            "subscriptions": [],
        }
        actual_payload = StripeCustomerUpdated(
            self.customer_updated_event_missing_name
        ).parse_payload()

        assert actual_payload == expected_payload


class StripeCustomerDeletedTest(TestCase):
    def setUp(self) -> None:
        self.user_id = "user123"
        self.cust_id = "cus_123"
        self.subscription_item = dict(
            current_period_end=1574519675,
            current_period_start=1571841275,
            nickname="Guardian VPN",
            plan_amount=499,
            productId="prod_FvnsFHIfezy3ZI",
            subscription_id="sub_G2qciC6nDf1Hz1",
        )
        self.origin_system = "fxa"

        self.deleted_user = SubHubDeletedAccountModel(
            user_id=self.user_id,
            cust_id=self.cust_id,
            subscription_info=[self.subscription_item],
            origin_system=self.origin_system,
            customer_status="deleted",
        )

        self.deleted_user_no_subscriptions = SubHubDeletedAccountModel(
            user_id=self.user_id,
            cust_id=self.cust_id,
            subscription_info=list(),
            origin_system=self.origin_system,
            customer_status="deleted",
        )
        fixture_dir = "src/hub/tests/unit/fixtures/"
        with open(f"{fixture_dir}stripe_customer_deleted_event.json") as fh:
            self.customer_deleted_event = json.loads(fh.read())

        with open(f"{fixture_dir}stripe_customer_deleted_event_no_metadata.json") as fh:
            self.customer_deleted_event_no_meta = json.loads(fh.read())

        get_deleted_user_patcher = patch("flask.g.subhub_deleted_users.get_user")
        run_pipeline_patcher = patch("hub.routes.pipeline.RoutesPipeline.run")

        self.addCleanup(get_deleted_user_patcher.stop)
        self.addCleanup(run_pipeline_patcher.stop)

        self.mock_get_deleted_user = get_deleted_user_patcher.start()
        self.mock_run_pipeline = run_pipeline_patcher.start()

    def test_run(self):
        self.mock_get_deleted_user.return_value = self.deleted_user
        self.mock_run_pipeline.return_value = None
        did_run = StripeCustomerDeleted(self.customer_deleted_event).run()
        assert did_run

    def test_get_deleted_user(self):
        self.mock_get_deleted_user.return_value = self.deleted_user
        user = StripeCustomerDeleted(self.customer_deleted_event).get_deleted_user()
        assert user == self.deleted_user

    def test_get_deleted_user_no_meta(self):
        self.mock_get_deleted_user.return_value = self.deleted_user
        with self.assertRaises(
            ClientError, msg="subhub_deleted_user could not be fetched - missing keys"
        ):
            StripeCustomerDeleted(
                self.customer_deleted_event_no_meta
            ).get_deleted_user()

    def test_get_deleted_user_not_found(self):
        self.mock_get_deleted_user.return_value = None
        with self.assertRaises(
            ClientError,
            msg=f"subhub_deleted_user is None for customer {self.cust_id} and user {self.user_id}",
        ):
            StripeCustomerDeleted(self.customer_deleted_event).get_deleted_user()

    def test_create_payload(self):
        expected_payload = dict(
            event_id="evt_00000000000000",
            event_type="customer.deleted",
            created=1557511290,
            customer_id=self.cust_id,
            plan_amount=499,
            nickname=[self.subscription_item.get("nickname")],
            subscription_id=f"{self.subscription_item.get('subscription_id')}",
            current_period_end=self.subscription_item.get("current_period_end"),
            current_period_start=self.subscription_item.get("current_period_start"),
        )

        payload = StripeCustomerDeleted(self.customer_deleted_event).create_payload(
            self.deleted_user
        )

        self.assertEqual(payload.keys(), expected_payload.keys())
        self.assertEqual(payload, expected_payload)

    def test_create_payload_no_subscription_data(self):
        expected_payload = dict(
            event_id="evt_00000000000000",
            event_type="customer.deleted",
            created=1557511290,
            customer_id=self.cust_id,
            plan_amount=0,
            nickname=[],
            subscription_id="",
            current_period_end=None,
            current_period_start=None,
        )

        payload = StripeCustomerDeleted(self.customer_deleted_event).create_payload(
            self.deleted_user_no_subscriptions
        )

        self.assertEqual(payload.keys(), expected_payload.keys())
        self.assertEqual(payload, expected_payload)


class StripeCustomerSourceExpiringTest(TestCase):
    def setUp(self) -> None:
        fixture_dir = "src/hub/tests/unit/fixtures/"
        with open(f"{fixture_dir}stripe_cust_test1.json") as fh:
            cust_test1 = json.loads(fh.read())
        self.customer = convert_to_stripe_object(cust_test1)

        with open(f"{fixture_dir}stripe_sub_test1.json") as fh:
            self.subscription = json.loads(fh.read())

        with open(f"{fixture_dir}stripe_sub_test2.json") as fh:
            self.subscription2 = json.loads(fh.read())

        with open(f"{fixture_dir}stripe_plan_test1.json") as fh:
            self.plan = json.loads(fh.read())

        with open(f"{fixture_dir}stripe_prod_test1.json") as fh:
            prod_test1 = json.loads(fh.read())
        self.product = convert_to_stripe_object(prod_test1)

        with open(f"{fixture_dir}stripe_source_expiring_event.json") as fh:
            self.source_expiring_event = json.loads(fh.read())

        customer_patcher = patch("stripe.Customer.retrieve")
        product_patcher = patch("stripe.Product.retrieve")
        run_pipeline_patcher = patch("hub.routes.pipeline.RoutesPipeline.run")

        self.addCleanup(customer_patcher.stop)
        self.addCleanup(product_patcher.stop)
        self.addCleanup(run_pipeline_patcher.stop)

        self.mock_customer = customer_patcher.start()
        self.mock_product = product_patcher.start()
        self.mock_run_pipeline = run_pipeline_patcher.start()

    def test_run(self):
        self.subscription["plan"] = self.plan
        self.customer.subscriptions["data"].append(self.subscription)
        self.mock_customer.return_value = self.customer
        self.mock_product.return_value = self.product
        self.mock_run_pipeline = None

        did_run = StripeCustomerSourceExpiring(self.source_expiring_event).run()

        assert did_run

    def test_run_no_subscriptions(self):
        self.mock_customer.return_value = self.customer
        self.mock_run_pipeline = None
        did_run = StripeCustomerSourceExpiring(self.source_expiring_event).run()
        assert did_run

    def test_run_customer_not_found(self):
        self.mock_customer.side_effect = InvalidRequestError(
            message="message", param="param"
        )
        self.mock_run_pipeline = None
        with self.assertRaises(InvalidRequestError):
            StripeCustomerSourceExpiring(self.source_expiring_event).run()

    def test_create_payload(self):
        self.subscription["plan"] = self.plan
        self.customer.subscriptions["data"].append(self.subscription2)
        self.customer.subscriptions["data"].append(self.subscription)
        self.mock_product.return_value = self.product

        expected_payload = dict(
            event_id="evt_00000000000000",
            event_type="customer.source.expiring",
            email="test@example.com",
            nickname="Project Guardian",
            customer_id="cus_00000000000000",
            last4="4242",
            brand="Visa",
            exp_month=5,
            exp_year=2019,
        )

        payload = StripeCustomerSourceExpiring(
            self.source_expiring_event
        ).create_payload(self.customer)
        assert payload == expected_payload

    def test_create_payload_no_subscriptions(self):
        self.mock_product.return_value = self.product

        expected_payload = dict(
            event_id="evt_00000000000000",
            event_type="customer.source.expiring",
            email="test@example.com",
            nickname="",
            customer_id="cus_00000000000000",
            last4="4242",
            brand="Visa",
            exp_month=5,
            exp_year=2019,
        )
        payload = StripeCustomerSourceExpiring(
            self.source_expiring_event
        ).create_payload(self.customer)
        assert payload == expected_payload


class StripeCustomerSubscriptionDeletedTest(TestCase):
    def setUp(self) -> None:
        fixture_dir = "src/hub/tests/unit/fixtures/"
        with open(f"{fixture_dir}stripe_cust_test1.json") as fh:
            cust_test1 = json.loads(fh.read())
        self.customer = convert_to_stripe_object(cust_test1)

        with open(f"{fixture_dir}stripe_cust_test2.json") as fh:
            cust_test2 = json.loads(fh.read())
        self.customer_active_sub = convert_to_stripe_object(cust_test2)

        with open(f"{fixture_dir}stripe_cust_no_metadata.json") as fh:
            cust_no_metadata = json.loads(fh.read())
        self.customer_missing_user = convert_to_stripe_object(cust_no_metadata)

        with open(f"{fixture_dir}stripe_cust_test1_deleted.json") as fh:
            cust_test1_deleted = json.loads(fh.read())
        self.deleted_customer = convert_to_stripe_object(cust_test1_deleted)

        with open(f"{fixture_dir}stripe_sub_deleted_event.json") as fh:
            self.subscription_deleted_event = json.loads(fh.read())

        with open(f"{fixture_dir}stripe_sub_test3.json") as fh:
            self.sub_to_delete = json.loads(fh.read())

        customer_patcher = patch("stripe.Customer.retrieve")
        delete_customer_patcher = patch("stripe.Customer.delete")
        run_pipeline_patcher = patch("hub.routes.pipeline.RoutesPipeline.run")

        self.addCleanup(customer_patcher.stop)
        self.addCleanup(run_pipeline_patcher.stop)
        self.addCleanup(delete_customer_patcher.stop)

        self.mock_customer = customer_patcher.start()
        self.mock_run_pipeline = run_pipeline_patcher.start()
        self.mock_delete_customer = delete_customer_patcher.start()

    def test_run(self):
        self.mock_customer.return_value = self.customer
        self.mock_run_pipeline.return_value = None

        did_run = StripeCustomerSubscriptionDeleted(
            self.subscription_deleted_event
        ).run()

        assert did_run

    def test_check_for_deleted_user(self):
        self.mock_delete_customer.return_value = self.deleted_customer
        to_delete_cus = StripeCustomerSubscriptionDeleted(
            self.subscription_deleted_event
        )
        deleted_cus = to_delete_cus.delete_customer(self.mock_delete_customer)
        assert deleted_cus.get("deleted") is True

    def test_add_user_to_deleted_users_record(self):
        deleted_user = StripeCustomerSubscriptionDeleted(
            self.subscription_deleted_event
        )
        add_deleted_user = deleted_user.add_user_to_deleted_users_record(
            user_id="test1",
            cust_id="cust_1",
            origin_system="origin1",
            subscription_info=[
                {
                    "nickname": "test sub 1",
                    "plan_amount": 100,
                    "productId": "prod_tes1",
                    "current_period_start": 1234567,
                    "current_period_end": 1234567,
                    "subscription_id": "sub_test1",
                }
            ],
        )
        assert add_deleted_user

    def test_update_deleted_user(self):
        deleted_user = StripeCustomerSubscriptionDeleted(
            self.subscription_deleted_event
        )
        deleted_user.add_user_to_deleted_users_record(
            user_id="test1",
            cust_id="cust_1",
            origin_system="origin1",
            subscription_info=[
                {
                    "nickname": "test sub 1",
                    "plan_amount": 100,
                    "productId": "prod_tes1",
                    "current_period_start": 1234567,
                    "current_period_end": 1234567,
                    "subscription_id": "sub_test1",
                }
            ],
        )
        updated_user = deleted_user.update_deleted_user(
            "test1",
            "cust_1",
            [
                {
                    "nickname": "test sub 2",
                    "plan_amount": 100,
                    "productId": "prod_tes2",
                    "current_period_start": 1234567,
                    "current_period_end": 1234567,
                    "subscription_id": "sub_test2",
                }
            ],
        )
        logger.info("update deleted user", updated_user=updated_user)
        assert len(updated_user) == 2

    def test_get_origin_system(self):
        deleted_user = StripeCustomerSubscriptionDeleted(
            self.subscription_deleted_event
        )
        origin_test = deleted_user.get_origin_system(self.customer)
        assert origin_test == "unknown"

    def test_get_user_id(self):
        deleted_user = StripeCustomerSubscriptionDeleted(
            self.subscription_deleted_event
        )
        user_id = deleted_user.get_user_id(self.customer)
        assert user_id == "user123"

    def test_delete_customer(self):
        self.mock_delete_customer.return_value = self.deleted_customer
        deleted_user = StripeCustomerSubscriptionDeleted(
            self.subscription_deleted_event
        )
        deleted_cust = deleted_user.delete_customer("cust_test1")
        assert deleted_cust.get("id") == "cust_test1"
        assert deleted_cust.get("deleted") is True

    def test_get_customer(self):
        self.mock_customer.return_value = self.customer
        logger.info("get customer", cus=self.customer, cus_id=self.customer.get("id"))
        delete_cus = StripeCustomerSubscriptionDeleted(self.subscription_deleted_event)
        get_customer = delete_cus.get_customer(self.customer.get("id"))
        assert get_customer.id == "cus_test1"

    def test_check_all_subscriptions(self):
        self.mock_customer.return_value = self.customer_active_sub
        delete_cus = StripeCustomerSubscriptionDeleted(self.subscription_deleted_event)
        check_all = delete_cus.check_all_subscriptions(
            customer=self.customer_active_sub
        )
        assert check_all is True

    def test_check_mark_delete(self):
        self.mock_customer.return_value = self.customer_active_sub
        delete_cus = StripeCustomerSubscriptionDeleted(self.subscription_deleted_event)
        check_mark_deleted = delete_cus.check_mark_delete(
            customer=self.customer_active_sub
        )
        assert check_mark_deleted is True

    def test_get_subscription_info(self):
        self.mock_customer.return_value = self.customer_active_sub
        delete_cus = StripeCustomerSubscriptionDeleted(self.subscription_deleted_event)
        logger.info("get sub", subs=self.customer_active_sub.get("subscriptions"))
        logger.info("sub to delete", to_delete=self.sub_to_delete)
        check_sub_info = delete_cus.get_subscription_info(
            subscriptions=self.customer_active_sub.get("subscriptions"),
            current_sub=self.sub_to_delete,
        )
        assert check_sub_info[0].get("nickname") == "test plan"


class StripeCustomerSubscriptionUpdatedTest(TestCase):
    def setUp(self) -> None:
        fixture_dir = "src/hub/tests/unit/fixtures/"
        with open(f"{fixture_dir}stripe_cust_test1.json") as fh:
            cust_test1 = json.loads(fh.read())
        self.customer = convert_to_stripe_object(cust_test1)

        with open(f"{fixture_dir}stripe_cust_no_metadata.json") as fh:
            cust_no_metadata = json.loads(fh.read())
        self.customer_missing_user = convert_to_stripe_object(cust_no_metadata)

        with open(f"{fixture_dir}stripe_cust_test1_deleted.json") as fh:
            cust_test1_deleted = json.loads(fh.read())
        self.deleted_customer = convert_to_stripe_object(cust_test1_deleted)

        with open(f"{fixture_dir}stripe_prod_test1.json") as fh:
            prod_test1 = json.loads(fh.read())
        self.product = convert_to_stripe_object(prod_test1)

        with open(f"{fixture_dir}stripe_prod_bad_test1.json") as fh:
            bad_prod_test1 = json.loads(fh.read())
        self.bad_product = convert_to_stripe_object(bad_prod_test1)

        with open(f"{fixture_dir}stripe_in_test1.json") as fh:
            invoice_test1 = json.loads(fh.read())
        self.invoice = convert_to_stripe_object(invoice_test1)

        with open(f"{fixture_dir}stripe_in_test2.json") as fh:
            invoice_test2 = json.loads(fh.read())
        self.incomplete_invoice = convert_to_stripe_object(invoice_test2)

        with open(f"{fixture_dir}stripe_ch_test1.json") as fh:
            charge_test1 = json.loads(fh.read())
        self.charge = convert_to_stripe_object(charge_test1)

        with open(f"{fixture_dir}stripe_ch_test2.json") as fh:
            charge_test2 = json.loads(fh.read())
        self.incomplete_charge = convert_to_stripe_object(charge_test2)

        with open(f"{fixture_dir}stripe_sub_updated_event_cancel.json") as fh:
            self.subscription_cancelled_event = json.loads(fh.read())

        with open(f"{fixture_dir}stripe_sub_updated_event_charge.json") as fh:
            self.subscription_charge_event = json.loads(fh.read())

        with open(f"{fixture_dir}stripe_sub_updated_event_reactivate.json") as fh:
            self.subscription_reactivate_event = json.loads(fh.read())

        with open(f"{fixture_dir}stripe_sub_updated_event_change.json") as fh:
            self.subscription_change_event = json.loads(fh.read())

        with open(f"{fixture_dir}stripe_sub_updated_event_no_trigger.json") as fh:
            self.subscription_updated_event_no_match = json.loads(fh.read())

        with open(f"{fixture_dir}stripe_previous_plan1.json") as fh:
            self.previous_plan = json.loads(fh.read())

        with open(f"{fixture_dir}valid_plan_response.json") as fh:
            self.plan_list = json.loads(fh.read())

        with open(f"{fixture_dir}stripe_prod_test2.json") as fh:
            self.new_product = json.loads(fh.read())

        with open(f"{fixture_dir}stripe_in_test2.json") as fh:
            self.upcoming_invoice = json.loads(fh.read())

        customer_patcher = patch("stripe.Customer.retrieve")
        product_patcher = patch("stripe.Product.retrieve")
        invoice_patcher = patch("stripe.Invoice.retrieve")
        charge_patcher = patch("stripe.Charge.retrieve")
        plan_retrieve_patcher = patch("stripe.Plan.retrieve")
        upcoming_invoice_patcher = patch("stripe.Invoice.upcoming")
        run_pipeline_patcher = patch("hub.routes.pipeline.RoutesPipeline.run")

        self.addCleanup(customer_patcher.stop)
        self.addCleanup(product_patcher.stop)
        self.addCleanup(invoice_patcher.stop)
        self.addCleanup(upcoming_invoice_patcher.stop)
        self.addCleanup(plan_retrieve_patcher.stop)
        self.addCleanup(charge_patcher.stop)
        self.addCleanup(run_pipeline_patcher.stop)

        self.mock_customer = customer_patcher.start()
        self.mock_product = product_patcher.start()
        self.mock_invoice = invoice_patcher.start()
        self.mock_upcoming_invoice = upcoming_invoice_patcher.start()
        self.mock_plan_retrieve = plan_retrieve_patcher.start()
        self.mock_charge = charge_patcher.start()
        self.mock_run_pipeline = run_pipeline_patcher.start()

    def test_run_cancel(self):
        self.mock_customer.return_value = self.customer
        self.mock_product.return_value = self.product
        self.mock_run_pipeline.return_value = None

        did_route = StripeCustomerSubscriptionUpdated(
            self.subscription_cancelled_event
        ).run()
        assert did_route

    def test_run_charge(self):
        self.mock_customer.return_value = self.customer
        self.mock_product.return_value = self.product
        self.mock_invoice.return_value = self.invoice
        self.mock_upcoming_invoice.return_value = self.invoice
        self.mock_charge.return_value = self.charge
        self.mock_run_pipeline.return_value = None
        self.mock_upcoming_invoice.return_value = self.upcoming_invoice

        did_route = StripeCustomerSubscriptionUpdated(
            self.subscription_charge_event
        ).run()
        assert did_route

    def test_run_reactivate(self):
        self.mock_customer.return_value = self.customer
        self.mock_product.return_value = self.product
        self.mock_invoice.return_value = self.invoice
        self.mock_charge.return_value = self.charge
        self.mock_run_pipeline.return_value = None

        did_route = StripeCustomerSubscriptionUpdated(
            self.subscription_reactivate_event
        ).run()
        assert did_route

    def test_run_no_action(self):
        self.mock_customer.return_value = self.customer

        did_route = StripeCustomerSubscriptionUpdated(
            self.subscription_updated_event_no_match
        ).run()
        assert did_route is False

    def test_get_user_id_missing(self):
        self.mock_customer.return_value = self.customer_missing_user

        with self.assertRaises(ClientError):
            StripeCustomerSubscriptionUpdated(
                self.subscription_updated_event_no_match
            ).get_user_id("cust_123")

    def test_get_user_id_fetch_error(self):
        self.mock_customer.side_effect = InvalidRequestError(
            message="invalid data", param="bad data"
        )

        with self.assertRaises(InvalidRequestError):
            StripeCustomerSubscriptionUpdated(
                self.subscription_updated_event_no_match
            ).get_user_id("cust_123")

    def test_get_user_id_deleted_cust(self):
        self.mock_customer.return_value = self.deleted_customer

        with self.assertRaises(ClientError):
            StripeCustomerSubscriptionUpdated(
                self.subscription_updated_event_no_match
            ).get_user_id("cust_1")

    def test_create_payload_error(self):
        self.mock_product.side_effect = InvalidRequestError(
            message="invalid data", param="bad data"
        )

        with self.assertRaises(InvalidRequestError):
            StripeCustomerSubscriptionUpdated(
                self.subscription_updated_event_no_match
            ).create_payload(
                event_type="event.type", user_id="user_123", previous_plan=None
            )

    def test_create_payload_cancelled(self):
        self.mock_product.return_value = self.product

        user_id = "user123"
        event_name = "customer.subscription_cancelled"

        expected_payload = dict(
            event_id="evt_1FXDCFJNcmPzuWtRrogbWpRZ",
            event_type=event_name,
            uid=user_id,
            customer_id="cus_FCUzOhOp9iutWa",
            subscription_id="sub_FCUzkHmNY3Mbj1",
            plan_amount=100,
            nickname="Project Guardian",
            canceled_at=None,
            cancel_at=None,
            cancel_at_period_end=True,
            current_period_start=1571949971,
            current_period_end=1572036371,
            invoice_id="in_1FXDCFJNcmPzuWtRT9U5Xvcz",
        )

        actual_payload = StripeCustomerSubscriptionUpdated(
            self.subscription_cancelled_event
        ).create_payload(event_type=event_name, user_id=user_id, previous_plan=None)

        assert actual_payload == expected_payload

    def test_create_payload_reactivated(self):
        self.mock_product.return_value = self.product
        self.mock_invoice.return_value = self.invoice
        self.mock_charge.return_value = self.charge

        user_id = "user123"
        event_name = "customer.subscription.reactivated"

        expected_payload = dict(
            event_id="evt_1FXDCFJNcmPzuWtRrogbWpRZ",
            event_type=event_name,
            uid=user_id,
            customer_id="cus_FCUzOhOp9iutWa",
            subscription_id="sub_FCUzkHmNY3Mbj1",
            plan_amount=100,
            nickname="Project Guardian",
            close_date=1571949975,
            current_period_end=1572036371,
            brand="Visa",
            last4="0019",
        )

        actual_payload = StripeCustomerSubscriptionUpdated(
            self.subscription_reactivate_event
        ).create_payload(event_type=event_name, user_id=user_id, previous_plan=None)

        assert actual_payload == expected_payload

    def test_get_subscription_change(self):
        self.mock_customer.return_value = self.product
        self.mock_invoice.return_value = self.invoice
        self.mock_upcoming_invoice.return_value = self.upcoming_invoice
        self.mock_product.return_value = self.product
        self.mock_plan_retrieve.return_value = self.previous_plan

        expected_sub_change = dict(
            close_date=1571949975,
            nickname_old="Previous Product",
            nickname_new="Test Plan Original",
            event_type="customer.subscription.upgrade",
            plan_amount_old=499,
            plan_amount_new=999,
            proration_amount=1000,
            current_period_end=1572036371,
            invoice_number="3B74E3D0-0001",
            invoice_id="in_test1",
            interval="month",
        )

        payload = dict(
            event_id="evt_change_test",
            event_type="customer.subscription.updated",
            uid=None,
            customer_id="cus_123",
            subscription_id="sub_123",
            plan_amount=999,
            nickname="Test Plan Original",
        )

        actual_sub_change = StripeCustomerSubscriptionUpdated(
            self.subscription_change_event
        ).get_subscription_change(
            payload=payload,
            previous_plan=self.previous_plan,
            new_product=self.new_product,
        )
        assert expected_sub_change == actual_sub_change
