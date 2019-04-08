from subhub import stripe_calls
import pytest
import stripe


def test_create_customer_tok_visa():
    """
    GIVEN create a stripe customer
    WHEN provided a test visa token and test fxa
    THEN validate the customer metadata is correct
    """
    customer = stripe_calls.create_customer('tok_visa', 'test_mozilla', 'test_visa@tester.com')
    pytest.customer = customer
    assert customer['metadata']['fxuid'] == 'test_mozilla'

def test_create_customer_tok_mastercard():
    """
    GIVEN create a stripe customer
    WHEN provided a test mastercard token and test fxa
    THEN validate the customer metadata is correct
    """
    customers = stripe_calls.create_customer('tok_mastercard', 'test_mozilla', 'test_mastercard@tester.com')
    assert customers['metadata']['fxuid'] == 'test_mozilla'

def test_create_customer_tok_invalid():
    """
    GIVEN create a stripe customer
    WHEN provided an invalid test token and test fxa
    THEN validate the customer metadata is correct
    """
    customers = stripe_calls.create_customer('tok_invalid', 'test_mozilla', 'test_invalid@tester.com')
    assert 'No such token: tok_invalid' in customers

def test_create_customer_tok_avsFail():
    """
    GIVEN create a stripe customer
    WHEN provided an invalid test token and test fxa
    THEN validate the customer metadata is correct
    """
    customers = stripe_calls.create_customer('tok_avsFail', 'test_mozilla', 'test_avsfail@tester.com')
    assert customers['metadata']['fxuid'] == 'test_mozilla'

def test_create_customer_tok_avsUnchecked():
    """
    GIVEN create a stripe customer
    WHEN provided an invalid test token and test fxa
    THEN validate the customer metadata is correct
    """
    customers = stripe_calls.create_customer('tok_avsUnchecked', 'test_mozilla', 'test_avsunchecked@tester.com')
    assert customers['metadata']['fxuid'] == 'test_mozilla'


def test_subscribe_customer(create_customer_for_processing):
    """
    GIVEN create a subscription
    WHEN provided a customer and plan
    THEN validate subscription is created
    """
    customer = create_customer_for_processing
    subscription = stripe_calls.subscribe_customer(customer, 'plan_EozlyJpXw1runC')
    assert subscription['plan']['active']


def test_subscribe_customer_invalid_plan(create_customer_for_processing):
    """
    GIVEN create a subscription
    WHEN provided a customer and plan
    THEN validate subscription is created
    """
    customer = create_customer_for_processing
    subscription = stripe_calls.subscribe_customer(customer, 'plan_notvalid')
    assert 'No such plan: plan_notvalid' in subscription


def test_create_subscription_with_valid_data(create_customer_for_processing):
    """
    GIVEN create a subscription
    WHEN provided a api_token, fxa, pmt_token, plan_id, cust_id
    THEN validate subscription is created
    """
    customer = create_customer_for_processing
    subscription = stripe_calls.subscribe_to_plan('test_token', 'mcb12345', 'tok_visa', 'plan_EozlyJpXw1runC', customer['email'])
    assert 201 in subscription


def test_create_subscription_with_missing_api_token(create_customer_for_processing):
    """
        GIVEN create a subscription
        WHEN provided a api_token, fxa, pmt_token, plan_id, email
        THEN validate subscription is created
        """
    customer = create_customer_for_processing
    subscription = stripe_calls.subscribe_to_plan(None, 'mcb12345', 'tok_visa', 'plan_EozlyJpXw1runC', customer['email'])
    assert 400 in subscription


def test_create_subscription_with_invalid_api_token(create_customer_for_processing):
    """
    GIVEN create a subscription
    WHEN provided a api_token, fxa, pmt_token, plan_id, email
    THEN validate subscription is created
    """
    customer = create_customer_for_processing
    subscription = stripe_calls.subscribe_to_plan(913, 'mcb12345', 'tok_visa', 'plan_EozlyJpXw1runC', customer['email'])
    assert 400 in subscription
