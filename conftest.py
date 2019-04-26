import pytest
from api import payments


@pytest.fixture(scope="module")
def create_customer_for_processing():
    customer = payments.create_customer('tok_visa', 'process_customer', 'test_fixture@tester.com')
    yield customer


@pytest.fixture(scope="module")
def create_subscription_for_processing(create_customer_for_processing):
    subscription = payments.subscribe_to_plan('subscribe_test', {"pmt_token": 'tok_visa', "plan_id": 'plan_EtMcOlFMNWW4nd', "email": 'subscribe_test@tester.com'})
    yield subscription
