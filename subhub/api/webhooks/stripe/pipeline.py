from subhub.api.webhooks.stripe.customer import (
    StripeCustomerCreated,
    StripeCustomerDeleted,
    StripeCustomerSubscriptionCreated,
    StripeCustomerUpdated,
    StripeCustomerSubscriptionUpdated,
    StripeCustomerSubscriptionDeleted,
    StripeCustomerSourceExpiring,
)
from subhub.api.webhooks.stripe.charge import StripeChargeSucceededEvent
from subhub.api.webhooks.stripe.subscription import StripeSubscriptionCreated
from subhub.api.webhooks.stripe.unhandled import StripeUnhandledEvent
from subhub.api.webhooks.stripe.invoices import (
    StripeInvoiceFinalized,
    StripeInvoicePaymentFailed,
)
from subhub.api.webhooks.stripe.payment_intents import StripePaymentIntentSucceeded


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
        elif event_type == "invoice.finalized":
            StripeInvoiceFinalized(self.payload).run()
        elif event_type == "invoice.payment_failed":
            StripeInvoicePaymentFailed(self.payload).run()
        elif event_type == "payment_intent.succeeded":
            StripePaymentIntentSucceeded(self.payload).run()
        else:
            StripeUnhandledEvent(self.payload).run()
