import logging
from datetime import datetime
import stripe
from flask import g

from subhub.api.types import JsonDict, FlaskResponse, FlaskListResponse
from subhub.customer import existing_or_new_customer, has_existing_plan
from subhub.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def subscribe_to_plan(uid, data) -> FlaskResponse:
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
        origin_system=data["orig_system"],
    )
    existing_plan = has_existing_plan(customer, plan_id=data["plan_id"])
    if existing_plan:
        return {"message": "User already subscribed."}, 409
    stripe.Subscription.create(customer=customer.id, items=[{"plan": data["plan_id"]}])
    updated_customer = stripe.Customer.retrieve(customer.id)
    newest_subscription = find_newest_subscription(updated_customer["subscriptions"])
    return create_return_data(newest_subscription), 201


def find_newest_subscription(subscriptions):
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


def check_stripe_subscriptions(customer: str) -> list:
    customer_info = stripe.Customer.retrieve(id=customer)
    logger.debug(f"cust info {customer_info.subscriptions}")
    try:
        customer_subscriptions_data = customer_info.subscriptions
        customer_subscriptions = customer_subscriptions_data.get("data")
        sources_to_remove(customer_subscriptions, customer)
        return customer_subscriptions
    except NameError as e:
        logger.debug(f"check_stripe_subscriptions: {e}")
        return []


def sources_to_remove(subscriptions: list, customer: str) -> None:
    logger.debug(f"subs {subscriptions}")
    active_subscriptions = []
    try:
        active_subscriptions = [
            sub
            for sub in subscriptions
            if sub.get("status") in ["active", "trialing"]
            and sub.get("cancel_at") is None
        ]
        if not bool(active_subscriptions):
            sources = stripe.Customer.retrieve(id=customer)
            for source in sources.sources["data"]:
                stripe.Customer.delete_source(customer, source["id"])
    except KeyError as e:
        raise ClientError(message="Source missing key element.", payload=str(e))
    except TypeError as e:
        raise ClientError(message="Source missing type element.", payload=str(e))


def cancel_subscription(uid, sub_id) -> FlaskResponse:
    """
    Cancel an existing subscription for a user.
    :param uid:
    :param sub_id:
    :return: Success or failure message for the cancellation.
    """
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
            stripe.Subscription.modify(sub_id, cancel_at_period_end=True)
            check_stripe_subscriptions(subscription_user.custId)
            return {"message": "Subscription cancellation successful"}, 201
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
            if invoice["charge"]:
                intents = stripe.Charge.retrieve(invoice["charge"])
                logging.debug(f"intents {intents}")
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


def create_subscription_object_without_failure(subscription: object) -> object:
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
    items = g.subhub_account.get_user(uid)
    if not items or not items.custId:
        return {"message": "Customer does not exist."}, 404
    customer = stripe.Customer.retrieve(items.custId)
    if customer["metadata"]["userid"] == uid:
        customer.modify(items.custId, source=data["pmt_token"])
        return {"message": "Payment method updated successfully."}, 201
    else:
        return {"message": "Customer mismatch."}, 400


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
            if invoice["charge"]:
                intents = stripe.Charge.retrieve(invoice["charge"])
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
