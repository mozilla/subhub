import pytest
from flask import g

from subhub.api import payments
from subhub.app import create_app


@pytest.fixture(scope="module")
def app():
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
