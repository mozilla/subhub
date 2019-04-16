from subhub import stripe_calls
import pytest
import json


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
    subscription = stripe_calls.subscribe_customer(customer, 'plan_EtMcOlFMNWW4nd')
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
    subscription = stripe_calls.subscribe_to_plan('mcb12345', {"pmt_token": 'tok_visa', "plan_id": 'plan_EtMcOlFMNWW4nd', "email": customer['email']})
    assert 201 in subscription


def test_create_subscription_with_missing_fxa_id(create_customer_for_processing):
    """
    GIVEN should not create a subscription
    WHEN provided a api_token, no fxa, pmt_token, plan_id, email
    THEN validate subscription is created
    """
    customer = create_customer_for_processing
    subscription = stripe_calls.subscribe_to_plan(None, {"pmt_token": 'tok_visa', "plan_id": 'plan_EtMcOlFMNWW4nd', "email": customer['email']})
    assert 400 in subscription

def test_create_subscription_with_invalid_fxa_id(create_customer_for_processing):
    """
    GIVEN should not create a subscription
    WHEN provided a api_token, invalid fxa, pmt_token, plan_id, email
    THEN validate subscription is created
    """
    customer = create_customer_for_processing
    subscription = stripe_calls.subscribe_to_plan(123, {"pmt_token": 'tok_visa', "plan_id": 'plan_EtMcOlFMNWW4nd', "email": customer['email']})
    assert 400 in subscription


def test_create_subscription_with_missing_payment_token():
    """
    GIVEN should not create a subscription
    WHEN provided a api_token, fxa, invalid pmt_token, plan_id, email
    THEN validate subscription is created
    """
    subscription = stripe_calls.subscribe_to_plan('123456', {"pmt_token": 'tok_invalid', "plan_id": 'plan_EtMcOlFMNWW4nd', "email": 'invalid_test@test.com'})
    assert 400 in subscription


def test_create_subscription_with_invalid_payment_token():
    """
    GIVEN should not create a subscription
    WHEN provided a api_token, fxa, invalid pmt_token, plan_id, email
    THEN validate subscription is created
    """
    subscription = stripe_calls.subscribe_to_plan('12345', {"pmt_token": 1234, "plan_id": 'plan_EtMcOlFMNWW4nd', "email": 'invalid_test@test.com'})
    assert 400 in subscription


def test_create_subscription_with_missing_plan_id():
    """
    GIVEN should not create a subscription
    WHEN provided a api_token, fxa, pmt_token, missing plan_id, email
    THEN validate subscription is created
    """
    subscription = stripe_calls.subscribe_to_plan('missing_plan', {"pmt_token": 'tok_visa', "plan_id": None, "email": 'missing_plan@tester.com'})
    assert 400 in subscription


def test_create_subscription_with_invalid_plan_id():
    """
    GIVEN should not create a subscription
    WHEN provided a api_token, fxa, pmt_token, invalid plan_id, email
    THEN validate subscription is created
    """
    subscription = stripe_calls.subscribe_to_plan('invalid_plan', {"pmt_token": 'tok_visa', "plan_id": 'plan_abc123', "email": 'invalid_plan@tester.com'})
    assert 400 in subscription


def test_create_subscription_with_missing_email_id():
    """
    GIVEN should not create a subscription
    WHEN provided a api_token, fxa, pmt_token, plan_id, missing email
    THEN validate subscription is created
    """
    subscription = stripe_calls.subscribe_to_plan('missing_email', {"pmt_token": 'tok_visa', "plan_id": 'plan_EtMcOlFMNWW4nd', "email": None})
    assert 400 in subscription


def test_list_all_plans_valid():
    """
    GIVEN should list all available plans
    WHEN provided an api_token,
    THEN validate able to list all available plans
    """
    (plans, code) = stripe_calls.list_all_plans()
    assert len(plans) > 0
    assert 200 == code


def test_cancel_subscription_with_valid_data(create_subscription_for_processing):
    """
    GIVEN should cancel an active subscription
    WHEN provided a api_token, and subscription id
    THEN validate should cancel subscription
    """
    (subscription, code) = create_subscription_for_processing
    print(f'subscription {subscription}')
    print(f'code {code}')
    (cancelled, code) = stripe_calls.cancel_subscription('subscribe_test', subscription['id'])
    for can in cancelled:
        assert can['status'] == 'canceled'
    assert 201 == code


def test_cancel_subscription_with_missing_subscription_id(create_subscription_for_processing):
    """
    GIVEN should not cancel an active subscription
    WHEN provided a api_token, and missing subscription id
    THEN validate should not cancel subscription
    """
    (cancelled, code) = stripe_calls.cancel_subscription('subscribe_test', None)
    assert 400 == code


def test_check_subscription_with_valid_parameters():
    """
    GIVEN should get a list of active subscriptions
    WHEN provided an api_token and a fxa id
    THEN validate should return list of active subscriptions
    """
    (sub_status, code) = stripe_calls.subscription_status('moz12345')
    assert 201 == code
    assert len(sub_status['data']) > 0



def test_check_subscription_with_missing_fxa_id():
    """
    GIVEN should not get a list of active subscriptions
    WHEN provided an api_token and a missing fxa id
    THEN validate should not return list of active subscriptions
    """
    (sub_status, code) = stripe_calls.subscription_status(None)
    assert 400 == code
    assert 'Invalid ID' in sub_status


def test_check_subscription_with_invalid_fxa_id():
    """
    GIVEN should not get a list of active subscriptions
    WHEN provided an api_token and an invalid fxa id
    THEN validate should not return list of active subscriptions
    """
    (sub_status, code) = stripe_calls.subscription_status(42)
    assert 400 == code
    assert 'Invalid ID' in sub_status


def test_update_payment_method_valid_parameters():
    """
    GIVEN api_token, fxa, pmt_token
    WHEN all parameters are valid
    THEN update payment method for a customer
    """
    (updated_pmt, code) = stripe_calls.update_payment_method('moz12345', {"pmt_token": 'tok_mastercard'})
    assert 201 == code


def test_update_payment_method_missing_fxa_id():
    """
    GIVEN api_token, fxa, pmt_token
    WHEN missing fxa id
    THEN do not update payment method for a customer
    """
    (updated_pmt, code) = stripe_calls.update_payment_method(None, {"pmt_token": 'tok_mastercard'})
    assert 400 == code
    assert 'Missing or invalid user' in updated_pmt


def test_update_payment_method_invalid_fxa_id():
    """
    GIVEN api_token, fxa, pmt_token
    WHEN invalid fxa id
    THEN do not update payment method for a customer
    """
    (updated_pmt, code) = stripe_calls.update_payment_method(42, {"pmt_token": 'tok_mastercard'})
    assert 400 == code
    assert 'Missing or invalid user' in updated_pmt


def test_update_payment_method_missing_payment_token():
    """
    GIVEN api_token, fxa, pmt_token
    WHEN missing pmt_token
    THEN do not update payment method for a customer
    """
    (updated_pmt, code) = stripe_calls.update_payment_method('moz12345', {"pmt_token": None})
    assert 400 == code
    assert 'Missing token' in updated_pmt


def test_update_payment_method_invalid_payment_token():
    """
    GIVEN api_token, fxa, pmt_token
    WHEN invalid pmt_token
    THEN do not update payment method for a customer
    """
    (updated_pmt, code) = stripe_calls.update_payment_method('moz12345', {"pmt_token": 'tok_invalid'})
    assert 400 == code
    assert 'No such token:' in updated_pmt
