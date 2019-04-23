import stripe
from subhub.cfg import CFG
import os
import boto3
from subhub.secrets import get_secret
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)



SUBHUB_TABLE = os.environ.get('SUBHUB_TABLE')
IS_DEPLOYED = os.environ.get("AWS_EXECUTION_ENV")
if IS_DEPLOYED is None:
    logger.info(f'table {SUBHUB_TABLE}')
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
    resp = client.get_item(
        TableName=SUBHUB_TABLE,
        Key={
            'userId': {'S': uid}
        }
    )
    subscription_user = resp.get('Item')
    if subscription_user:
        if 'subscriptions' in subscription_user:
            if data['plan_id'] == subscription_user['subscriptions']:
                logger.info(f'already subscribed')
                return {"message": "User has current subscription.", "code": 400}, 400
    else:
        resp = client.put_item(
            TableName=SUBHUB_TABLE,
            Item={
                'userId': {'S': uid},
            }
        )
        subscription_user = resp

    if 'custId' not in subscription_user:
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
        resp = client.get_item(
            TableName=SUBHUB_TABLE,
            Key={
                'userId': {'S': uid}
            }
        )
        updated_customer = stripe.Customer.retrieve(customer['id'])
        item = resp['Item']
        item['custId'] = {'S': customer['id']}
        item['orig_system'] = {'S': data['orig_system']}
        endedVal = 'None'
        if subscription['ended_at']:
            endedVal = str(subscription['ended_at'])
        item['subscriptions'] = {'L': [{'M': {'subscription_id': {'S': subscription['id']},
                          'current_period_end': {'S': str(subscription['current_period_end'])},
                          'current_period_start': {'S': str(subscription['current_period_start'])},
                          'plan_id': {'S': subscription['plan']['id']},
                          'ended_at': {'S': endedVal},
                          'orig_system': {'S': data['orig_system']},
                          'status': {'S': subscription['status']},
                          'nickname': {'S': subscription['plan']['nickname']}}}]}

        client.put_item(TableName=SUBHUB_TABLE, Item=item)
        products = []
        for prod in subscription["items"]["data"]:
            products.append(prod["plan"]["product"])
        return_data = {}
        return_data['subscriptions'] = []
        for subscription in updated_customer["subscriptions"]["data"]:
            endedVal = 'None'
            if subscription['ended_at']:
                endedVal = str(subscription['ended_at'])
            return_data['subscriptions'].append({
                'current_period_end': subscription['current_period_end'],
                'current_period_start': subscription['current_period_start'],
                'ended_at': subscription['ended_at'],
                'nickname': subscription['plan']['nickname'],
                'plan_id': subscription['plan']['id'],
                'status': subscription['status'],
                'subscription_id': subscription['id']})
        return return_data, 201
    else:
        resp = client.get_item(
            TableName=SUBHUB_TABLE,
            Key={
                'userId': {'S': uid}
            }
        )
        items = resp['Item']
        for item in items['subscriptions']['L']:
            if item["M"]["plan_id"]["S"] == data["plan_id"] and item["M"]["status"]["S"] in ['active', 'trialing']:
                return 'User has existing plan', 400
        subscription = subscribe_customer(subscription_user['custId']['S'], data['plan_id'])
        if 'Missing required param' in subscription:
            return 'Missing parameter ', 400
        elif 'No such plan' in subscription:
            return 'Plan not valid', 400

        updated_customer = stripe.Customer.retrieve(subscription_user['custId']['S'])
        updated_subscriptions = []
        return_data = {}
        return_data['subscriptions'] = []
        for subscription in updated_customer["subscriptions"]["data"]:
            endedVal = 'None'
            if subscription['ended_at']:
                endedVal = str(subscription['ended_at'])
            item = {'M': {'subscription_id': {'S': subscription['id']},
                          'current_period_end': {'S': str(subscription['current_period_end'])},
                          'current_period_start': {'S': str(subscription['current_period_start'])},
                          'plan_id': {'S': subscription['plan']['id']},
                          'ended_at': {'S': endedVal},
                          'orig_system': {'S': data['orig_system']},
                          'status': {'S': subscription['status']},
                          'nickname': {'S': subscription['plan']['nickname']}}}
            updated_subscriptions.append(item)
            return_data['subscriptions'].append({
                'current_period_end': subscription['current_period_end'],
                'current_period_start': subscription['current_period_start'],
                'ended_at': subscription['ended_at'],
                'nickname': subscription['plan']['nickname'],
                'plan_id': subscription['plan']['id'],
                'status': subscription['status'],
                'subscription_id': subscription['id']})
        items['subscriptions'] = {'L': updated_subscriptions}
        client.put_item(TableName=SUBHUB_TABLE, Item=items)
        return return_data, 201


def list_all_plans():
    plans = stripe.Plan.list(limit=100)
    stripe_plans = []
    for p in plans:
        stripe_plans.append({'plan_id': p['id'], 'product_id': p['product'], 'interval': p['interval'], 'amount': p['amount'], 'currency': p['currency']})
    return stripe_plans, 200


def cancel_subscription(uid, sub_id):
    if not isinstance(uid, str):
        return 'Invalid ID', 400
    if not isinstance(sub_id, str):
        return 'Invalid Subscription ', 400
    # TODO Remove payment source on cancel
    resp = client.get_item(
        TableName=SUBHUB_TABLE,
        Key={
            'userId': {'S': uid}
        }
    )
    subscription_user = resp.get('Item')
    subscriptions = []
    for suser in subscription_user['subscriptions']['L']:
        subscriptions.append(suser['M']['subscription_id']['S'])
    if sub_id in subscriptions:
        try:
            tocancel = stripe.Subscription.retrieve(sub_id)
        except stripe.error.InvalidRequestError as e:
            return str(e)
        if 'No such subscription:' in tocancel:
            return 'Invalid subscription.', 400
        if tocancel['status'] in ['active', 'trialing']:
            tocancel.delete()
            cancelled = stripe.Subscription.retrieve(sub_id)
            return tocancel, 201
        else:
            return 'Error cancelling subscription', 400
    else:
        return 'Subscription not available.', 400


def subscription_status(uid):
    if not isinstance(uid, str):
        return 'Invalid ID', 400
    resp = client.get_item(
        TableName=SUBHUB_TABLE,
        Key={
            'userId': {'S': uid}
        }
    )
    items = resp.get('Item')
    if items is None:
        return 'Customer does not exist.', 404
    subscriptions = stripe.Subscription.list(customer=items['custId']['S'], limit=100, status='all')
    if subscriptions is None:
        return 'No subscriptions for this customer.', 404
    updated_subscriptions = []
    return_data = {}
    return_data['subscriptions'] = []
    for subscription in subscriptions["data"]:
        endedVal = 'None'
        if subscription['ended_at']:
            endedVal = str(subscription['ended_at'])
        item = {'M': {'subscription_id': {'S': subscription['id']},
                      'current_period_end': {'S': str(subscription['current_period_end'])},
                      'current_period_start': {'S': str(subscription['current_period_start'])},
                      'plan_id': {'S': subscription['plan']['id']},
                      'ended_at': {'S': endedVal},
                      'status': {'S': subscription['status']},
                      'nickname': {'S': subscription['plan']['nickname']}}}
        updated_subscriptions.append(item)
        return_data['subscriptions'].append({
            'current_period_end': subscription['current_period_end'],
            'current_period_start': subscription['current_period_start'],
            'ended_at': subscription['ended_at'],
            'nickname': subscription['plan']['nickname'],
            'plan_id': subscription['plan']['id'],
            'status': subscription['status'],
            'subscription_id': subscription['id']})
    items['subscriptions'] = {'L': updated_subscriptions}
    client.put_item(TableName=SUBHUB_TABLE, Item=items)
    return return_data, 201



def update_payment_method(uid, data):
    if not isinstance(data['pmt_token'], str):
        return 'Missing token', 400
    if not isinstance(uid, str):
        return 'Missing or invalid user.', 400
    resp = client.get_item(
        TableName=SUBHUB_TABLE,
        Key={
            'userId': {'S': uid}
        }
    )
    items = resp.get('Item')
    if items is None:
        return 'Customer does not exist.', 404
    try:
        customer = stripe.Customer.retrieve(items['custId']['S'])
        if customer['metadata']['fxuid'] == uid:
            try:
                updated_customer = customer.modify(items['custId']['S'], source=data['pmt_token'])
                return 'Payment method updated successfully.', 201
            except stripe.error.InvalidRequestError as e:
                return str(e), 400
        else:
            return 'Customer mismatch.', 400
    except KeyError as e:
        return f'Customer does not exist: missing {e}', 404


def customer_update(uid):
    logger.info(f'customer update {uid}')
    if not isinstance(uid, str):
        return 'Invalid ID', 400
    resp = client.get_item(
        TableName=SUBHUB_TABLE,
        Key={
            'userId': {'S': uid}
        }
    )
    items = resp.get('Item')
    if items is None:
        return 'Customer does not exist.', 404
    try:
        customer = stripe.Customer.retrieve(items['custId']['S'])
        if customer['metadata']['fxuid'] == uid:
            return_data = {}
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
            return return_data, 200
        else:
            return 'Customer mismatch.', 400
    except KeyError as e:
        return f'Customer does not exist: missing {e}', 404


def remove_from_db(uid):
    client.delete_item(
        TableName=SUBHUB_TABLE,
        Key={
            'userId': {'S': uid}
        }
    )
    # create a response
    response = {
        "statusCode": 200
    }
    return response

