#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from flask import request, Response

import stripe
from subhub.cfg import CFG
from subhub.hub.stripe.customer import StripeCustomerCreated
from subhub.hub.stripe.customer import StripeCustomerDeleted
from subhub.hub.stripe.customer import StripeCustomerSubscriptionCreated
from subhub.hub.stripe.customer import StripeCustomerUpdated
from subhub.hub.stripe.subscription import StripeSubscriptionCreated
from subhub.hub.stripe.customer import StripeCustomerSubscriptionUpdated
from subhub.hub.stripe.customer import StripeCustomerSubscriptionDeleted
from subhub.hub.stripe.customer import StripeCustomerSourceExpiring
from subhub.hub.stripe.invoices import StripeInvoiceFinalized
from subhub.hub.stripe.invoices import StripeInvoicePaymentFailed
from subhub.hub.stripe.intents import StripePaymentIntentSucceeded
from subhub.log import get_logger

logger = get_logger()


class StripeHubEventPipeline:
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
        elif event_type == "subscription.created":
            StripeSubscriptionCreated(self.payload).run()
        elif event_type == "invoice.finalized":
            StripeInvoiceFinalized(self.payload).run()
        elif event_type == "payment_intent.succeeded":
            StripePaymentIntentSucceeded(self.payload).run()
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
        pipeline = StripeHubEventPipeline(event)
        pipeline.run()
    except ValueError as e:
        # Invalid payload
        logger.error("ValueError", error=e)
        return Response(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.error("SignatureVerificationError", error=e)
        return Response(status=400)
    except Exception as e:
        logger.error("General Exception", error=e)
        return Response(e, status=500)

    return Response("Success", status=200)


def event_process(missing_event):
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
        return Response(e, status=500)

    return Response("Success", status=200)
