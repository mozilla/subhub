# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import sys
import signal
import subprocess
import uuid
import logging
import json

from unittest.mock import Mock, MagicMock, PropertyMock

import psutil
import pytest
import stripe

from flask import g

from sub import payments
from sub.app import create_app
from sub.shared.cfg import CFG
from sub.customer import create_customer

from sub.shared.log import get_logger

logger = get_logger()

ddb_process = None
THIS_PATH = os.path.join(os.path.realpath(os.path.dirname(__file__)))
UID = str(uuid.uuid4())


class MockCustomer:
    id = None
    object = "customer"
    subscriptions = [{"data": "somedata"}]

    def properties(self, cls):
        return [i for i in cls.__dict__.keys() if i[:1] != "_"]

    def get(self, key, default=None):
        properties = self.properties(MockCustomer)
        if key in properties:
            return key
        else:
            return default


def get_file(filename, path=THIS_PATH, **overrides):
    with open(f"{path}/unit/customer/{filename}") as f:
        obj = json.load(f)
        return dict(obj, **overrides)


def pytest_configure():
    """Called before testing begins"""
    global ddb_process
    for name in ("boto3", "botocore"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    if os.getenv("AWS_LOCAL_DYNAMODB") is None:
        os.environ["AWS_LOCAL_DYNAMODB"] = f"http://127.0.0.1:{CFG.DYNALITE_PORT}"

    # Latest boto3 now wants fake credentials around, so here we are.
    os.environ["AWS_ACCESS_KEY_ID"] = "fake"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "fake"
    os.environ["USER_TABLE"] = "users-testing"
    os.environ["DELETED_USER_TABLE"] = "deleted-users-testing"
    os.environ["ALLOWED_ORIGIN_SYSTEMS"] = "Test_system,Test_System,Test_System1"
    sys._called_from_test = True

    # Locate absolute path of dynalite
    dynalite = f"{CFG.REPO_ROOT}/node_modules/.bin/dynalite"

    cmd = f"{dynalite} --port {CFG.DYNALITE_PORT}"
    ddb_process = subprocess.Popen(
        cmd, shell=True, env=os.environ, stdout=subprocess.PIPE
    )
    while 1:
        line = ddb_process.stdout.readline()
        if line.startswith(b"Listening"):
            break


def pytest_unconfigure():
    del sys._called_from_test
    global ddb_process
    """Called after all tests run and warnings displayed"""
    proc = psutil.Process(pid=ddb_process.pid)
    child_procs = proc.children(recursive=True)
    for p in [proc] + child_procs:
        os.kill(p.pid, signal.SIGTERM)
    ddb_process.wait()


@pytest.fixture(autouse=True, scope="module")
def app():
    app = create_app()
    with app.app.app_context():
        g.subhub_account = app.app.subhub_account
        g.subhub_deleted_users = app.app.subhub_deleted_users
        yield app


@pytest.fixture()
def create_customer_for_processing():
    uid = uuid.uuid4()
    customer = create_customer(
        g.subhub_account,
        user_id="process_customer",
        source_token="tok_visa",
        email="test_fixture@{}tester.com".format(uid.hex),
        origin_system="Test_system",
        display_name="John Tester",
    )
    yield customer


@pytest.fixture(scope="function")
def create_subscription_for_processing(monkeypatch):
    subhub_account = MagicMock()

    get_user = MagicMock()
    user_id = PropertyMock(return_value=UID)
    cust_id = PropertyMock(return_value="cust123")
    type(get_user).user_id = user_id
    type(get_user).cust_id = cust_id

    subhub_account.get_user = get_user

    customer = Mock(return_value=MockCustomer())
    none = Mock(return_value=None)
    updated_customer = Mock(
        return_value={
            "subscriptions": {"data": [get_file("subscription1.json")]},
            "metadata": {"userid": "process_test"},
            "id": "cust_123",
        }
    )
    product = Mock(return_value={"name": "Mozilla Product"})

    monkeypatch.setattr("flask.g.subhub_account", subhub_account)
    monkeypatch.setattr("sub.payments.existing_or_new_customer", customer)
    monkeypatch.setattr("sub.payments.has_existing_plan", none)
    monkeypatch.setattr("stripe.Subscription.create", Mock)
    monkeypatch.setattr("stripe.Customer.retrieve", updated_customer)
    monkeypatch.setattr("stripe.Product.retrieve", product)

    data = json.dumps(
        {
            "pmt_token": "tok_visa",
            "plan_id": "plan_EtMcOlFMNWW4nd",
            "origin_system": "Test_system",
            "email": "subtest@tester.com",
            "display_name": "John Tester",
        }
    )

    subscription = payments.subscribe_to_plan("process_test", json.loads(data))
    yield subscription
