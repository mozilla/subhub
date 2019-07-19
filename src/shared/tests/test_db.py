# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from mockito import when, mock, unstub

from shared.db import _create_account_model
from shared.db import SubHubAccount, SubHubAccountModel

from pynamodb.exceptions import PutError


def test_create_account_model():
    cls = _create_account_model("table", "region", "https://google.com")
    assert cls.Meta.table_name == "table"
    assert cls.Meta.region == "region"
    assert cls.Meta.host == "https://google.com"


def test_save_user_PutError():
    when(SubHubAccountModel).get("uid").thenRaise(PutError)
    model = _create_account_model("table", "region", "https://google.com")()
    model.user_id = "1"
    model.cust_id = "1"
    model.origin_system = "Firefox"
    SubHubAccount.save_user(model)
