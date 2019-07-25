#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from subhub.db import SubHubAccount


class DynamoUtils:
    def __init__(self, table_name, region, host):
        self.subhub_account = SubHubAccount(table_name, region, host)

    def create_user(self, uid, origin_system, customer_id):
        self.subhub_account.new_user(uid, origin_system, customer_id)

    def delete_user(self, uid):
        self.subhub_account.remove_from_db(uid)
