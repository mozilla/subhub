from subhub.api.webhooks.stripe.abstract import AbstractStripeWebhookEvent


class StripeUnhandledEvent(AbstractStripeWebhookEvent):
    def run(self):
        salesforce_payload = self.payload
        self.unhandled_event(salesforce_payload)
