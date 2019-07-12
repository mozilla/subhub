"""Customer functions"""
import stripe

from subhub.exceptions import IntermittentError, ServerError
from stripe.error import InvalidRequestError
from subhub.subhub_dynamodb import SubHubAccount
from subhub.log import get_logger
from subhub.tracing import timed

logger = get_logger()


@timed
def create_customer(
    subhub_account: SubHubAccount,
    user_id: str,
    email: str,
    source_token: str,
    origin_system: str,
    display_name: str,
) -> stripe.Customer:
    # First search Stripe to ensure we don't have an unlinked Stripe record
    # already in Stripe
    customer = None
    customers = stripe.Customer.list(email=email)
    for possible_customer in customers.data:
        if possible_customer.email == email:
            # If the userid doesn't match, the system is damaged.
            if possible_customer.metadata.get("userid") != user_id:
                raise ServerError("customer email exists but userid mismatch")

            customer = possible_customer
            # If we have a mis-match on the source_token, overwrite with the
            # new one.
            if customer.default_source != source_token:
                stripe.Customer.modify(customer.id, source=source_token)
            break

    # No existing Stripe customer, create one.
    if not customer:
        try:
            customer = stripe.Customer.create(
                source=source_token,
                email=email,
                description=user_id,
                name=display_name,
                metadata={"userid": user_id},
            )

        except InvalidRequestError as e:
            logger.error("create customer error", error=e)
            raise InvalidRequestError(
                message="Unable to create customer.", param=str(e)
            )
    # Link the Stripe customer to the origin system id
    db_account = subhub_account.new_user(
        uid=user_id, origin_system=origin_system, cust_id=customer.id
    )

    if not subhub_account.save_user(db_account):
        # Clean-up the Stripe customer record since we can't link it
        stripe.Customer.delete(customer.id)
        e = IntermittentError("error saving db record")
        logger.error("unable to save user or link it", error=e)
        raise e
    return customer


@timed
def existing_or_new_customer(
    subhub_accouunt: SubHubAccount,
    user_id: str,
    email: str,
    source_token: str,
    origin_system: str,
    display_name: str,
) -> stripe.Customer:
    db_account = subhub_accouunt.get_user(user_id)
    if not db_account:
        return create_customer(
            subhub_accouunt, user_id, email, source_token, origin_system, display_name
        )
    customer_id = db_account.cust_id
    return existing_payment_source(customer_id, source_token)


@timed
def existing_payment_source(customer_id: str, source_token: str) -> stripe.Customer:
    existing_customer = stripe.Customer.retrieve(customer_id)
    if not existing_customer["sources"]["data"]:
        existing_customer = stripe.Customer.modify(customer_id, source=source_token)
        logger.info(f"add source {existing_customer}")
    return existing_customer


@timed
def subscribe_customer(customer: stripe.Customer, plan_id: str) -> stripe.Subscription:
    """
    Subscribe Customer to Plan
    :param customer:
    :param plan:
    :return: Subscription Object
    """
    return stripe.Subscription.create(customer=customer, items=[{"plan": plan_id}])


@timed
def has_existing_plan(user: stripe.Customer, plan_id: str) -> bool:
    """
    Check if user has the existing plan in an active or trialing state.
    :param user:
    :param plan_id:
    :return: True if user has existing plan, otherwise False
    """
    customer = stripe.Customer.retrieve(user.id)
    for item in customer["subscriptions"]["data"]:
        if item["plan"]["id"] == plan_id and item["status"] in ["active", "trialing"]:
            return True
    return False
