# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import cachetools
import time
import json

from datetime import datetime
from typing import List, Dict, Any, Optional
from stripe import Customer, Product
from flask import g

from sub.shared import vendor, utils
from sub.shared.types import JsonDict, FlaskResponse, FlaskListResponse
from sub.shared.utils import format_plan_nickname
from sub.customer import existing_or_new_customer, has_existing_plan, fetch_customer
from sub.shared.db import SubHubDeletedAccount
from sub.messages import Message
from shared.log import get_logger

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
        logger.debug("subscribe to plan", existing_plan=existing_plan)
        return dict(message="User already subscribed."), 409

    if not customer.get("deleted"):
        vendor.build_stripe_subscription(
            customer.id, data["plan_id"], utils.get_indempotency_key()
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
    logger.debug("find newest subscription", result=result)
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
        logger.debug("cancel subscription customer does not exist")
        return dict(message="Customer does not exist."), 404

    for item in customer["subscriptions"]["data"]:
        if item["id"] == sub_id and item["status"] in [
            "active",
            "trialing",
            "incomplete",
        ]:
            vendor.cancel_stripe_subscription_period_end(
                sub_id, utils.get_indempotency_key()
            )
            updated_customer = fetch_customer(g.subhub_account, uid)
            logger.debug("updated customer", updated_customer=updated_customer)
            subs = retrieve_stripe_subscriptions(updated_customer)
            logger.debug("retrieved subs", subs=subs, type=type(subs))
            for sub in subs:
                if sub["cancel_at_period_end"] and sub["id"] == sub_id:
                    response_message = dict(
                        message="Subscription cancellation successful"
                    )
                    logger.debug(
                        "cancel subscription response",
                        response_message=response_message,
                        response_code=201,
                    )
                    return response_message, 201

    return dict(message="Subscription not available."), 400


def delete_customer(uid: str) -> FlaskResponse:
    """
    Delete an existing customer, cancel active subscriptions
    and delete from payment provider
    :param uid:
    :return: Success of failure message for the deletion
    """
    logger.debug("delete customer", uid=uid)
    subscription_user = g.subhub_account.get_user(uid)
    logger.debug("delete customer", subscription_user=subscription_user)
    if subscription_user is not None:
        origin = subscription_user.origin_system
        logger.debug("delete origin", origin=origin)
        if not subscription_user:
            return dict(message="Customer does not exist."), 404
        subscribed_customer = vendor.retrieve_stripe_customer(subscription_user.cust_id)
        subscribed_customer = subscribed_customer.to_dict()
        subscription_info: List = []
        logger.info(
            "subscribed customer",
            subscribed_customer=subscribed_customer,
            data_type=type(subscribed_customer),
        )

        products = {}  # type: Dict
        for subs in subscribed_customer["subscriptions"]["data"]:
            try:
                product = products[subs.plan.product]
            except KeyError:
                product = Product.retrieve(subs.plan.product)
                products[subs.plan.product] = product
            plan_id = subs.plan.product

            sub = dict(
                plan_amount=subs.plan.amount,
                nickname=format_plan_nickname(subs.plan.nickname, subs.plan.interval),
                productId=plan_id,
                current_period_end=subs.current_period_end,
                current_period_start=subs.current_period_start,
                subscription_id=subs.id,
            )
            subscription_info.append(sub)
            vendor.cancel_stripe_subscription_immediately(
                subs.id, utils.get_indempotency_key()
            )
            data = dict(
                uid=subscribed_customer["metadata"]["userid"],
                active=False,
                subscriptionId=subs.id,
                productId=plan_id,
                eventId=utils.get_indempotency_key(),
                eventCreatedAt=int(time.time()),
                messageCreatedAt=int(time.time()),
            )
            sns_message = Message(json.dumps(data)).route()
            logger.info("delete message", sns_message=sns_message)
        else:
            deleted_payment_customer = vendor.delete_stripe_customer(
                subscription_user.cust_id
            )
            if deleted_payment_customer:
                deleted_customer = delete_user(
                    user_id=subscribed_customer["metadata"]["userid"],
                    cust_id=subscribed_customer["id"],
                    origin_system=origin,
                    subscription_info=subscription_info,
                )
                user = g.subhub_account.get_user(uid)
                if deleted_customer and user is None:
                    logger.debug(
                        "delete customer successful", deleted_customer=deleted_customer
                    )
                    return dict(message="Customer deleted successfully"), 200
    return dict(message="Customer not available"), 400


def delete_user(
    user_id: str,
    cust_id: str,
    origin_system: str,
    subscription_info: List[Dict[str, Any]],
) -> bool:
    """
    Provided with customer data to be deleted
    - created deleted entry in the deleted table
    - remove the customer from the active table
    :param user_id:
    :param cust_id:
    :param origin_system:
    :param subscription_info:
    :return:
    """
    logger.info(
        "delete user",
        user_id=user_id,
        cust_id=cust_id,
        origin_system=origin_system,
        subscription_info=subscription_info,
    )
    deleted_user = add_user_to_deleted_users_record(
        user_id=user_id,
        cust_id=cust_id,
        origin_system=origin_system,
        subscription_info=subscription_info,
    )
    new_deleted_user = g.subhub_deleted_users.save_user(deleted_user)
    if not new_deleted_user:
        return False
    return g.subhub_account.remove_from_db(user_id)


def add_user_to_deleted_users_record(
    user_id: str,
    cust_id: Optional[str],
    origin_system: str,
    subscription_info: List[Dict[str, Any]],
) -> Optional[Any]:
    return g.subhub_deleted_users.new_user(
        uid=user_id,
        cust_id=cust_id,
        origin_system=origin_system,
        subscription_info=subscription_info,
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
        response_message = dict(message="Customer does not exist.")
        logger.debug("reactivate subscription", response_message=response_message)
        return response_message, 404

    active_subscriptions = customer["subscriptions"]["data"]
    response_message = dict(message="Current subscription not found.")
    for subscription in active_subscriptions:
        if subscription["id"] == sub_id:
            response_message = dict(message="Subscription is already active.")
            if subscription["cancel_at_period_end"]:
                vendor.reactivate_stripe_subscription(
                    sub_id, utils.get_indempotency_key()
                )
                response_message = dict(
                    message="Subscription reactivation was successful."
                )
                logger.debug(
                    "reactivate subscription",
                    response_message=response_message,
                    response_code=200,
                )
                return response_message, 200
            logger.debug(
                "reactivate subscription",
                response_message=response_message,
                response_code=200,
            )
            return response_message, 200
    logger.debug(
        "reactivate subscription", response_message=response_message, response_code=404
    )
    return response_message, 404


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
        response_message = dict(message="Customer does not exist.")
        logger.debug(
            "subscription status", response_message=response_message, response_code=404
        )
        return response_message, 404

    subscriptions = vendor.list_customer_subscriptions(items.cust_id)
    if not subscriptions:
        response_message = dict(message="No subscriptions for this customer.")
        logger.debug(
            "subscription status", response_message=response_message, response_code=403
        )
        return response_message, 403

    return_data = create_return_data(subscriptions)
    logger.debug("subscription status", return_data=return_data)
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
                intents = vendor.retrieve_stripe_charge(invoice["charge"])
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
    logger.debug("create return data", return_data=return_data)
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
    logger.debug("customer", customer=customer)
    if not customer:
        response_message = dict(message="Customer does not exist.")
        logger.debug(
            "update payment method",
            response_message=response_message,
            response_code=404,
        )
        return response_message, 404

    metadata = customer.get("metadata")
    logger.debug("metadata", metadata=metadata, customer=type(customer))
    if metadata:
        if metadata["userid"] == uid:
            vendor.modify_customer(
                customer_id=customer.id,
                source_token=data["pmt_token"],
                idempotency_key=utils.get_indempotency_key(),
            )
            response_message = dict(message="Payment method updated successfully.")
            logger.debug(
                "update payment method",
                response_message=response_message,
                response_code=201,
            )
            return response_message, 201
    response_message = dict(message="Customer mismatch.")
    logger.debug(
        "update payment method", response_message=response_message, response_code=400
    )
    return response_message, 400


def customer_update(uid) -> tuple:
    """
    Provide latest data for a given user
    :param uid:
    :return: return_data dict with credit card info and subscriptions
    """
    try:
        customer = fetch_customer(g.subhub_account, uid)
        if not customer:
            response_message = dict(message="Customer does not exist.")
            logger.debug(
                "customer update", response_message=response_message, response_code=404
            )
            return response_message, 404

        if customer["metadata"]["userid"] == uid:
            return_data = create_update_data(customer)
            logger.debug(
                "customer update", response_message=return_data, response_code=200
            )
            return return_data, 200
        response_message = dict(message="Customer mismatch.")
        logger.debug(
            "customer update", response_message=response_message, response_code=400
        )
        return response_message, 400
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
                intents = vendor.retrieve_stripe_invoice(invoice["charge"])
                intents = intents.to_dict()
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
    logger.debug("create update data", return_data=return_data)
    return return_data
