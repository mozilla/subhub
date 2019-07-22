#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Customer functions"""
from stripe import Customer, Subscription
import stripe
from stripe.error import InvalidRequestError

from subhub.cfg import CFG
from subhub.exceptions import IntermittentError, ServerError
from subhub.subhub_dynamodb import SubHubAccount
from subhub.log import get_logger

logger = get_logger()


def create_customer(
    subhub_account: SubHubAccount,
    user_id: str,
    email: str,
    source_token: str,
    origin_system: str,
    display_name: str,
) -> Customer:
    _validate_origin_system(origin_system)
    # First search Stripe to ensure we don't have an unlinked Stripe record
    # already in Stripe
    customer = None
    customers = Customer.list(email=email)
    for possible_customer in customers.data:
        if possible_customer.email == email:
            # If the userid doesn't match, the system is damaged.
            if possible_customer.metadata.get("userid") != user_id:
                raise ServerError("customer email exists but userid mismatch")

            customer = possible_customer
            # If we have a mis-match on the source_token, overwrite with the
            # new one.
            if customer.default_source != source_token:
                Customer.modify(customer.id, source=source_token)
            break

    # No existing Stripe customer, create one.
    if not customer:
        try:
            customer = Customer.create(
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
        Customer.delete(customer.id)
        e = IntermittentError("error saving db record")
        logger.error("unable to save user or link it", error=e)
        raise e
    return customer


def existing_or_new_customer(
    subhub_account: SubHubAccount,
    user_id: str,
    email: str,
    source_token: str,
    origin_system: str,
    display_name: str,
) -> Customer:
    _validate_origin_system(origin_system)
    customer = fetch_customer(subhub_account, user_id)
    if not customer:
        return create_customer(
            subhub_account, user_id, email, source_token, origin_system, display_name
        )
    return existing_payment_source(customer, source_token)


def fetch_customer(subhub_account: SubHubAccount, user_id: str) -> Customer:
    customer = None
    db_account = subhub_account.get_user(user_id)
    if db_account:
        customer = Customer.retrieve(db_account.cust_id)
        if "deleted" in customer and customer["deleted"]:
            subhub_account.remove_from_db(user_id)
            customer = None
    return customer


def existing_payment_source(existing_customer: Customer, source_token: str) -> Customer:
    if not existing_customer.get("sources"):
        if not existing_customer.get("deleted"):
            existing_customer = Customer.modify(
                existing_customer["id"], source=source_token
            )
            logger.info("add source", existing_customer=existing_customer)
        else:
            logger.info("existing source deleted")
    return existing_customer


def subscribe_customer(customer: Customer, plan_id: str) -> Subscription:
    """
    Subscribe Customer to Plan
    :param customer:
    :param plan:
    :return: Subscription Object
    """
    try:
        sub = Subscription.create(customer=customer, items=[{"plan": plan_id}])
        return sub
    except Exception as e:
        logger.error("sub error", error=e)
        raise InvalidRequestError("Unable to create plan", param=plan_id)


def has_existing_plan(customer: Customer, plan_id: str) -> bool:
    """
    Check if user has the existing plan in an active or trialing state.
    :param customer:
    :param plan_id:
    :return: True if user has existing plan, otherwise False
    """
    if customer.get("subscriptions"):
        for item in customer["subscriptions"]["data"]:
            if item["plan"]["id"] == plan_id and item["status"] in [
                "active",
                "trialing",
            ]:
                return True
    return False


def _validate_origin_system(origin_system: str):
    """
    This function validates a request's origin_system to validate that is permitted.  This
    allows us to ensure that callers are permitted by configuration to interact with this application.
    :param origin_system: The originating system in Mozilla
    """
    if origin_system not in CFG.ALLOWED_ORIGIN_SYSTEMS:
        msg = f"origin_system={origin_system} not one of allowed origin system values, please contact a system administrator in the #subscription-platform channel."
        raise InvalidRequestError(message=msg, param=str(origin_system))
