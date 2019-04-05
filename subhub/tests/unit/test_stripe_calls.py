from subhub import stripe_calls
import logging

customer = ''

def test_create_customer():
    """
    GIVEN create a stripe customer
    WHEN provided a test token and test fxa
    THEN validate the customer metadata is correct
    """
    customer = stripe_calls.create_customer('tok_visa', 'test_mozilla')
    print(f'customer {customer}')
    assert customer['metadata']['fxuid'] == 'test_mozilla'

def test_subscribe_customer():
    """
    GIVEN create a subscription
    WHEN provided a customer and plan
    THEN validate subscription is created
    """
    subscription = stripe_calls.subscribe_customer(customer, 'plan_EozlyJpXw1runC')
    print(f'subscription {subscription}')
    assert subscription is not None
