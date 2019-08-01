#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import json


def _generate_pprint_json(value):
    return json.dumps(value, sort_keys=True, indent=4)


def generate_assert_failure_message(expected_value, actual_value):
    return f"\033[91m\n\nExpected:\n{_generate_pprint_json(expected_value)}\n\nActual:\n{_generate_pprint_json(actual_value)}\n\n\033[0m"
