# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from typing import Dict, Any, Union, Iterable

from flask import request, Response

from hub.stripe.invoices import StripeInvoicePaymentFailed
from hub.stripe.customer import StripeCustomerCreated
from hub.stripe.customer import StripeCustomerSourceExpiring
from hub.stripe.customer import StripeCustomerSubscriptionCreated
from hub.stripe.customer import StripeCustomerSubscriptionUpdated
from hub.stripe.customer import StripeCustomerSubscriptionDeleted
from shared.cfg import CFG
from shared.log import get_logger

logger = get_logger()


class StripeHubEventPipeline:
    def __init__(self, payload) -> None:
        assert isinstance(payload, dict)
        self.payload: dict = payload

    def run(self) -> None:
        event_type = self.payload["type"]
        if event_type == "customer.subscription.created":
            StripeCustomerSubscriptionCreated(self.payload).run()
        elif event_type == "customer.subscription.updated":
            StripeCustomerSubscriptionUpdated(self.payload).run()
        elif event_type == "customer.subscription.deleted":
            StripeCustomerSubscriptionDeleted(self.payload).run()
        elif event_type == "customer.created":
            StripeCustomerCreated(self.payload).run()
        elif event_type == "customer.source.expiring":
            StripeCustomerSourceExpiring(self.payload).run()
        elif event_type == "invoice.payment_failed":
            StripeInvoicePaymentFailed(self.payload).run()
        else:
            pass


def view() -> tuple:
    try:
        payload = request.data
        logger.info("check payload", payload=payload)
        logger.info("payload type", type=type(payload))
        sig_header = request.headers["Stripe-Signature"]
        event = stripe.Webhook.construct_event(payload, sig_header, CFG.HUB_API_KEY)
        return Response("", status=200)
    except ValueError as e:
        # Invalid payload
        logger.error("ValueError", error=e)
        return Response(str(e), status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.error("SignatureVerificationError", error=e)
        return Response(str(e), status=400)
    except Exception as e:
        logger.error("General Exception", error=e)
        return Response(str(e), status=500)
    finally:
        pipeline = StripeHubEventPipeline(event)
        pipeline.run()


def event_process(missing_event) -> Response:
    logger.info("event process", missing_event=missing_event)
    try:
        payload = missing_event
        if not isinstance(payload, dict):
            raise Exception
        logger.info("check payload", payload=payload)
        pipeline = StripeHubEventPipeline(payload)
        pipeline.run()
    except Exception as e:
        logger.error("General Exception", error=e)
        return Response(str(e), status=500)

    return Response("Success", status=200)
