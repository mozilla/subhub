import pytest
from api import payments


@pytest.fixture(scope="module")
def create_customer_for_processing():
    customer = payments.create_customer('tok_visa', 'process_customer', 'test_fixture@tester.com')
    print(f'customer {customer}')
    yield customer

@pytest.fixture(scope="function")
def create_subscription_for_processing():
    subscription = payments.subscribe_to_plan('process_test', {"pmt_token": "tok_visa",
                                                                   "plan_id": "plan_EtMcOlFMNWW4nd",
                                                                   "orig_system": "Test_system",
                                                                   "email": "subtest@tester.com"})
    yield subscription