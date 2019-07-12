from datetime import datetime
import stripe
from flask import g

from subhub.api.types import JsonDict, FlaskResponse, FlaskListResponse
from subhub.customer import existing_or_new_customer, has_existing_plan
from subhub.exceptions import ClientError
from subhub.log import get_logger

logger = get_logger()


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
        display_name=data["display_name"],
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
    logger.info("number of plans", count=len(plans))
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
    logger.debug("check strip subscriptions", subscriptions=customer_info.subscriptions)
    try:
        customer_subscriptions_data = customer_info.subscriptions
        customer_subscriptions = customer_subscriptions_data.get("data")
        sources_to_remove(customer_subscriptions, customer)
        return customer_subscriptions
    except NameError as ne:
        logger.error("error getting subscriptions", customer=customer, error=ne)
        return []


def sources_to_remove(subscriptions: list, customer: str) -> None:
    logger.debug("subscriptions", subscriptions=subscriptions)
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
    except KeyError as ke:
        message = "Source missing 'key' element"
        logger.error(message, error=ke)
        raise ClientError(message=message) from ke
    except TypeError as te:
        message = "Source missing 'type' element"
        logger.error(message, error=ke)
        raise ClientError(message=message) from te


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
    customer = stripe.Customer.retrieve(subscription_user.cust_id)
    for item in customer["subscriptions"]["data"]:
        if item["id"] == sub_id and item["status"] in [
            "active",
            "trialing",
            "incomplete",
        ]:
            stripe.Subscription.modify(sub_id, cancel_at_period_end=True)
            check_stripe_subscriptions(subscription_user.cust_id)
            return {"message": "Subscription cancellation successful"}, 201
    return {"message": "Subscription not available."}, 400


def delete_customer(uid) -> FlaskResponse:
    """
    Delete an existing customer, cancel active subscriptions
    and delete from payment provider
    :param uid:
    :return: Success of failure message for the deletion
    """
    subscription_user = g.subhub_account.get_user(uid)
    if not subscription_user:
        return dict(message="Customer does not exist."), 404
    deleted_payment_customer = stripe.Customer.delete(subscription_user.cust_id)
    if deleted_payment_customer:
        deleted_customer = g.subhub_account.remove_from_db(uid)
        if deleted_customer:
            return dict(message="Customer deleted successfully"), 200
    return dict(message="Customer not available"), 400


def reactivate_subscription(uid, sub_id):
    """
    Given a user's subscription that is flagged for cancellation, but is still active
    remove the cancellation flag to ensure the subscription remains active
    :param uid: User ID
    :param sub_id: Subscription ID
    :return: Success or failure message for the activation
    """
    subscription_user = g.subhub_account.get_user(uid)
    if not subscription_user:
        return {"message": "Customer does not exist."}, 404

    customer = stripe.Customer.retrieve(subscription_user.cust_id)
    active_subscriptions = customer["subscriptions"]["data"]

    for subscription in active_subscriptions:
        if subscription["id"] == sub_id:
            if subscription["cancel_at_period_end"]:
                stripe.Subscription.modify(sub_id, cancel_at_period_end=False)
                return {"message": "Subscription reactivation was successful."}, 201
            return {"message": "Subscription is already active."}, 200
    return {"message": "Current subscription not found."}, 404


def support_status(uid) -> FlaskResponse:
    return subscription_status(uid)


def subscription_status(uid) -> FlaskResponse:
    """
    Given a user id return the current subscription status
    :param uid:
    :return: Current subscriptions
    """
    items = g.subhub_account.get_user(uid)
    if not items or not items.cust_id:
        return {"message": "Customer does not exist."}, 404
    subscriptions = stripe.Subscription.list(
        customer=items.cust_id, limit=100, status="all"
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
    if not items or not items.cust_id:
        return {"message": "Customer does not exist."}, 404
    customer = stripe.Customer.retrieve(items.cust_id)
    if customer["metadata"]["userid"] == uid:
        customer.modify(items.cust_id, source=data["pmt_token"])
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
    if not items or not items.cust_id:
        return "Customer does not exist.", 404
    try:
        customer = stripe.Customer.retrieve(items.cust_id)
        if customer["metadata"]["userid"] == uid:
            return_data = create_update_data(customer)
            return return_data, 200
        else:
            return "Customer mismatch.", 400
    except KeyError as e:
        logger.error("Customer does not exist", error=e)
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
