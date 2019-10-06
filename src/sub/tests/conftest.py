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

import backoff
import docker

from unittest.mock import Mock, MagicMock, PropertyMock

import psutil
import pytest
import requests
import stripe

from flask import g

from sub import payments
from sub.app import create_app
from sub.shared.cfg import CFG
from sub.customer import create_customer

from shared.log import get_logger

logger = get_logger()

THIS_PATH = os.path.join(os.path.realpath(os.path.dirname(__file__)))
UID = str(uuid.uuid4())
IMAGE = "vitarn/dynalite:latest"
CONTAINERS_FOR_TESTING_LABEL = "pytest_docker_log"


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
    for name in ("boto3", "botocore"):
        logging.getLogger(name).setLevel(logging.CRITICAL)

    os.environ["AWS_ACCESS_KEY_ID"] = "fake"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "fake"
    os.environ["USER_TABLE"] = "users-testing"
    os.environ["DELETED_USER_TABLE"] = "deleted-users-testing"
    os.environ["ALLOWED_ORIGIN_SYSTEMS"] = "Test_system,Test_System,Test_System1"
    sys._called_from_test = True


def get_free_tcp_port():
    import socket

    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.bind(("", 0))
    addr, port = tcp.getsockname()
    tcp.close()
    return port


def _docker_client():
    return docker.from_env()


def pull_image(image):
    docker_client = _docker_client()
    response = docker_client.api.pull(image)
    lines = [line for line in response.splitlines() if line]
    pull_result = json.loads(lines[-1])
    if "error" in pull_result:
        raise Exception("Could not pull {}: {}".format(image, pull_result["error"]))


@pytest.yield_fixture(scope="module", autouse=True)
def dynamodb():
    pull_image(IMAGE)
    docker_client = _docker_client()
    host_port = get_free_tcp_port()
    port_bindings = {4567: host_port}
    host_config = docker_client.api.create_host_config(port_bindings=port_bindings)
    container = docker_client.api.create_container(
        image=IMAGE,
        labels=[CONTAINERS_FOR_TESTING_LABEL],
        host_config=host_config,
        ports=[4567],
    )
    docker_client.api.start(container=container["Id"])
    container_info = docker_client.api.inspect_container(container.get("Id"))

    host_ip = container_info["NetworkSettings"]["Ports"]["4567/tcp"][0]["HostIp"]
    host_port = container_info["NetworkSettings"]["Ports"]["4567/tcp"][0]["HostPort"]
    yield f"http://{host_ip}:{host_port}"
    docker_client.api.remove_container(container=container["Id"], force=True)


@backoff.on_exception(backoff.fibo, Exception, max_tries=8)
def _check_container(url):
    return requests.get(url)


@pytest.fixture(autouse=True, scope="module")
def app(dynamodb):
    os.environ["DYNALITE_URL"] = dynamodb
    _check_container(dynamodb)
    app = create_app()
    with app.app.app_context():
        g.subhub_account = app.app.subhub_account
        g.subhub_deleted_users = app.app.subhub_deleted_users
        yield app


@pytest.fixture()
def create_customer_for_processing(dynamodb):
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
