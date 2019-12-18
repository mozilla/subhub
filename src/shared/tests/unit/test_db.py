# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import random
import string 

from shared.db import (
    HubEvent,
    SubHubDeletedAccount,
    SubHubAccount,
    _create_account_model,
    _create_deleted_account_model,
    _create_hub_model,
)

from shared.dynamodb import dynamodb
from past.builtins import xrange

####################
# SubHubAccountModel
# SubHubAccount
####################


def generate_random_table():
    return "".join(
        [random.choice(string.ascii_letters + string.digits) for n in xrange(32)]
    )


def test_create_account_model(dynamodb):
    model = _create_account_model(generate_random_table(), "local", dynamodb)
    assert model is not None


def test_new_user_account_model(dynamodb):
    subhub_account = SubHubAccount(generate_random_table(), "local", dynamodb)
    customer_model = subhub_account.new_user(
        "uid", "origin_system", "customer_identifier"
    )
    assert customer_model is not None

######################################################
# TODO(med): These tests rely on the container
# being clean which isn't guaranteed right not.  These
# merely serve as a placeholder for future tests that
# need to be written.
######################################################

# def test_get_user_account_model(dynamodb):
#     subhub_account = SubHubAccount(generate_random_table(), "local", dynamodb)
#     customer_model = subhub_account.new_user(
#         "uid", "origin_system", "customer_identifier"
#     )
#     user_model = subhub_account.get_user("uid")
#     assert user_model is not None


# def test_append_customer_id_account_model(dynamodb):
#     subhub_account = SubHubAccount(generate_random_table(), "local", dynamodb)
#     customer_model = subhub_account.new_user(
#         "uid", "origin_system", "customer_identifier"
#     )
#     user_model = subhub_account.append_custid("uid", "customer_identifier2")
#     assert subhub_account.get_user("uid").cust_id == "customer_identifier2"


# def test_remove_from_db_account_model(dynamodb):
#     subhub_account = SubHubAccount(generate_random_table(), "local", dynamodb)
#     customer_model = subhub_account.new_user(
#         "uid", "origin_system", "customer_identifier"
#     )
#     user_model = subhub_account.append_custid("uid", "customer_identifier2")
#     subhub_account.remove_from_db("uid")
#     assert subhub_account.get_user("uid") is None


# def test_mark_deleted_account_model(dynamodb):
#     subhub_account = SubHubAccount(generate_random_table(), "local", dynamodb)
#     customer_model = subhub_account.new_user(
#         "uid", "origin_system", "customer_identifier"
#     )
#     subhub_account.mark_deleted("uid")
#     user_model = subhub_account.get_user("uid")
#     assert subhub_account.customer_status == "deleted"


####################
# HubEventModel
####################


def test_create_create_hub_model(dynamodb):
    model = _create_hub_model(generate_random_table(), "local", dynamodb)
    assert model is not None


def test_append_event_hub_event(dynamodb):
    pass


def test_remove_from_db_hub_event(dynamodb):
    pass


####################
# SubHubDeletedAccountModel
####################


def test_create_deleted_account_model(dynamodb):
    model = _create_deleted_account_model(generate_random_table(), "local", dynamodb)
    assert model is not None


def test_new_deleted_user_created(dynamodb):
    subhub_deleted_account_model = SubHubDeletedAccount(
        generate_random_table(), "local", dynamodb
    )
    user_model = subhub_deleted_account_model.new_user("uid", "origin_system", None)
    assert user_model is not None
