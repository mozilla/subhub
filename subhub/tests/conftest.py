import logging
import os
import signal
import subprocess

import psutil
import pytest
from flask import g

from subhub.api import payments
from subhub.app import create_app

ddb_process = None


def pytest_configure():
    """Called before testing begins"""
    global ddb_process
    for name in ('boto3', 'botocore', 'stripe'):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    if os.getenv("AWS_LOCAL_DYNAMODB") is None:
        os.environ["AWS_LOCAL_DYNAMODB"] = "http://127.0.0.1:8000"

    # Latest boto3 now wants fake credentials around, so here we are.
    os.environ["AWS_ACCESS_KEY_ID"] = "fake"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "fake"

    cmd = " ".join(["./services/fxa/node_modules/.bin/dynalite --port 8000"])
    ddb_process = subprocess.Popen(cmd, shell=True, env=os.environ,
                                   stdout=subprocess.PIPE)
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


@pytest.fixture(scope="module")
def app():
    print(f'test app')
    app = create_app()
    with app.app.app_context():
        g.subhub_account = app.app.subhub_account
        yield app


@pytest.fixture(scope="module")
def create_customer_for_processing():
    customer = payments.create_customer('tok_visa', 'process_customer', 'test_fixture@tester.com')
    yield customer


@pytest.fixture(scope="function")
def create_subscription_for_processing():
    subscription = payments.subscribe_to_plan('process_test', {"pmt_token": "tok_visa",
                                                                   "plan_id": "plan_EtMcOlFMNWW4nd",
                                                                   "orig_system": "Test_system",
                                                                   "email": "subtest@tester.com"})
    yield subscription
