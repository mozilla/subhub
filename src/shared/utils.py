# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import uuid

from .cfg import CFG


def format_plan_nickname(product_name: str, plan_interval: str) -> str:
    interval_dict = {
        "day": "daily",
        "week": "weekly",
        "month": "monthly",
        "year": "yearly",
    }

    try:
        formatted_interval = interval_dict[plan_interval]
    except KeyError:
        formatted_interval = plan_interval

    return f"{product_name} ({formatted_interval})".title()


def get_indempotency_key() -> str:
    return uuid.uuid4().hex
