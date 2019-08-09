# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from subhub.tests.bdd.deps.stripeapi import StripeUtils


def before_all(context):
    context.stripe_utils = StripeUtils(context)


def before_scenario(context, scenario):
    context.headers = {}
    context.data = u""
    context.query = {}
