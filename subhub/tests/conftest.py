import pytest
from subhub import stripe_calls


@pytest.fixture(scope="module")
def create_customer_for_processing():
    customer = stripe_calls.create_customer('tok_visa', 'process_customer', 'test_fixture@tester.com')
    yield customer
