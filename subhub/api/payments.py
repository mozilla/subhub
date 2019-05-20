import logging
from typing import Any, Dict, List, Tuple

import stripe
from stripe.error import (
    InvalidRequestError,
    APIConnectionError,
    APIError,
    AuthenticationError,
    CardError,
)
from flask import g

from subhub.customer import existing_or_new_customer, has_existing_plan

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# API types
JsonDict = Dict[str, Any]
FlaskResponse = Tuple[JsonDict, int]
FlaskListResponse = Tuple[List[JsonDict], int]


def subscribe_to_plan(uid, data) -> FlaskResponse:
    """
    Subscribe to a plan given a user id, payment token, email, orig_system
    :param uid:
    :param data:
    :return: current subscriptions for user.
    """
    try:
        customer = existing_or_new_customer(
            g.subhub_account,
            user_id=uid,
            email=data["email"],
            source_token=data["pmt_token"],
            origin_system=data["orig_system"],
        )
    except InvalidRequestError as e:
        return {"message": f"Unable to subscribe. {e}"}, 400
    existing_plan = has_existing_plan(customer, plan_id=data["plan_id"])
    if existing_plan:
        return {"message": "User already subscribed."}, 409
    if existing_plan:
        return {"message": "User already subscribed."}, 409
    try:
        stripe.Subscription.create(
            customer=customer.id, items=[{"plan": data["plan_id"]}]
        )
    except InvalidRequestError as e:
        return {"message": f"Unable to subscribe. {e}"}, 400
    updated_customer = stripe.Customer.retrieve(customer.id)
    return create_return_data(updated_customer["subscriptions"]), 201


def list_all_plans() -> FlaskListResponse:
    """
    List all available plans for a user to purchase.
    :return:
    """
    plans = stripe.Plan.list(limit=100)
    stripe_plans = []
    for plan in plans:
        product = stripe.Product.retrieve(plan["product"])
        stripe_plans.append(
            {
                "plan_id": plan["id"],
                "product_id": plan["product"],
                "interval": plan["interval"],
                "amount": plan["amount"],
                "currency": plan["currency"],
                "plan_name": plan["nickname"],
                "product_name": product["name"],
            }
        )
    return stripe_plans, 200


def cancel_subscription(uid, sub_id) -> FlaskResponse:
    """
    Cancel an existing subscription for a user.
    :param uid:
    :param sub_id:
    :return: Success or failure message for the cancellation.
    """
    # TODO Remove payment source on cancel
    subscription_user = g.subhub_account.get_user(uid)
    if not subscription_user:
        return {"message": "Customer does not exist."}, 404
    customer = stripe.Customer.retrieve(subscription_user.custId)
    for item in customer["subscriptions"]["data"]:
        if item["id"] == sub_id and item["status"] in [
            "active",
            "trialing",
            "incomplete",
        ]:
            try:
                tocancel = stripe.Subscription.retrieve(sub_id)
                cancel = stripe.Subscription.modify(sub_id, cancel_at_period_end=True)
                return {"message": "Subscription cancellation successful"}, 201
            except (
                InvalidRequestError,
                APIConnectionError,
                APIError,
                AuthenticationError,
                CardError,
            ) as e:
                return {"message": f"Unable to cancel subscription: {e}"}, 400
        else:
            return {"message": "Subscription not available."}, 400


def support_status(uid) -> FlaskResponse:
    return subscription_status(uid)


def subscription_status(uid) -> FlaskResponse:
    """
    Given a user id return the current subscription status
    :param uid:
    :return: Current subscriptions
    """
    items = g.subhub_account.get_user(uid)
    if not items or not items.custId:
        return {"message": "Customer does not exist."}, 404
    subscriptions = stripe.Subscription.list(
        customer=items.custId, limit=100, status="all"
    )
    if not subscriptions:
        return {"message": "No subscriptions for this customer."}, 403
    return_data = create_return_data(subscriptions)
    return return_data, 201


def create_return_data(subscriptions) -> JsonDict:
    """
    Create json object subscriptions object
    :param subscriptions:
    :return: JSON data to be consumed by client.
    """
    return_data = dict()
    return_data["subscriptions"] = []
    for subscription in subscriptions["data"]:
        if subscription["status"] == "incomplete":
            invoice = stripe.Invoice.retrieve(subscription["latest_invoice"])
            intents = stripe.Charge.retrieve(invoice["charge"])
            return_data["subscriptions"].append(
                {
                    "current_period_end": subscription["current_period_end"],
                    "current_period_start": subscription["current_period_start"],
                    "ended_at": subscription["ended_at"],
                    "nickname": subscription["plan"]["nickname"],
                    "plan_id": subscription["plan"]["id"],
                    "status": subscription["status"],
                    "subscription_id": subscription["id"],
                    "cancel_at_period_end": subscription["cancel_at_period_end"],
                    "failure_code": intents["failure_code"],
                    "failure_message": intents["failure_message"],
                }
            )
        else:
            return_data["subscriptions"].append(
                {
                    "current_period_end": subscription["current_period_end"],
                    "current_period_start": subscription["current_period_start"],
                    "ended_at": subscription["ended_at"],
                    "nickname": subscription["plan"]["nickname"],
                    "plan_id": subscription["plan"]["id"],
                    "status": subscription["status"],
                    "subscription_id": subscription["id"],
                    "cancel_at_period_end": subscription["cancel_at_period_end"],
                }
            )
    return return_data


def update_payment_method(uid, data) -> FlaskResponse:
    """
    Given a user id and a payment token, update user's payment method
    :param uid:
    :param data:
    :return: Success or failure message.
    """
    items = g.subhub_account.get_user(uid)
    if not items or not items.custId:
        return {"message": "Customer does not exist."}, 404
    try:
        customer = stripe.Customer.retrieve(items.custId)
        if customer["metadata"]["userid"] == uid:
            try:
                customer.modify(items.custId, source=data["pmt_token"])
                return {"message": "Payment method updated successfully."}, 201
            except (
                InvalidRequestError,
                APIConnectionError,
                APIError,
                AuthenticationError,
                CardError,
            ) as e:

                return {"message": f"{e}"}, 400
        else:
            return "Customer mismatch.", 400
    except KeyError as e:
        return f"Customer does not exist: missing {e}", 404


def customer_update(uid) -> tuple:
    """
    Provide latest data for a given user
    :param uid:
    :return: return_data dict with credit card info and subscriptions
    """
    items = g.subhub_account.get_user(uid)
    if not items or not items.custId:
        return "Customer does not exist.", 404
    try:
        customer = stripe.Customer.retrieve(items.custId)
        if customer["metadata"]["userid"] == uid:
            return_data = create_update_data(customer)
            return return_data, 200
        else:
            return "Customer mismatch.", 400
    except KeyError as e:
        return {"message": f"Customer does not exist: missing {e}"}, 404


def create_update_data(customer) -> dict:
    """
    Provide readable data for customer update to display
    :param customer:
    :return: return_data dict
    """
    return_data = dict()
    return_data["subscriptions"] = []
    return_data["payment_type"] = customer["sources"]["data"][0]["funding"]
    return_data["last4"] = customer["sources"]["data"][0]["last4"]
    return_data["exp_month"] = customer["sources"]["data"][0]["exp_month"]
    return_data["exp_year"] = customer["sources"]["data"][0]["exp_year"]
    for subscription in customer["subscriptions"]["data"]:
        if subscription["status"] == "incomplete":
            invoice = stripe.Invoice.retrieve(subscription["latest_invoice"])
            intents = stripe.Charge.retrieve(invoice["charge"])
            return_data["subscriptions"].append(
                {
                    "current_period_end": subscription["current_period_end"],
                    "current_period_start": subscription["current_period_start"],
                    "ended_at": subscription["ended_at"],
                    "nickname": subscription["plan"]["nickname"],
                    "plan_id": subscription["plan"]["id"],
                    "status": subscription["status"],
                    "subscription_id": subscription["id"],
                    "failure_code": intents["failure_code"],
                    "failure_message": intents["failure_message"],
                }
            )
        else:
            return_data["subscriptions"].append(
                {
                    "current_period_end": subscription["current_period_end"],
                    "current_period_start": subscription["current_period_start"],
                    "ended_at": subscription["ended_at"],
                    "nickname": subscription["plan"]["nickname"],
                    "plan_id": subscription["plan"]["id"],
                    "status": subscription["status"],
                    "subscription_id": subscription["id"],
                }
            )
    return return_data
