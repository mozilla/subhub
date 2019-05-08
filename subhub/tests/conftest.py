import logging
import os
import signal
import subprocess
import uuid

import psutil
import pytest
import stripe
from flask import g

from subhub.api import payments
from subhub.app import create_app
from subhub.cfg import CFG
from subhub.customer import create_customer

ddb_process = None


def pytest_configure():
    """Called before testing begins"""
    global ddb_process
    for name in ("boto3", "botocore", "stripe"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    if os.getenv("AWS_LOCAL_DYNAMODB") is None:
        os.environ["AWS_LOCAL_DYNAMODB"] = "http://127.0.0.1:8000"

    # Latest boto3 now wants fake credentials around, so here we are.
    os.environ["AWS_ACCESS_KEY_ID"] = "fake"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "fake"
    os.environ["USER_TABLE"] = "subhub-acct-table-dev"

    # Set stripe api key
    stripe.api_key = CFG.STRIPE_API_KEY

    # Locate absolute path of dynalite
    here_dir = os.path.abspath(os.path.dirname(__file__))
    root_dir = os.path.dirname(os.path.dirname(here_dir))
    dynalite = os.path.join(root_dir, "services/fxa/node_modules/.bin/dynalite")

    cmd = " ".join([f"{dynalite} --port 8000"])
    ddb_process = subprocess.Popen(
        cmd, shell=True, env=os.environ, stdout=subprocess.PIPE
    )
    while 1:
        line = ddb_process.stdout.readline()
        if line.startswith(b"Listening"):
            break


def pytest_unconfigure():
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
            "orig_system": "Test_system",
            "email": "subtest@{}tester.com".format(uid),
        },
    )
    yield subscription
