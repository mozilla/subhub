# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import cachetools
import time
import json

from datetime import datetime
from typing import List, Dict, Any, Optional
from stripe import Customer, Product, Plan
from stripe.error import InvalidRequestError
from stripe.util import convert_to_dict
from flask import g

from sub.shared.vendor import (
    modify_customer,
    build_stripe_subscription,
    update_stripe_subscription,
    retrieve_plan_list,
    retrieve_stripe_product,
    cancel_stripe_subscription_period_end,
    retrieve_stripe_customer,
    cancel_stripe_subscription_immediately,
    delete_stripe_customer,
    reactivate_stripe_subscription,
    list_customer_subscriptions,
    retrieve_stripe_product,
    retrieve_stripe_invoice,
    retrieve_stripe_charge,
    retrieve_stripe_product,
    retrieve_stripe_invoice,
    retrieve_stripe_plan,
)
from sub.shared import utils
from sub.shared.exceptions import ValidationError, EntityNotFoundError
from sub.shared.types import JsonDict, FlaskResponse, FlaskListResponse
from sub.shared.utils import format_plan_nickname
from sub.customer import (
    existing_or_new_customer,
    has_existing_plan,
    fetch_customer,
    find_customer,
    find_customer_subscription,
)
from sub.shared.db import SubHubDeletedAccount
from sub.messages import Message
from sub.shared.cfg import CFG
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
    valid_country = check_customer_country(customer)
    if not valid_country:
        return dict(message="Country not supported."), 400
    existing_plan = has_existing_plan(customer, plan_id=data["plan_id"])
    if existing_plan:
        logger.debug("subscribe to plan", existing_plan=existing_plan)
        return dict(message="User already subscribed."), 409
    if "deleted" not in customer:
        sub = build_stripe_subscription(
            customer.id, data["plan_id"], utils.get_indempotency_key()
        )
        updated_customer = fetch_customer(g.subhub_account, user_id=uid)
        newest_subscription = find_newest_subscription(
            updated_customer["subscriptions"]
        )
        return create_return_data(newest_subscription), 201

    return dict(message=None), 400


def check_customer_country(check_cust: Dict[str, Any]) -> bool:
    customer_sources = check_cust.get("sources", None)
    if customer_sources:
        source_data = customer_sources.get("data", None)
        if source_data:
            first_source = source_data[0].get("country", None)
            if first_source:
                if first_source in CFG.SUPPORTED_COUNTRIES:
                    return True
    return False


def find_newest_subscription(subscriptions: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    result = None
    if not subscriptions:
        return None
    for subscription in subscriptions["data"]:
        if not result:
            result = subscription
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
    plans = retrieve_plan_list(100)
    logger.debug("number of plans", count=len(plans))
    stripe_plans = []
    products = {}  # type: Dict
    for plan in plans:
        try:
            product = products[plan["product"]]
        except KeyError:
            product = retrieve_stripe_product(plan["product"])
            products[plan["product"]] = product

        stripe_plans.append(format_plan(plan, product))
    return stripe_plans


def format_plan(plan: Dict[str, Any], product: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format a Stripe Plan for response
    :param plan:
    :param product:
    :return:
    """
    plan_name = format_plan_nickname(
        product_name=product["name"], plan_interval=plan["interval"]
    )

    return {
        "plan_id": plan["id"],
        "product_id": product["id"],
        "interval": plan["interval"],
        "amount": plan["amount"],
        "currency": plan["currency"],
        "plan_name": plan_name,
        "product_name": product["name"],
        "plan_metadata": plan["metadata"],
        "product_metadata": product["metadata"],
    }


def retrieve_stripe_subscriptions(customer: Customer) -> List[Dict[str, Any]]:
    try:
        customer_subscriptions_data = customer.subscriptions
        customer_subscriptions = customer_subscriptions_data.get("data")
        return customer_subscriptions
    except AttributeError as e:
        logger.error("error getting subscriptions", customer=customer, error=e)
        raise e


def update_subscription(uid: str, sub_id: str, data: Dict[str, Any]) -> FlaskResponse:
    """
    Update a Customer's Subscription with a new Plan
    Locate a Stripe Customer from the provided uid and locate the Customer's subscription from the provided sub_id
        - If the Customer is not found, or the Customer object does not contain a Subscription with the sub_id
            :return 404 Not Found
    Determine if the new plan_id can replace the current Subscription Plan:
        - If the new plan_id and current plan_id are the same
            : return 400 Bad Request
        - If the new plan and the old plan have different intervals:
            : return 400 Bad Request
        - If the products do not have the same ProductSet metadata
            :return 400 Bad Request
    Make call to Stripe to update the Subscription
        :return 200 OK - Updated Subscription in response body

    :param uid:
    :param sub_id:
    :param data:
    :return:
    """
    customer = find_customer(g.subhub_account, uid)
    subscription = find_customer_subscription(customer, sub_id)

    current_plan = subscription["plan"]
    new_plan_id = data["plan_id"]

    new_product = validate_plan_change(current_plan, new_plan_id)

    updated_subscription = update_stripe_subscription(
        subscription, new_plan_id, utils.get_indempotency_key()
    )

    formatted_subscription = format_subscription(
        convert_to_dict(updated_subscription), new_product
    )

    return formatted_subscription, 200


def validate_plan_change(current_plan: Dict[str, Any], new_plan_id: str) -> Product:
    """
    Validate that a new plan qualifies to replace a current plan. Return the new Product
    :param current_plan:
    :param new_plan_id:
    :return:
    """
    if current_plan["id"] == new_plan_id:
        raise ValidationError(message="The plans are the same", error_number=1003)

    new_plan = find_stripe_plan(new_plan_id)
    if (
        current_plan["interval"] != new_plan["interval"]
        or current_plan["interval_count"] != new_plan["interval_count"]
    ):
        raise ValidationError(
            message="The plans do not have the same interval", error_number=1002
        )

    new_product = find_stripe_product(new_plan["product"])
    if current_plan["product"] != new_plan["product"]:
        old_product = find_stripe_product(current_plan["product"])
        old_product_set = old_product.metadata.get("productSet", None)
        new_product_set = new_product.metadata.get("productSet", None)
        if old_product_set != new_product_set or old_product_set is None:
            raise ValidationError(
                message="The plans are not a part of a tiered relationship",
                error_number=1001,
            )

    return new_product


def find_stripe_plan(plan_id: str) -> Plan:
    """
    Find the Stripe Plan by ID
    :raise EntityNotFoundError
    :param plan_id:
    :return:
    """
    try:
        plan = retrieve_stripe_plan(plan_id)
        return plan
    except InvalidRequestError as e:
        if e.http_status == 404:
            raise EntityNotFoundError(message="Plan not found", error_number=4003)
        raise e


def find_stripe_product(product_id: str) -> Product:
    """
    Find the Stripe Product by ID
    :raise EntityNotFoundError
    :param plan_id:
    :return:
    """
    try:
        product = retrieve_stripe_product(product_id)
        return product
    except InvalidRequestError as e:
        if e.http_status == 404:
            raise EntityNotFoundError(message="Product not found", error_number=4002)
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
            cancel_stripe_subscription_period_end(sub_id, utils.get_indempotency_key())
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
    if subscription_user is None:
        return dict(message="Customer does not exist"), 404
    else:
        origin = subscription_user.origin_system
        logger.debug("delete origin", origin=origin)
        subscribed_customer = retrieve_stripe_customer(subscription_user.cust_id)
        subscribed_customer = subscribed_customer.to_dict()
        subscription_info: List = []
        logger.debug(
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
            cancel_stripe_subscription_immediately(
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
            logger.debug("delete customer", sns_message=sns_message)
        else:
            deleted_payment_customer = delete_stripe_customer(subscription_user.cust_id)
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
    logger.debug(
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
                reactivate_stripe_subscription(sub_id, utils.get_indempotency_key())
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

    subscriptions = list_customer_subscriptions(items.cust_id)
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
    formatted_subscriptions = format_subscriptions_data(subscriptions["data"])
    return_data = {"subscriptions": formatted_subscriptions}
    logger.debug("create return data", return_data=return_data)
    return return_data


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
        if metadata.get("userid", None) == uid:
            modify_customer(
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
    customer = fetch_customer(g.subhub_account, uid)
    if not customer:
        response_message = dict(message="Customer does not exist.")
        logger.debug(
            "customer update", response_message=response_message, response_code=404
        )
        return response_message, 404
    metadata = customer.get("metadata", None)
    if metadata:
        if metadata.get("userid", None) == uid:
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

    return_data["subscriptions"] = format_subscriptions_data(
        customer["subscriptions"]["data"]
    )
    logger.debug("create update data", return_data=return_data)
    return return_data


def format_subscriptions_data(
    subscription_data: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Prepare Subscription Data for response
    :param subscription_data:
    :return:
    """
    products = {}  # type: Dict
    subscriptions = []
    for subscription in subscription_data:
        try:
            product = products[subscription["plan"]["product"]]
        except KeyError:
            product = retrieve_stripe_product(subscription["plan"]["product"])
            products[subscription["plan"]["product"]] = product

        intents = None
        if subscription.get("status", None) == "incomplete":
            invoice = retrieve_stripe_invoice(subscription["latest_invoice"])
            if invoice["charge"]:
                intents = retrieve_stripe_charge(invoice["charge"])
                intents = convert_to_dict(intents)

        subscriptions.append(format_subscription(subscription, product, intents))

    return subscriptions


def format_subscription(
    subscription: Dict[str, Any],
    product: Dict[str, Any],
    failed_charge: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Format a single Subscription
    :param subscription:
    :param product:
    :param failed_charge:
    :return:
    """
    plan_name = format_plan_nickname(
        product_name=product["name"], plan_interval=subscription["plan"]["interval"]
    )

    subscription = {
        "current_period_end": subscription["current_period_end"],
        "current_period_start": subscription["current_period_start"],
        "ended_at": subscription["ended_at"],
        "plan_name": plan_name,
        "plan_id": subscription["plan"]["id"],
        "product_metadata": product["metadata"],
        "plan_metadata": subscription["plan"]["metadata"],
        "status": subscription["status"],
        "subscription_id": subscription["id"],
        "cancel_at_period_end": subscription["cancel_at_period_end"],
    }

    if failed_charge is not None:
        subscription["failure_code"] = failed_charge["failure_code"]
        subscription["failure_message"] = failed_charge["failure_message"]

    return subscription
