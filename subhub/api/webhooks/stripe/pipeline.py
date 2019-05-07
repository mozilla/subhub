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
