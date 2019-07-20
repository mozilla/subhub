#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest.mock import MagicMock, PropertyMock

from subhub.customer import fetch_customer


def test_fetch_customer_no_account(monkeypatch):
    """
    GIVEN an invalid user_id
    WHEN a user attempts to fetch a customer
    THEN None is returned
    """

    subhub_account = MagicMock()
    get_user = MagicMock(return_value=None)
    subhub_account.get_user = get_user

    customer = fetch_customer(subhub_account, "user123")

    assert customer is None


def test_fetch_customer_missing_stripe(monkeypatch):
    """
    GIVEN a valid user_id that maps to an deleted customer account
    WHEN a user attempts to fetch a customer
    THEN None is returned
    """
    subhub_account = MagicMock()

    get_user = MagicMock()
    user_id = PropertyMock(return_value="user123")
    cust_id = PropertyMock(return_value="cust123")
    type(get_user).user_id = user_id
    type(get_user).cust_id = cust_id

    remove_from_db = MagicMock(return_value=None)

    subhub_account.get_user = get_user
    subhub_account.remove_from_db = remove_from_db

    mock_customer = MagicMock(return_value={"id": "cust123", "deleted": True})

    monkeypatch.setattr("stripe.Customer.retrieve", mock_customer)

    customer = fetch_customer(subhub_account, "user123")

    assert customer is None


def test_fetch_customer_success(monkeypatch):
    """
    GIVEN a valid user_id that maps to a valid customer account
    WHEN a user attempts to fetch a customer
    THEN that customer is returned
    """

    subhub_account = MagicMock()

    get_user = MagicMock()
    user_id = PropertyMock(return_value="user123")
    cust_id = PropertyMock(return_value="cust123")
    type(get_user).user_id = user_id
    type(get_user).cust_id = cust_id

    subhub_account.get_user = get_user

    mock_customer = MagicMock(return_value={"id": "cust123", "deleted": False})

    monkeypatch.setattr("stripe.Customer.retrieve", mock_customer)

    customer = fetch_customer(subhub_account, "user123")

    assert customer is not None
