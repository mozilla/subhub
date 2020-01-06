# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import time

from typing import List, Optional, Dict, Any
from tenacity import retry, wait_exponential, stop_after_attempt
from stripe import Customer, Subscription, Charge, Invoice, Plan, Product, api_key
from stripe.error import (
    InvalidRequestError,
    APIConnectionError,
    APIError,
    CardError,
    RateLimitError,
    IdempotencyError,
    StripeErrorWithParamCode,
    AuthenticationError,
)

from shared.log import get_logger

logger = get_logger()


# begin Customer calls
@retry(
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(4),
    reraise=True,
)
def get_customer_list(email: str) -> Optional[List[Customer]]:
    try:
        customer_list = Customer.list(email=email)
        logger.debug("get customer list", customer_list=customer_list)
        return customer_list
    except (
        APIConnectionError,
        APIError,
        RateLimitError,
        StripeErrorWithParamCode,
    ) as e:
        logger.error("get customer list error", error=e)
        raise e


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(4),
    reraise=True,
)
def modify_customer(
    customer_id: str, source_token: str, idempotency_key: str
) -> Customer:
    """
    Update customer source
    :param customer_id:
    :param source_token:
    :param idempotency_key:
    :return: updated Customer
    """
    try:
        customer = Customer.modify(
            customer_id, source=source_token, idempotency_key=idempotency_key
        )
        logger.debug("modify customer", customer=customer)
        return customer
    except (
        InvalidRequestError,
        APIConnectionError,
        APIError,
        RateLimitError,
        IdempotencyError,
        CardError,
        StripeErrorWithParamCode,
    ) as e:
        logger.error("modify customer token", error=e)
        raise e


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(4),
    reraise=True,
)
def create_stripe_customer(
    source_token: str, email: str, userid: str, name: str, idempotency_key: str
) -> Customer:
    """
    Create a new Stripe Customer.
    :param source_token:
    :param email:
    :param userid:
    :param name:
    :param idempotency_key:
    :return: Customer
    """
    try:
        customer = Customer.create(
            source=source_token,
            email=email,
            description=userid,
            name=name,
            metadata={"userid": userid},
            idempotency_key=idempotency_key,
        )
        logger.debug("create stripe customer", customer=customer)
        return customer
    except (
        InvalidRequestError,
        APIConnectionError,
        APIError,
        RateLimitError,
        IdempotencyError,
        CardError,
        StripeErrorWithParamCode,
    ) as e:
        logger.error("create customer error", error=e)
        raise e


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(4),
    reraise=True,
)
def delete_stripe_customer(customer_id: str) -> Dict[str, Any]:
    """
    Delete a Stripe customer
    :param customer_id:
    :return: object
    """
    try:
        deleted_customer = Customer.delete(sid=customer_id)
        logger.debug("delete stripe customer", deleted_customer=deleted_customer)
        return deleted_customer
    except (
        InvalidRequestError,
        APIConnectionError,
        APIError,
        RateLimitError,
        StripeErrorWithParamCode,
    ) as e:
        logger.error("delete customer error", error=e)
        raise e


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(4),
    reraise=True,
)
def retrieve_stripe_customer(customer_id: str) -> Optional[Customer]:
    """
    Retrieve Stripe Customer
    :param customer_id:
    :return: Customer
    """
    try:
        customer = Customer.retrieve(id=customer_id)
        logger.debug("retrieve stripe customer", customer=customer)
        return customer
    except (
        InvalidRequestError,
        APIConnectionError,
        APIError,
        RateLimitError,
        StripeErrorWithParamCode,
    ) as e:
        logger.error("retrieve stripe customer error", error=e)
        raise e


# end Customer calls


# begin Subscription calls
@retry(
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(4),
    reraise=True,
)
def build_stripe_subscription(
    customer_id: str, plan_id: str, idempotency_key: str
) -> Subscription:
    """
    Create a new Stripe subscription for a given customer
    :param customer_id:
    :param plan_id:
    :param idempotency_key:
    :return: Subscription object
    """
    try:
        sub = Subscription.create(
            customer=customer_id,
            items=[{"plan": plan_id}],
            idempotency_key=idempotency_key,
        )
        logger.debug("build stripe subscription", sub=sub)
        return sub
    except (
        InvalidRequestError,
        APIConnectionError,
        APIError,
        RateLimitError,
        IdempotencyError,
        StripeErrorWithParamCode,
        AuthenticationError,
    ) as e:
        logger.error("sub error", error=e)
        raise e


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(4),
    reraise=True,
)
def update_stripe_subscription(
    subscription: Dict[str, Any], plan_id: str, idempotency_key: str
) -> Subscription:
    """
    Update a stripe subscription to a new plan
    :param customer_id:
    :param plan_id:
    :param idempotency_key:
    :return: Subscription object
    """
    try:
        subscription = Subscription.modify(
            subscription["id"],
            cancel_at_period_end=False,
            items=[{"id": subscription["items"]["data"][0]["id"], "plan": plan_id}],
            metadata={
                "previous_plan_id": subscription["plan"]["id"],
                "plan_change_date": int(time.time()),
            },
            idempotency_key=idempotency_key,
        )

        logger.debug("update stripe subscription", sub=subscription)
        return subscription
    except (
        InvalidRequestError,
        APIConnectionError,
        APIError,
        RateLimitError,
        IdempotencyError,
        StripeErrorWithParamCode,
        AuthenticationError,
    ) as e:
        logger.error("sub error", error=e)
        raise e


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(4),
    reraise=True,
)
def cancel_stripe_subscription_period_end(
    subscription_id: str, idempotency_key: str
) -> Subscription:
    """
    Set Stripe subscription to cancel at period end
    :param subscription_id:
    :param idempotency_key:
    :return: Subscription
    """
    try:
        sub = Subscription.modify(
            sid=subscription_id,
            cancel_at_period_end=True,
            idempotency_key=idempotency_key,
        )
        logger.debug("cancel stripe subscription", sub=sub)
        return sub
    except (
        InvalidRequestError,
        APIConnectionError,
        APIError,
        RateLimitError,
        IdempotencyError,
        StripeErrorWithParamCode,
    ) as e:
        logger.error("cancel sub error", error=str(e))
        raise e


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(4),
    reraise=True,
)
def cancel_stripe_subscription_immediately(
    subscription_id: str, idempotency_key: str
) -> Subscription:
    """
    Set Stripe subscription to cancel at period end
    :param subscription_id:
    :param idempotency_key:
    :return: Subscription
    """
    try:
        sub = Subscription.delete(sid=subscription_id, idempotency_key=idempotency_key)
        logger.debug("cancel stripe subscription immediately", sub=sub)
        return sub
    except (
        InvalidRequestError,
        APIConnectionError,
        APIError,
        RateLimitError,
        IdempotencyError,
        StripeErrorWithParamCode,
    ) as e:
        logger.error("cancel sub error", error=str(e))
        raise e


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(4),
    reraise=True,
)
def reactivate_stripe_subscription(
    subscription_id: str, idempotency_key: str
) -> Subscription:
    """
    Set Stripe subscription to cancel at period end
    :param subscription_id:
    :param idempotency_key:
    :return: Subscription
    """
    try:
        sub = Subscription.modify(
            sid=subscription_id,
            cancel_at_period_end=False,
            idempotency_key=idempotency_key,
        )
        logger.debug("reactivate stripe subscription", sub=sub)
        return sub
    except (
        InvalidRequestError,
        APIConnectionError,
        APIError,
        RateLimitError,
        IdempotencyError,
        StripeErrorWithParamCode,
    ) as e:
        logger.error("reactivate sub error", error=str(e))
        raise e


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(4),
    reraise=True,
)
def list_customer_subscriptions(cust_id: str) -> List[Subscription]:
    """
    List customer subscriptions
    :param cust_id:
    :return: List of Subscriptions
    """
    try:
        subscriptions = Subscription.list(customer=cust_id, limit=100, status="all")
        logger.debug("list customer subscriptions", subscriptions=subscriptions)
        return subscriptions
    except (
        InvalidRequestError,
        APIConnectionError,
        APIError,
        RateLimitError,
        IdempotencyError,
        StripeErrorWithParamCode,
    ) as e:
        logger.error("list subscriptions error", error=e)
        raise e


# end Subscription calls


# start Charge calls
@retry(
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(4),
    reraise=True,
)
def retrieve_stripe_charge(charge_id: str) -> Charge:
    """
    Retrive Stripe Charge
    :param charge_id:
    :return: Charge
    """
    if charge_id is None:
        logger.error(
            "hub::shared::vendor::retrieve_stripe_charge received a None charge_id, ignoring."
        )
        return None
    else:
        try:
            charge = Charge.retrieve(charge_id)
            logger.debug("retrieve stripe charge", charge=charge)
            return charge
        except (
            InvalidRequestError,
            APIConnectionError,
            APIError,
            RateLimitError,
            IdempotencyError,
            StripeErrorWithParamCode,
        ) as e:
            logger.error("retrieve stripe error", error=str(e))
            raise e


# end Charge calls


# start Invoice calls
@retry(
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(4),
    reraise=True,
)
def retrieve_stripe_invoice(invoice_id: str) -> Invoice:
    """
    Retrieve Stripe Invoice
    :param invoice_id:
    :return: Invoice
    """
    try:
        invoice = Invoice.retrieve(invoice_id)
        logger.debug("retrieve stripe invoice", invoice=invoice)
        return invoice
    except (
        InvalidRequestError,
        APIConnectionError,
        APIError,
        RateLimitError,
        IdempotencyError,
        StripeErrorWithParamCode,
    ) as e:
        logger.error("retrieve invoice error", error=str(e))
        raise e


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(4),
    reraise=True,
)
def retrieve_stripe_invoice_upcoming_by_subscription(
    customer_id: str, subscription_id: str
) -> Invoice:
    """
    Retrieve the next invoice for a customer that will be for a specific subscription
    :param customer_id:
    :param subscription_id:
    :return:
    """
    try:
        invoice = Invoice.upcoming(customer=customer_id, subscription=subscription_id)
        logger.debug("retrieve stripe invoice upcoming", invoice=invoice)
        return invoice
    except (
        InvalidRequestError,
        APIConnectionError,
        APIError,
        RateLimitError,
        IdempotencyError,
        StripeErrorWithParamCode,
    ) as e:
        logger.error("retrieve stripe invoice upcoming error", error=str(e))
        raise e


def retrieve_stripe_invoice_upcoming(customer: str) -> Invoice:
    """
    Retrieve an upcoming stripe invoice
    :param customer:
    :return:
    """
    try:
        invoice = Invoice.upcoming(customer=customer)
        logger.debug("retrieve stripe invoice upcoming", invoice=invoice)
        return invoice
    except (
        InvalidRequestError,
        APIConnectionError,
        APIError,
        RateLimitError,
        IdempotencyError,
        StripeErrorWithParamCode,
    ) as e:
        logger.error("retrieve stripe invoice upcoming error", error=str(e))
        raise e


# end Invoice calls

# start Plan calls
@retry(
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(4),
    reraise=True,
)
def retrieve_plan_list(limit: int) -> List[Plan]:
    """
    Retrieve Stripe Plan list
    :param limit:
    :return: List of Plans
    """
    try:
        plans = Plan.list(limit=limit)
        return plans
    except (
        InvalidRequestError,
        APIConnectionError,
        APIError,
        RateLimitError,
        IdempotencyError,
        StripeErrorWithParamCode,
    ) as e:
        logger.error("retrieve plan list error", error=str(e))
        raise e


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(4),
    reraise=True,
)
def retrieve_stripe_plan(plan_id: str) -> Plan:
    """
    Retrieve Stripe Plan
    :param plan_id:
    :return:
    """
    try:
        plan = Plan.retrieve(plan_id)
        logger.debug("retrieve stripe plan", plan=plan)
        return plan
    except (
        InvalidRequestError,
        APIConnectionError,
        APIError,
        RateLimitError,
        IdempotencyError,
        StripeErrorWithParamCode,
    ) as e:
        logger.error("retrieve plan error", error=str(e))
        raise e


# end Plan calls


# start Product calls
@retry(
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(4),
    reraise=True,
)
def retrieve_stripe_product(product_id: str) -> Product:
    """
    Retrieve Stripe Product
    :param product_id:
    :return: Product
    """
    try:
        product = Product.retrieve(product_id)
        logger.debug("retrieve stripe product", product=product)
        return product
    except (
        InvalidRequestError,
        APIConnectionError,
        APIError,
        RateLimitError,
        IdempotencyError,
        StripeErrorWithParamCode,
    ) as e:
        logger.error("retrieve product error", error=str(e))
        raise e


# end Product calls
