#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from subhub.exceptions import SecretStringMissingError


def test_SecretStringMissingError():
    secret = {"foo": "bar", "baz": "qux"}
    error = SecretStringMissingError(secret)
    assert error
