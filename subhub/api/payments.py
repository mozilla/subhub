import logging
from typing import Optional

import stripe
from flask import g, app
from stripe.error import InvalidRequestError as StripeInvalidRequest, APIConnectionError, APIError, AuthenticationError, CardError

from subhub.cfg import CFG
from subhub.secrets import get_secret
import subhub.subhub_dynamodb as dynamo

logger = logging.getLogger()
logger.setLevel(logging.INFO)

if CFG('AWS_EXECUTION_ENV', None) is None:
    stripe.api_key = CFG.STRIPE_API_KEY
else:
    subhub_values = get_secret('dev/SUBHUB')
    stripe.api_key = subhub_values['stripe_api_key']


def create_customer(source_token, userid, email):
    """
    Create Stripe customer
    :param source_token: token from browser
    :param userid: user's id
    :param email: user's email
    :return: Stripe Customer
    """
    # TODO Add error handlers and static typing
    try:
        customer = stripe.Customer.create(
            source=source_token,
            email=email,
            description=userid,
            metadata={'userid': userid}
        )
        return customer
    # TODO: Verify that this is the only error we need to worry about
    except stripe.error.InvalidRequestError as e:
        return str(e)


def subscribe_customer(customer, plan):
    """
    Subscribe Customer to Plan
    :param customer:
    :param plan:
    :return: Subscription Object
    """
    # TODO Add error handlers and static typing
    try:
        subscription = stripe.Subscription.create(
            customer=customer,
            items=[{
                "plan": plan,
            },
            ]
        )
        return subscription
    except stripe.error.InvalidRequestError as e:
        return str(e)


def existing_or_new_subscriber(uid, data):
    """
    Check if user exists and if so if they have a payment customer id, otherwise create the user
    id and/or the payment customer id
    :param uid:
    :param data:
    :return: user object
    """
    subscription_user = g.subhub_account.get_user(uid=uid)
    if not subscription_user:
        save_sub_user = g.subhub_account.save_user(uid=uid, orig_system=data["orig_system"])
        if save_sub_user:
            subscription_user = g.subhub_account.get_user(uid)
        else:
            existing_or_new_subscriber(uid, data)
    if not subscription_user.custId:
        customer = create_customer(data['pmt_token'], uid, data['email'])
        if 'No such token:' in customer:
            return 'Token not valid', 400
        update_successful = g.subhub_account.append_custid(uid, customer['id'])
        if not update_successful:
            return "Customer not saved successfully.", 400
        updated_user = g.subhub_account.get_user(uid)
        return updated_user, 200
    else:
        return subscription_user, 200
    

def has_existing_plan(user, data) -> bool:
    """
    Check if user has the existing plan in an active or trialing state.
    :param user:
    :param data:
    :return: True if user has existing plan, otherwise False
    """
    customer = stripe.Customer.retrieve(user.custId)
    for item in customer['subscriptions']['data']:
        if item["plan"]["id"] == data["plan_id"] and item['status'] in ['active', 'trialing']:
            return True
    return False


def subscribe_to_plan(uid, data) -> tuple:
    """
    Subscribe to a plan given a user id, payment token, email, orig_system
    :param uid:
    :param data:
    :return: current subscriptions for user.
    """
    sub_user, code = existing_or_new_subscriber(uid, data)
    if code == 400:
        return "Customer issue.", 400
    existing_plan = has_existing_plan(sub_user, data)
    if existing_plan:
        return "User already subscribed.", 400
    subscription = subscribe_customer(sub_user.custId, data['plan_id'])
    if 'Missing required param' in subscription:
        return 'Missing parameter ', 400
    elif 'No such plan' in subscription:
        return 'Plan not valid', 400
    updated_customer = stripe.Customer.retrieve(sub_user.custId)
    return_data = create_return_data(updated_customer["subscriptions"])
    return return_data, 201


def list_all_plans() -> tuple:
    """
    List all available plans for a user to purchase.
    :return:
    """
    plans = stripe.Plan.list(limit=100)
    stripe_plans = []
    for p in plans:
        stripe_plans.append({'plan_id': p['id'], 'product_id': p['product'], 'interval': p['interval'],
                             'amount': p['amount'], 'currency': p['currency'], 'nickname': p['nickname']})
    return stripe_plans, 200


def cancel_subscription(uid, sub_id) -> tuple:
    """
    Cancel an existing subscription for a user.
    :param uid:
    :param sub_id:
    :return: Success or failure message for the cancellation.
    """
    # TODO Remove payment source on cancel
    subscription_user = g.subhub_account.get_user(uid)
    if not subscription_user:
        return {"message": 'Customer does not exist.'}, 404
    customer = stripe.Customer.retrieve(subscription_user.custId)
    for item in customer['subscriptions']['data']:
        if item["id"] == sub_id and item['status'] in ['active', 'trialing']:
            try:
                tocancel = stripe.Subscription.retrieve(sub_id)
            except StripeInvalidRequest as e:
                # TODO handle other errors: APIConnectionError, APIError, AuthenticationError, CardError
                return {"message": e}, 400
            if 'No such subscription:' in tocancel:
                return 'Invalid subscription.', 400
            if tocancel['status'] in ['active', 'trialing']:
                tocancel.delete()
                return {"message": 'Subscription cancellation successful'}, 201
            else:
                return {"message": 'Error cancelling subscription'}, 400
    else:
        return {"message": 'Subscription not available.'}, 400


def subscription_status(uid) -> tuple:
    """
    Given a user id return the current subscription status
    :param uid:
    :return: Current subscriptions
    """
    items = g.subhub_account.get_user(uid)
    if not items or not items.custId:
        return 'Customer does not exist.', 404
    subscriptions = stripe.Subscription.list(customer=items.custId, limit=100, status='all')
    if subscriptions is None:
        return 'No subscriptions for this customer.', 404
    return_data = create_return_data(subscriptions)
    return return_data, 201


def create_return_data(subscriptions) -> dict:
    """
    Create json object subscriptions object
    :param subscriptions:
    :return: JSON data to be consumed by client.
    """
    return_data = dict()
    return_data['subscriptions'] = []
    for subscription in subscriptions["data"]:
        return_data['subscriptions'].append({
            'current_period_end': subscription['current_period_end'],
            'current_period_start': subscription['current_period_start'],
            'ended_at': subscription['ended_at'],
            'nickname': subscription['plan']['nickname'],
            'plan_id': subscription['plan']['id'],
            'status': subscription['status'],
            'subscription_id': subscription['id']})
    return return_data


def update_payment_method(uid, data) -> tuple:
    """
    Given a user id and a payment token, update user's payment method
    :param uid:
    :param data:
    :return: Success or failure message.
    """
    items = g.subhub_account.get_user(uid)
    if not items or not items.custId:
        return 'Customer does not exist.', 404
    try:
        customer = stripe.Customer.retrieve(items.custId)
        if customer['metadata']['userid'] == uid:
            try:
                customer.modify(items.custId, source=data['pmt_token'])
                return 'Payment method updated successfully.', 201
            except StripeInvalidRequest as e:
                # TODO handle other errors: APIConnectionError, APIError, AuthenticationError, CardError
                return str(e), 400
        else:
            return 'Customer mismatch.', 400
    except KeyError as e:
        return f'Customer does not exist: missing {e}', 404


def customer_update(uid) -> tuple:
    """
    Provide latest data for a given user
    :param uid:
    :return: return_data dict with credit card info and subscriptions
    """
    items = g.subhub_account.get_user(uid)
    if not items or not items.custId:
        return 'Customer does not exist.', 404
    try:
        customer = stripe.Customer.retrieve(items.custId)
        if customer['metadata']['userid'] == uid:
            return_data = create_update_data(customer)
            return return_data, 200
        else:
            return 'Customer mismatch.', 400
    except KeyError as e:
        return f'Customer does not exist: missing {e}', 404


def create_update_data(customer) -> dict:
    """
    Provide readable data for customer update to display
    :param customer:
    :return: return_data dict
    """
    return_data = dict()
    return_data['subscriptions'] = []
    return_data['payment_type'] = customer['sources']['data'][0]['funding']
    return_data['last4'] = customer['sources']['data'][0]['last4']
    return_data['exp_month'] = customer['sources']['data'][0]['exp_month']
    return_data['exp_year'] = customer['sources']['data'][0]['exp_year']
    for subscription in customer['subscriptions']['data']:
        return_data['subscriptions'].append({
            'current_period_end': subscription['current_period_end'],
            'current_period_start': subscription['current_period_start'],
            'ended_at': subscription['ended_at'],
            'nickname': subscription['plan']['nickname'],
            'plan_id': subscription['plan']['id'],
            'status': subscription['status'],
            'subscription_id': subscription['id']})
    return return_data
