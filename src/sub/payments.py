# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import cachetools

from datetime import datetime
from typing import List, Dict, Any, Optional
from stripe import Customer, Product
from flask import g

from sub.shared import vendor, universal
from sub.shared.types import JsonDict, FlaskResponse, FlaskListResponse
from sub.shared.universal import format_plan_nickname
from sub.customer import existing_or_new_customer, has_existing_plan, fetch_customer
from sub.shared.db import SubHubDeletedAccount
from sub.shared.log import get_logger

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
        vendor.build_stripe_subscription(
            customer.id, data["plan_id"], universal.get_indempotency_key()
        )
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
    plans = vendor.retrieve_plan_list(100)
    logger.info("number of plans", count=len(plans))
    stripe_plans = []
    products = {}  # type: Dict
    for plan in plans:
        try:
            product = products[plan["product"]]
        except KeyError:
            product = vendor.retrieve_stripe_product(plan["product"])
            products[plan["product"]] = product

        plan_name = format_plan_nickname(
            product_name=product["name"], plan_interval=plan["interval"]
        )

        stripe_plans.append(
            {
                "plan_id": plan["id"],
                "product_id": plan["product"],
                "interval": plan["interval"],
                "amount": plan["amount"],
                "currency": plan["currency"],
                "plan_name": plan_name,
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
            vendor.cancel_stripe_subscription_period_end(
                sub_id, universal.get_indempotency_key()
            )
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

    deleted_payment_customer = vendor.delete_stripe_customer(subscription_user.cust_id)
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
                vendor.cancel_stripe_subscription_period_end(
                    sub_id, universal.get_indempotency_key()
                )
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

    subscriptions = vendor.list_customer_subscriptions(items.cust_id)
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
    return_data: Dict[str, Any] = {}
    return_data["subscriptions"] = []

    products = {}  # type: Dict
    for subscription in subscriptions["data"]:
        try:
            product = products[subscription["plan"]["product"]]
        except KeyError:
            product = vendor.retrieve_stripe_product(subscription["plan"]["product"])
            products[subscription["plan"]["product"]] = product

        plan_name = format_plan_nickname(
            product_name=product["name"], plan_interval=subscription["plan"]["interval"]
        )

        if subscription["status"] == "incomplete":
            invoice = vendor.retrieve_stripe_invoice(subscription["latest_invoice"])
            if invoice["charge"]:
                intents = vendor.retrieve_stripe_customer(invoice["charge"])
                logger.debug("intents", intents=intents)

                return_data["subscriptions"].append(
                    {
                        "current_period_end": subscription["current_period_end"],
                        "current_period_start": subscription["current_period_start"],
                        "ended_at": subscription["ended_at"],
                        "plan_name": plan_name,
                        "plan_id": subscription["plan"]["id"],
                        "status": subscription["status"],
                        "subscription_id": subscription["id"],
                        "cancel_at_period_end": subscription["cancel_at_period_end"],
                        "failure_code": intents["failure_code"],
                        "failure_message": intents["failure_message"],
                    }
                )
                continue

        return_data["subscriptions"].append(
            create_subscription_object_without_failure(subscription, plan_name)
        )
    return return_data


def create_subscription_object_without_failure(
    subscription: Dict[str, Any], plan_name: str
) -> Dict[str, Any]:
    return {
        "current_period_end": subscription["current_period_end"],
        "current_period_start": subscription["current_period_start"],
        "ended_at": subscription["ended_at"],
        "plan_name": plan_name,
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
    logger.info("customer", customer=customer)
    if not customer:
        return dict(message="Customer does not exist."), 404

    metadata = customer.get("metadata")
    logger.info("metadata", metadata=metadata, customer=type(customer))
    if metadata:
        if metadata["userid"] == uid:
            vendor.modify_customer(
                customer_id=customer.id,
                source_token=data["pmt_token"],
                idempotency_key=universal.get_indempotency_key(),
            )
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

    return_data["payment_type"] = ""
    return_data["last4"] = ""
    return_data["exp_month"] = ""
    return_data["exp_year"] = ""

    if len(payment_sources) > 0:
        first_payment_source = payment_sources[0]
        return_data["payment_type"] = first_payment_source.get("funding")
        return_data["last4"] = first_payment_source.get("last4")
        return_data["exp_month"] = first_payment_source.get("exp_month")
        return_data["exp_year"] = first_payment_source.get("exp_year")

    products = {}  # type: Dict
    for subscription in customer["subscriptions"]["data"]:
        try:
            product = products[subscription["plan"]["product"]]
        except KeyError:
            product = vendor.retrieve_stripe_product(subscription["plan"]["product"])
            products[subscription["plan"]["product"]] = product

        plan_name = format_plan_nickname(
            product_name=product["name"], plan_interval=subscription["plan"]["interval"]
        )

        if subscription["status"] == "incomplete":
            invoice = vendor.retrieve_stripe_invoice(subscription["latest_invoice"])
            if invoice["charge"]:
                intents = vendor.retrieve_stripe_customer(invoice["charge"])
                return_data["subscriptions"].append(
                    {
                        "current_period_end": subscription["current_period_end"],
                        "current_period_start": subscription["current_period_start"],
                        "ended_at": subscription["ended_at"],
                        "plan_name": plan_name,
                        "plan_id": subscription["plan"]["id"],
                        "status": subscription["status"],
                        "cancel_at_period_end": subscription["cancel_at_period_end"],
                        "subscription_id": subscription["id"],
                        "failure_code": intents["failure_code"],
                        "failure_message": intents["failure_message"],
                    }
                )
                continue

        return_data["cancel_at_period_end"] = subscription["cancel_at_period_end"]
        return_data["subscriptions"].append(
            create_subscription_object_without_failure(subscription, plan_name)
        )

    return return_data
