from flask import request, Response
import logging

import stripe

# from subhub.api.webhooks.stripe.pipeline import StripeWebhookEventPipeline

from subhub.cfg import CFG
from subhub import secrets

from subhub.api.webhooks.stripe.customer import StripeCustomerCreated
from subhub.api.webhooks.stripe.charge import StripeChargeSucceededEvent
from subhub.api.webhooks.stripe.customer import StripeCustomerDeleted
from subhub.api.webhooks.stripe.customer import StripeCustomerSubscriptionCreated
from subhub.api.webhooks.stripe.customer import StripeCustomerUpdated
from subhub.api.webhooks.stripe.subscription import StripeSubscriptionCreated
from subhub.api.webhooks.stripe.customer import StripeCustomerSubscriptionUpdated
from subhub.api.webhooks.stripe.customer import StripeCustomerSubscriptionDeleted
from subhub.api.webhooks.stripe.customer import StripeCustomerSourceExpiring
from subhub.api.webhooks.stripe.unhandled import StripeUnhandledEvent


logger = logging.getLogger("webhook_controller")
log_handle = logging.StreamHandler()
log_handle.setLevel(logging.INFO)
logformat = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log_handle.setFormatter(logformat)
logger.addHandler(log_handle)


class StripeWebhookEventPipeline:
    def __init__(self, payload):
        assert isinstance(payload, object)
        self.payload = payload

    def run(self):
        event_type = self.payload["type"]
        if event_type == "customer.subscription.created":
            StripeCustomerSubscriptionCreated(self.payload).run()
        elif event_type == "customer.subscription.updated":
            StripeCustomerSubscriptionUpdated(self.payload).run()
        elif event_type == "customer.subscription.deleted":
            StripeCustomerSubscriptionDeleted(self.payload).run()
        elif event_type == "customer.created":
            StripeCustomerCreated(self.payload).run()
        elif event_type == "customer.updated":
            StripeCustomerUpdated(self.payload).run()
        elif event_type == "customer.deleted":
            StripeCustomerDeleted(self.payload).run()
        elif event_type == "customer.source.expiring":
            StripeCustomerSourceExpiring(self.payload).run()
        elif event_type == "charge.succeeded":
            StripeChargeSucceededEvent(self.payload).run()
        elif event_type == "subscription.created":
            StripeSubscriptionCreated(self.payload).run()
        else:
            StripeUnhandledEvent(self.payload).run()


def view() -> tuple:
    logger.info(f"meta {request}")
    try:
        payload = request.data
        sig_header = request.headers["Stripe-Signature"]
        event = stripe.Webhook.construct_event(payload, sig_header, CFG.WEBHOOK_API_KEY)
        p = StripeWebhookEventPipeline(event)
        p.run()
    except ValueError as e:
        # Invalid payload
        logger.error(f"ValueError: {e}")
        return Response(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.error(f"SignatureVerificationError {e}")
        return Response(status=400)
    except Exception as e:
        logger.error(f"Oops! {e}")
        return Response(e, status=500)

    return Response("Success", status=200)
