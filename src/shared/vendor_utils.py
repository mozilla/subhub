# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


def format_brand(brand: str) -> str:
    """
    Format brand for emails prior to sending to Salesforce
    :param brand:
    :return:
    """
    brand_list = [
        ("amex", "American Express"),
        ("diners", "Diners Club"),
        ("discover", "Discover"),
        ("jcb", "JCB"),
        ("mastercard", "MasterCard"),
        ("unionpay", "UnionPay"),
        ("visa", "Visa"),
    ]
    try:
        return [item[1] for item in brand_list if item[0] == brand][0]
    except IndexError as e:
        return "Unknown"
