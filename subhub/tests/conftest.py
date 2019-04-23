import pytest
from subhub import stripe_calls


@pytest.fixture(scope="module")
def create_customer_for_processing():
    customer = stripe_calls.create_customer('tok_visa', 'process_customer', 'test_fixture@tester.com')
    yield customer

@pytest.fixture(scope="function")
def create_subscription_for_processing():
    subscription = stripe_calls.subscribe_to_plan('process_test', {"pmt_token": "tok_visa",
                                                                   "plan_id": "plan_EtMcOlFMNWW4nd",
                                                                   "orig_system": "Test_system",
                                                                   "email": "subtest@tester.com"})
    yield subscription