"""Customer functions"""
import stripe

from subhub.exceptions import IntermittentError, ServerError
from subhub.subhub_dynamodb import SubHubAccount


def create_customer(subhub_account: SubHubAccount, user_id: str, email: str,
                    source_token: str,
                    origin_system: str) -> stripe.Customer:
    # First search Stripe to ensure we don't have an unlinked Stripe record
    # already in Stripe
    customer = None
    customers = stripe.Customer.list(email=email)
    for possible_customer in customers.data:
        if possible_customer.email == email:
            # If the userid doesn't match, the system is damaged.
            if possible_customer.metadata.get('userid') != user_id:
                raise ServerError("customer email exists but userid mismatch")

            customer = possible_customer
            # If we have a mis-match on the source_token, overwrite with the
            # new one.
            if customer.default_source != source_token:
                stripe.Customer.modify(
                    customer.id,
                    source=source_token,
                )
            break

    # No existing Stripe customer, create one.
    if not customer:
        customer = stripe.Customer.create(
            source=source_token,
            email=email,
            description=user_id,
            metadata={'userid': user_id}
        )

    # Link the Stripe customer to the origin system id
    db_account = subhub_account.new_user(uid=user_id,
                                         origin_system=origin_system,
                                         custId=customer.id,
                                         )

    if not subhub_account.save_user(db_account):
        # Clean-up the Stripe customer record since we can't link it
        stripe.Customer.delete(customer.id)
        raise IntermittentError("error saving db record")
    return customer


def existing_or_new_customer(subhub_accouunt: SubHubAccount,
                             user_id: str, email: str, source_token: str,
                             origin_system: str) -> stripe.Customer:
    db_account = subhub_accouunt.get_user(user_id)
    if not db_account:
        return create_customer(subhub_accouunt, user_id, email, source_token,
                               origin_system)

    customer_id = db_account.custId
    return stripe.Customer.retrieve(customer_id)


def subscribe_customer(customer: stripe.Customer,
                       plan_id: str) -> stripe.Subscription:
    """
    Subscribe Customer to Plan
    :param customer:
    :param plan:
    :return: Subscription Object
    """
    return stripe.Subscription.create(
        customer=customer,
        items=[{
            "plan": plan_id,
        },
        ]
    )


def has_existing_plan(user: stripe.Customer, plan_id: str) -> bool:
    """
    Check if user has the existing plan in an active or trialing state.
    :param user:
    :param plan_id:
    :return: True if user has existing plan, otherwise False
    """
    customer = stripe.Customer.retrieve(user.id)
    for item in customer['subscriptions']['data']:
        if item["plan"]["id"] == plan_id and item['status'] in ['active', 'trialing']:
            return True
    return False
