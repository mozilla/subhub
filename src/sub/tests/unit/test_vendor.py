# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
import stripe

from stripe.error import APIError, APIConnectionError

from sub.shared import vendor, utils


def disable_base():
    stripe.api_base = "http://example.com"


def enable_base():
    stripe.api_base = "https://api.stripe.com"


def test_customer_list_error():
    disable_base()
    with pytest.raises(APIError):
        vendor.get_customer_list("")
    enable_base()


def test_modify_customer_error():
    disable_base()
    with pytest.raises(APIError):
        vendor.modify_customer(
            "no_customer", "tok_nothing", utils.get_indempotency_key()
        )
    enable_base()


def test_create_stripe_customer_error():
    disable_base()
    with pytest.raises(APIError):
        vendor.create_stripe_customer(
            "token",
            "noone@nowhere.com",
            "abc123",
            "Anonymous",
            utils.get_indempotency_key(),
        )
    enable_base()


def test_delete_stripe_customer_error():
    disable_base()
    with pytest.raises(APIError):
        vendor.delete_stripe_customer("no_one")
    enable_base()


def test_retrieve_stripe_customer_error():
    disable_base()
    with pytest.raises(APIError):
        vendor.retrieve_stripe_customer("no_one")
    enable_base()


def test_build_stripe_subscription_error():
    disable_base()
    with pytest.raises(APIError):
        vendor.build_stripe_subscription(
            "no_one", "no_plan", utils.get_indempotency_key()
        )
    enable_base()


def test_cancel_stripe_subscription_period_end_error():
    disable_base()
    with pytest.raises(APIError):
        vendor.cancel_stripe_subscription_period_end(
            "no_sub", utils.get_indempotency_key()
        )
    enable_base()


def test_list_customer_subscriptions_error():
    disable_base()
    with pytest.raises(APIError):
        vendor.list_customer_subscriptions("no_cust")
    enable_base()


def test_retrieve_stripe_charge_error():
    disable_base()
    with pytest.raises(APIError):
        vendor.retrieve_stripe_charge("no_charge")
    enable_base()


def test_retrieve_stripe_invoice_error():
    disable_base()
    with pytest.raises(APIError):
        vendor.retrieve_stripe_invoice("no_invoice")
    enable_base()


def test_retrieve_plan_list_error():
    disable_base()
    with pytest.raises(APIError):
        vendor.retrieve_plan_list(0)
    enable_base()


def test_retrieve_stripe_product_error():
    disable_base()
    with pytest.raises(APIError):
        vendor.retrieve_stripe_product("no_prod")
    enable_base()
