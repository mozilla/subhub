# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from hub.shared import vendor_utils


def test_format_brand():
    """
    Given brand is visa
    Test that brand is found in brand list and correct value is returned
    :return:
    """
    brand = "visa"
    found_brand = vendor_utils.format_brand(brand)
    assert found_brand == "Visa"


def test_format_brand_unknown():
    """
    Given brand is not in list
    Test that brand is not found in brand list and Unknown is returned
    :return:
    """
    brand = "test"
    found_brand = vendor_utils.format_brand(brand)
    assert found_brand == "Unknown"
