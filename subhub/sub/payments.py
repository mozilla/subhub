# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from datetime import datetime
from typing import List, Dict, Any, Optional

import cachetools
from stripe import Charge, Customer, Invoice, Plan, Product, Subscription
from flask import g

from subhub.sub.types import JsonDict, FlaskResponse, FlaskListResponse
from subhub.customer import existing_or_new_customer, has_existing_plan, fetch_customer
from subhub.log import get_logger
from subhub.db import SubHubDeletedAccount

logger = get_logger()


def subscribe_to_plan(uid: str, data: Dict[str, Any]) -> FlaskResponse:
    """
    Subscribe to a plan given a user id, payment token, email, orig_system
    :param uid:
    :param data:
    :return: current subscriptions for user.
    """
    customer = existing_or_new_customer(
        g.subhub_account,
        user_id=uid,
        email=data["email"],
        source_token=data["pmt_token"],
        origin_system=data["origin_system"],
        display_name=data["display_name"],
    )
    existing_plan = has_existing_plan(customer, plan_id=data["plan_id"])
    if existing_plan:
        return dict(message="User already subscribed."), 409

    if not customer.get("deleted"):
        Subscription.create(customer=customer.id, items=[{"plan": data["plan_id"]}])
        updated_customer = fetch_customer(g.subhub_account, user_id=uid)
        newest_subscription = find_newest_subscription(
            updated_customer["subscriptions"]
        )
        return create_return_data(newest_subscription), 201

    return dict(message=None), 400


def find_newest_subscription(subscriptions: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    result = None

    if not subscriptions:
        return result

    for subscription in subscriptions["data"]:
        if not subscription:
            continue
        if not result:
            result = subscription
            continue

        if subscription["status"] == "active":
            current_period_start = datetime.fromtimestamp(
                int(subscription["current_period_start"])
            )
            result_current_period_start = datetime.fromtimestamp(
                int(result["current_period_start"])
            )
            if result_current_period_start < current_period_start:
                result = subscription

    return {"data": [result]}


def list_all_plans() -> FlaskListResponse:
    """
    List all available plans for a user to purchase.
    :return:
    """
    return _get_all_plans(), 200


@cachetools.cached(cachetools.TTLCache(10, 600))
def _get_all_plans() -> List[Dict[str, str]]:
    plans = Plan.list(limit=100)
    logger.info("number of plans", count=len(plans))
    stripe_plans = []
    for plan in plans:
        product = Product.retrieve(plan["product"])
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
    return stripe_plans


def retrieve_stripe_subscriptions(customer: Customer) -> List[Dict[str, Any]]:
    logger.info("customer", customer=customer)
    try:
        customer_subscriptions_data = customer.subscriptions
        customer_subscriptions = customer_subscriptions_data.get("data")
        return customer_subscriptions
    except AttributeError as e:
        logger.error("error getting subscriptions", customer=customer, error=e)
        raise e


def cancel_subscription(uid: str, sub_id: str) -> FlaskResponse:
    """
    Cancel an existing subscription for a user.
    :param uid:
    :param sub_id:
    :return: Success or failure message for the cancellation.
    """
    customer = fetch_customer(g.subhub_account, uid)
    if not customer:
        return dict(message="Customer does not exist."), 404

    for item in customer["subscriptions"]["data"]:
        if item["id"] == sub_id and item["status"] in [
            "active",
            "trialing",
            "incomplete",
        ]:
            Subscription.modify(sub_id, cancel_at_period_end=True)
            updated_customer = fetch_customer(g.subhub_account, uid)
            logger.info("updated customer", updated_customer=updated_customer)
            subs = retrieve_stripe_subscriptions(updated_customer)
            logger.info("subs", subs=subs, type=type(subs))
            for sub in subs:
                if sub["cancel_at_period_end"] and sub["id"] == sub_id:
                    return {"message": "Subscription cancellation successful"}, 201

    return dict(message="Subscription not available."), 400


def delete_customer(uid: str) -> FlaskResponse:
    """
    Delete an existing customer, cancel active subscriptions
    and delete from payment provider
    :param uid:
    :return: Success of failure message for the deletion
    """
    subscription_user = g.subhub_account.get_user(uid)
    if not subscription_user:
        return dict(message="Customer does not exist."), 404

    deleted_payment_customer = Customer.delete(subscription_user.cust_id)
    if deleted_payment_customer:
        deleted_customer = delete_user(
            user_id=subscription_user.user_id,
            cust_id=subscription_user.cust_id,
            origin_system=subscription_user.origin_system,
        )
        user = g.subhub_account.get_user(uid)
        if deleted_customer and user is None:
            return dict(message="Customer deleted successfully"), 200

    return dict(message="Customer not available"), 400


def delete_user(user_id: str, cust_id: str, origin_system: str) -> bool:
    """
    Provided with customer data to be deleted
    - created deleted entry in the deleted table
    - remove the customer from the active table
    :param user_id:
    :param cust_id:
    :param origin_system:
    :return:
    """
    deleted_user = add_user_to_deleted_users_record(
        user_id=user_id, cust_id=cust_id, origin_system=origin_system
    )
    if not deleted_user:
        return False
    return g.subhub_account.remove_from_db(user_id)


def add_user_to_deleted_users_record(
    user_id: str, cust_id: Optional[str], origin_system: str
) -> Optional[Any]:
    return g.subhub_deleted_users.new_user(
        uid=user_id, cust_id=cust_id, origin_system=origin_system
    )


def reactivate_subscription(uid: str, sub_id: str) -> FlaskResponse:
    """
    Given a user's subscription that is flagged for cancellation, but is still active
    remove the cancellation flag to ensure the subscription remains active
    :param uid: User ID
    :param sub_id: Subscription ID
    :return: Success or failure message for the activation
    """

    customer = fetch_customer(g.subhub_account, uid)
    if not customer:
        return dict(message="Customer does not exist."), 404

    active_subscriptions = customer["subscriptions"]["data"]
    for subscription in active_subscriptions:
        if subscription["id"] == sub_id:
            if subscription["cancel_at_period_end"]:
                Subscription.modify(sub_id, cancel_at_period_end=False)
                return dict(message="Subscription reactivation was successful."), 200
            return dict(message="Subscription is already active."), 200

    return dict(message="Current subscription not found."), 404


def support_status(uid: str) -> FlaskResponse:
    return subscription_status(uid)


def subscription_status(uid: str) -> FlaskResponse:
    """
    Given a user id return the current subscription status
    :param uid:
    :return: Current subscriptions
    """
    items = g.subhub_account.get_user(uid)
    if not items or not items.cust_id:
        return dict(message="Customer does not exist."), 404

    subscriptions = Subscription.list(customer=items.cust_id, limit=100, status="all")
    if not subscriptions:
        return dict(message="No subscriptions for this customer."), 403

    return_data = create_return_data(subscriptions)
    return return_data, 200


def create_return_data(subscriptions) -> JsonDict:
    """
    Create json object subscriptions object
    :param subscriptions:
    :return: JSON data to be consumed by client.
    """
    return_data: Dict[str, Any] = dict()
    return_data["subscriptions"] = []
    for subscription in subscriptions["data"]:
        if subscription["status"] == "incomplete":
            invoice = Invoice.retrieve(subscription["latest_invoice"])
            if invoice["charge"]:
                intents = Charge.retrieve(invoice["charge"])
                logger.debug("intents", intents=intents)
                return_data["subscriptions"].append(
                    {
                        "current_period_end": subscription["current_period_end"],
                        "current_period_start": subscription["current_period_start"],
                        "ended_at": subscription["ended_at"],
                        "plan_name": subscription["plan"]["nickname"],
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
                    create_subscription_object_without_failure(subscription)
                )
        else:
            return_data["subscriptions"].append(
                create_subscription_object_without_failure(subscription)
            )
    return return_data


def create_subscription_object_without_failure(
    subscription: Dict[str, Any]
) -> Dict[str, Any]:
    return {
        "current_period_end": subscription["current_period_end"],
        "current_period_start": subscription["current_period_start"],
        "ended_at": subscription["ended_at"],
        "plan_name": subscription["plan"]["nickname"],
        "plan_id": subscription["plan"]["id"],
        "status": subscription["status"],
        "subscription_id": subscription["id"],
        "cancel_at_period_end": subscription["cancel_at_period_end"],
    }


def update_payment_method(uid, data) -> FlaskResponse:
    """
    Given a user id and a payment token, update user's payment method
    :param uid:
    :param data:
    :return: Success or failure message.
    """
    customer = fetch_customer(g.subhub_account, uid)
    if not customer:
        return dict(message="Customer does not exist."), 404

    if customer["metadata"]["userid"] == uid:
        customer.modify(customer.id, source=data["pmt_token"])
        return {"message": "Payment method updated successfully."}, 201

    return dict(message="Customer mismatch."), 400


def customer_update(uid) -> tuple:
    """
    Provide latest data for a given user
    :param uid:
    :return: return_data dict with credit card info and subscriptions
    """
    try:
        customer = fetch_customer(g.subhub_account, uid)
        if not customer:
            return dict(message="Customer does not exist."), 404

        if customer["metadata"]["userid"] == uid:
            return_data = create_update_data(customer)
            return return_data, 200

        return dict(message="Customer mismatch."), 400
    except KeyError as e:
        logger.error("Customer does not exist", error=e)
        return dict(message=f"Customer does not exist: missing {e}"), 404


def create_update_data(customer) -> Dict[str, Any]:
    """
    Provide readable data for customer update to display
    :param customer:
    :return: return_data dict
    """
    payment_sources = customer["sources"]["data"]
    return_data: Dict[str, Any] = dict()
    return_data["subscriptions"] = []
    if len(payment_sources) > 0:
        first_payment_source = payment_sources[0]
        return_data["payment_type"] = first_payment_source.get("funding")
        return_data["last4"] = first_payment_source.get("last4")
        return_data["exp_month"] = first_payment_source.get("exp_month")
        return_data["exp_year"] = first_payment_source.get("exp_year")
    else:
        return_data["payment_type"] = ""
        return_data["last4"] = ""
        return_data["exp_month"] = ""
        return_data["exp_year"] = ""

    for subscription in customer["subscriptions"]["data"]:
        if subscription["status"] == "incomplete":
            invoice = Invoice.retrieve(subscription["latest_invoice"])
            if invoice["charge"]:
                intents = Charge.retrieve(invoice["charge"])
                return_data["subscriptions"].append(
                    {
                        "current_period_end": subscription["current_period_end"],
                        "current_period_start": subscription["current_period_start"],
                        "ended_at": subscription["ended_at"],
                        "plan_name": subscription["plan"]["nickname"],
                        "plan_id": subscription["plan"]["id"],
                        "status": subscription["status"],
                        "cancel_at_period_end": subscription["cancel_at_period_end"],
                        "subscription_id": subscription["id"],
                        "failure_code": intents["failure_code"],
                        "failure_message": intents["failure_message"],
                    }
                )
            else:
                return_data["cancel_at_period_end"] = subscription[
                    "cancel_at_period_end"
                ]
                return_data["subscriptions"].append(
                    create_subscription_object_without_failure(subscription)
                )
        else:
            return_data["cancel_at_period_end"] = subscription["cancel_at_period_end"]
            return_data["subscriptions"].append(
                create_subscription_object_without_failure(subscription)
            )

    return return_data
