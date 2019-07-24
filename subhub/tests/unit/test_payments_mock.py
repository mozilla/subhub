#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import stripe

from mockito import when, mock, unstub, ANY

from subhub.sub import payments
from subhub.log import get_logger

logger = get_logger()


def test_check_stripe_subscriptions():
    response = mock(
        {
            "id": "cus_tester1",
            "object": "customer",
            "subscriptions": {"data": [{"status": "active", "id": "sub_123"}]},
            "sources": {"data": [{"id": "src_123"}]},
        },
        spec=stripe.Customer,
    )
    test_subscriptions = payments.check_stripe_subscriptions(response)
    logger.info("test subscriptions", test_subscriptions=test_subscriptions)
    assert test_subscriptions[0]["id"] == "sub_123"
    assert test_subscriptions[0]["status"] == "active"
    unstub()


def test_check_stripe_subscriptions_cancelled():
    cancelled_sub = {"status": "cancelled", "id": "sub_124", "cancel_at": 232322}

    cancel_response = mock(
        {
            "id": "cus_tester2",
            "object": "customer",
            "subscriptions": {"data": [cancelled_sub]},
            "sources": {"data": [{"id": "src_123"}]},
        },
        spec=stripe.Customer,
    )

    delete_response = mock(
        {"id": "cus_tester2", "object": "customer", "sources": []}, spec=stripe.Customer
    )
    when(stripe.Customer).delete_source("cus_tester2", "src_123").thenReturn(
        delete_response
    )
    test_cancel = payments.check_stripe_subscriptions(cancel_response)
    logger.info("test cancel", test_cancel=test_cancel)
    assert test_cancel[0]["status"] == "cancelled"
    unstub()


def test_check_stripe_subscriptions_fail():
    cancel_response = mock(
        {
            "id": "cus_tester3",
            "object": "customer",
            "subscriptions": {"data": []},
            "sources": {"data": [{"id": "src_123"}]},
        },
        spec=stripe.Customer,
    )
    delete_response = mock(
        {"id": "cus_tester3", "object": "customer", "sources": []}, spec=stripe.Customer
    )
    when(stripe.Customer).delete_source("cus_tester3", "src_123").thenReturn(
        delete_response
    )
    test_fail = payments.check_stripe_subscriptions(cancel_response)
    logger.info("test fail", test_fail=test_fail)
    assert test_fail == []
    unstub()


def test_check_stripe_subscriptions_name_error():
    customer = mock(
        {
            "id": "cus_tester3",
            "object": "customer",
            "subscriptions": {"data": []},
            "sources": {"data": [{"id": "src_123"}]},
        },
        spec=stripe.Customer,
    )
    when(stripe.Customer).delete_source("cus_tester3", "src_123").thenRaise(NameError)

    test_fail = payments.check_stripe_subscriptions(customer)
    logger.info("test fail", test_fail=test_fail)
    assert test_fail == []
    unstub()
