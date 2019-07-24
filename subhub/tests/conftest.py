#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import sys
import signal
import subprocess
import uuid
import logging

import psutil
import pytest
import stripe
from flask import g

from subhub.sub import payments
from subhub.app import create_app
from subhub.cfg import CFG
from subhub.customer import create_customer

from subhub.log import get_logger

logger = get_logger()

ddb_process = None


def pytest_configure():
    """Called before testing begins"""
    global ddb_process
    for name in ("boto3", "botocore", "stripe"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    if os.getenv("AWS_LOCAL_DYNAMODB") is None:
        os.environ["AWS_LOCAL_DYNAMODB"] = f"http://127.0.0.1:{CFG.DYNALITE_PORT}"

    # Latest boto3 now wants fake credentials around, so here we are.
    os.environ["AWS_ACCESS_KEY_ID"] = "fake"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "fake"
    os.environ["USER_TABLE"] = "users-testing"
    os.environ["EVENT_TABLE"] = "events-testing"
    os.environ["ALLOWED_ORIGIN_SYSTEMS"] = "Test_system,Test_System,Test_System1"
    sys._called_from_test = True

    # Set stripe api key
    stripe.api_key = CFG.STRIPE_API_KEY

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
        g.hub_table = app.app.hub_table
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
def create_subscription_for_processing():
    uid = uuid.uuid4()
    subscription = payments.subscribe_to_plan(
        "process_test",
        {
            "pmt_token": "tok_visa",
            "plan_id": "plan_EtMcOlFMNWW4nd",
            "origin_system": "Test_system",
            "email": "subtest@{}tester.com".format(uid),
            "display_name": "John Tester",
        },
    )
    yield subscription
