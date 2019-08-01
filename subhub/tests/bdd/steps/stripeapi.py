#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import stripe
from behave import given, when, then


@given('I am using the Stripe API located at "{api_base}"')
def using_api_base(context, api_base):
    stripe.api_base = api_base
