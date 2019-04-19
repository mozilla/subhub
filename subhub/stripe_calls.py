import stripe
from subhub.cfg import CFG
from flask import jsonify
import os
import boto3
from subhub.secrets import get_secret
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

premium_customers = [
    {'userId': 'mcb12345', 'custId': None, 'subscriptions': []},
    {'userId': 'moz12345', 'custId': 'cus_EtNIP101PMoaS0', 'subscriptions': []}
]

SUBHUB_TABLE = os.environ.get('SUBHUB_TABLE')
IS_DEPLOYED = os.environ.get("AWS_EXECUTION_ENV")
if IS_DEPLOYED is None:
    print(f'table {SUBHUB_TABLE}')
    stripe.api_key = CFG.STRIPE_API_KEY
    client = boto3.client(
        'dynamodb',
        region_name='localhost',
        endpoint_url='http://localhost:8000'
    )
else:
    subhub_values = get_secret('dev/SUBHUB')
    logger.info(f'{type(subhub_values)}')
    stripe.api_key = subhub_values['stripe_api_key']
    client = boto3.client('dynamodb')





# Stripe methods begin

def create_customer(source_token, fxa, email):
    """
    Create Stripe customer
    :param source_token:
    :param fxa:
    :return: Stripe Customer
    """
    try:
        customer = stripe.Customer.create(
            source=source_token,
            email=email,
            description=fxa,
            metadata={'fxuid': fxa}
        )
        return customer
    except stripe.error.InvalidRequestError as e:
        return str(e)


def subscribe_customer(customer, plan):
    """
    Subscribe Customer to Plan
    :param customer:
    :param plan:
    :return: Subscription Object
    """
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


def subscribe_to_plan(uid, data):
    if not isinstance(uid, str):
        return 'Invalid ID', 400
    try:
        subscription_user = next(f for f in premium_customers if uid == f['userId'])
        # resp = client.get_item(
        #     TableName=SUBHUB_TABLE,
        #     Key={
        #         'userId': {'S': uid}
        #     }
        # )
        # subscription_user = resp.get('Item')
        # print(f'sub user {subscription_user}')
        for fox in subscription_user['subscriptions']:
            if data['plan_id'] == fox["plan"]["id"] and fox["plan"]["active"]:
                logger.info(f'already subscribed')
                return {"message": "User has current subscription.", "code": 400}, 400
    except StopIteration as e:
        premium_customers.append({'userId': uid, 'custId': None, 'subscriptions': []})
        subscription_user = {'userId': uid, 'custId': None, 'subscriptions': []}
    if subscription_user['custId'] is None:
        if data['email'] is None:
            return 'Missing email parameter.', 400
        customer = create_customer(data['pmt_token'], uid, data['email'])
        if 'No such token:' in customer:
            return 'Token not valid', 400
        subscription = subscribe_customer(customer, data['plan_id'])
        if 'Missing required param' in subscription:
            return 'Missing parameter ', 400
        elif 'No such plan' in subscription:
            return 'Plan not valid', 400
        for f in premium_customers:
            if f['userId'] == uid:
                f['custId'] = customer['id']
                f['subscriptions'].append(subscription)
        user_subscriptions = []
        products = []
        for prod in subscription["items"]["data"]:
            products.append(prod["plan"]["product"])
        user_subscriptions.append(
            {"subscription_id": subscription["id"], "plan_id": subscription["plan"]["id"], "product_id": products,
             "current_period_end": subscription["current_period_end"], "end_at": subscription["ended_at"]})
        return user_subscriptions, 201
    else:
        subscription = subscribe_customer(subscription_user['custId'], data['plan_id'])
        if 'Missing required param' in subscription:
            return 'Missing parameter ', 400
        elif 'No such plan' in subscription:
            return 'Plan not valid', 400
        return subscription, 201


def list_all_plans():
    plans = stripe.Plan.list(limit=100)
    stripe_plans = []
    for p in plans:
        stripe_plans.append({'plan_id': p['id'], 'product_id': p['product'], 'interval': p['interval'], 'amount': p['amount'], 'currency': p['currency']})
    return stripe_plans, 200


def cancel_subscription(uid, sub_id):
    # TODO Remove payment source on cancel
    try:
        subscription_user = next(f for f in premium_customers if uid == f['userId'])
    except StopIteration as e:
        return 'User does not exist', 404
    subscriptions = []
    for fox in subscription_user['subscriptions']:
        subscriptions.append(fox['id'])
    if sub_id in subscriptions:
        try:
            tocancel = stripe.Subscription.retrieve(sub_id)
        except stripe.error.InvalidRequestError as e:
            return str(e)
        if 'No such subscription:' in tocancel:
            return 'Invalid subscription.', 400
        if tocancel['status'] in ['active', 'trialing']:
            tocancel.delete()
            return tocancel, 201
        else:
            return 'Error cancelling subscription', 400
    else:
        return 'Subscription not available.', 400


def subscription_status(uid):
    if not isinstance(uid, str):
        return 'Invalid ID', 400
    try:
        subscription_user = next(f for f in premium_customers if uid == f['userId'])
    except StopIteration as e:
        return 'Customer ID not valid.', 400
    subscriptions = stripe.Subscription.list(customer=subscription_user['custId'], limit=100)
    if subscriptions is None:
        return 'No subscriptions for this customer.', 404
    user_subscriptions = []
    for sub in subscriptions["data"]:
        products = []
        for prod in sub["items"]["data"]:
            products.append(prod["plan"]["product"])
        user_subscriptions.append({"subscription_id": sub["id"], "plan_id": sub["plan"]["id"], "product_id": products,
                                   "current_period_end": sub["current_period_end"], "end_at": sub["ended_at"]})
    return user_subscriptions, 201



def update_payment_method(uid, data):
    if not isinstance(data['pmt_token'], str):
        return 'Missing token', 400
    try:
        subscription_user = next(f for f in premium_customers if uid == f['userId'])
    except StopIteration:
        return 'Missing or invalid user', 400
    if subscription_user['custId'] is None:
        return 'Customer does not exist.', 400
    customer = stripe.Customer.retrieve(subscription_user['custId'])
    if customer['metadata']['fxuid'] == uid:
        try:
            updated_customer = customer.modify(subscription_user['custId'], source=data['pmt_token'])
            return updated_customer, 201
        except stripe.error.InvalidRequestError as e:
            return str(e), 400
    else:
        return 'Customer mismatch.', 400


def fxa_customer_update(uid):
    logger.info(f'customer update {uid}')
    return {"customer": uid}, 200


def api_validation(api_token):
    if api_token is None:
        return False
    elif isinstance(api_token, int):
        return False
    else:
        return True
