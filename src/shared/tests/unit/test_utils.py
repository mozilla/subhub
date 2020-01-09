# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from hub.shared import utils


def test_format_plan_nickname():
    """
    Given a product name and plan interval
    Validate that interval is  formatted correctly
    and the returned value is  concatenated correctly
    :return:
    """
    product_name = "Test Product"
    plan_interval = "month"
    formatted_plan = utils.format_plan_nickname(
        product_name=product_name, plan_interval=plan_interval
    )
    valid_plan_name = "Test Product (Monthly)"
    assert valid_plan_name == formatted_plan


def test_format_plan_key_error():
    """
    Given a product name and an invalid interval
    Validate that the plan interval is not changed in the returned value
    :return:
    """
    product_name = "Test Product"
    plan_interval = "bi-weekly"
    formatted_plan = utils.format_plan_nickname(
        product_name=product_name, plan_interval=plan_interval
    )
    valid_plan_name = "Test Product (Bi-Weekly)"
    assert valid_plan_name == formatted_plan
