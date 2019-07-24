#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from subhub import authentication
from subhub.cfg import CFG


def test_payment_auth():
    payments_auth = authentication.payment_auth("fake_payment_api_key", None)
    assert payments_auth["value"] is True


def test_payment_auth_bad_token():
    payments_auth = authentication.payment_auth("bad_payment_api_key", None)
    assert payments_auth is None


def test_support_auth():
    support_auth = authentication.support_auth("fake_support_api_key", None)
    assert support_auth["value"] is True


def test_support_auth_bad_token():
    support_auth = authentication.support_auth("bad_support_api_key", None)
    assert support_auth is None


def test_hub_auth():
    hub_auth = authentication.hub_auth("fake_hub_api_key", None)
    assert hub_auth["value"] is True


def test_hub_auth_bad_token():
    hub_auth = authentication.hub_auth("bad_hub_api_key", None)
    assert hub_auth is None
