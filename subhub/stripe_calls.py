import stripe
import settings

stripe.api_key = settings.STRIPE_API_KEY
premium_customers = [
    {'fxa': 'mcb12345', 'cust_id': None, 'subscriptions': []}
]

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


def subscribe_to_plan(api_token, fxa, pmt_token, plan_id, email):
    valid_token = api_validation(api_token)
    if not valid_token:
        return 'Missing token ', 400
    firefox_user = next(f for f in premium_customers if fxa == f['fxa'])
    # print(f'firefox_user {len(firefox_user)}')
    if firefox_user['cust_id'] is None:
        customer = create_customer(pmt_token, fxa, email)
        # print(f'new customer {customer}')
        subscription = subscribe_customer(customer, plan_id)
        for f in premium_customers:
            if f['fxa'] == fxa:
                f['cust_id'] = customer['id']
                f['subscriptions'].append(subscription)
        # print(f'premium_customers {premium_customers}')
        return subscription, 201
    else:
        subscription = subscribe_customer(firefox_user['cust_id'], plan_id)
        return subscription, 201


def list_all_plans(api_token):
    valid_token = api_validation(api_token)
    if not valid_token:
        return 'Missing token ', 400
    plans = stripe.Plan.list(limit=100)
    return plans, 200

def cancel_subscription(api_token, subscription_id, customer_id):
    valid_token = api_validation(api_token)
    if not valid_token:
        return 'Missing token ', 400
    tocancel = stripe.Subscription.retrieve(subscription_id)
    print(f'tocancel {tocancel["customer"]}')
    if tocancel['customer'] == customer_id:
        tocancel.delete()
        return tocancel, 201
    else:
        return 'Error cancelling subscription', 400

def subscription_status(api_token, fxa, customer_id):
    valid_token = api_validation(api_token)
    if not valid_token:
        return 'Missing token ', 400
    subscriptions = stripe.Subscription.list(customer=customer_id, limit=100)
    if subscriptions is None:
        return 'Bad data', 400
    return subscriptions, 201

def update_payment_method(api_token, fxa, pmt_token, cust_id):
    valid_token = api_validation(api_token)
    if not valid_token:
        return 'Missing token ', 400
    customer = stripe.Customer.retrieve(cust_id)
    if customer['metadata']['fxuid'] == fxa:
        updated_customer = customer.modify(cust_id, source=pmt_token)
        return updated_customer, 201
    else:
        return 'Customer mismatch.', 400


def fxa_customer_update(api_token, fxa, cust_id):
    pass

def api_validation(api_token):
    if api_token is None:
        return False
    elif isinstance(api_token, int):
        return False
    else:
        return True
