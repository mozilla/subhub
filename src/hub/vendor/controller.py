# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import json
import stripe

from flask import request, Response
from typing import Dict, Any, Union, Iterable

from shared.cfg import CFG
from hub.vendor.customer import (
    StripeCustomerCreated,
    StripeCustomerSubscriptionUpdated,
    StripeCustomerSourceExpiring,
    StripeCustomerDeleted,
    StripeCustomerSubscriptionDeleted,
)
from hub.vendor.invoices import (
    StripeInvoicePaymentFailed,
    StripeInvoicePaymentSucceeded,
)
from hub.vendor.events import EventMaker
from shared.log import get_logger

logger = get_logger()


class StripeHubEventPipeline:
    def __init__(self, payload) -> None:
        assert isinstance(payload, dict)  # nosec
        self.payload: dict = payload

    def run(self) -> None:
        logger.debug("run", payload=self.payload)
        event_type = self.payload["type"]
        if event_type == "customer.subscription.updated":
            StripeCustomerSubscriptionUpdated(self.payload).run()
        elif event_type == "customer.subscription.deleted":
            StripeCustomerSubscriptionDeleted(self.payload).run()
        elif event_type == "customer.created":
            StripeCustomerCreated(self.payload).run()
        elif event_type == "customer.deleted":
            StripeCustomerDeleted(self.payload).run()
        elif event_type == "customer.source.expiring":
            StripeCustomerSourceExpiring(self.payload).run()
        elif event_type == "invoice.payment_failed":
            StripeInvoicePaymentFailed(self.payload).run()
        elif event_type == "invoice.payment_succeeded":
            StripeInvoicePaymentSucceeded(self.payload).run()
        else:
            pass


def view() -> Response:
    try:
        logger.debug("request", request=request)
        payload = request.data
        logger.debug("check payload", payload=payload)
        if not os.environ.get("HUB_DOCKER"):
            sig_header = request.headers["Stripe-Signature"]
            logger.debug("sig header", sig_header=sig_header)
            webhook_event = stripe.Webhook.construct_event(
                payload, sig_header, CFG.HUB_API_KEY
            )
        else:
            web_hook_payload = json.loads(payload.decode("utf-8"))
            logger.debug(
                "payload",
                payload_type=type(web_hook_payload),
                web_hook_payload=web_hook_payload,
                webhhook_type=web_hook_payload["type"],
            )
            event = EventMaker(payload=web_hook_payload)
            webhook_event = event.get_complete_event()
        return Response("", status=200)
    except ValueError as e:
        # Invalid payload
        logger.error("ValueError", error=e, payload=payload)
        return Response(str(e), status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.error("SignatureVerificationError", error=e, payload=payload)
        return Response(str(e), status=400)
    except Exception as e:
        logger.error("General Exception", error=e, payload=payload)
        return Response(str(e), status=500)
    finally:
        logger.debug("stripe event", webhook_event=webhook_event)
        pipeline = StripeHubEventPipeline(webhook_event)
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
