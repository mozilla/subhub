import logging
import json

from subhub.api.webhooks.stripe.abstract import AbstractStripeWebhookEvent
from subhub.api.webhooks.routes.static import StaticRoutes

logger = logging.getLogger("invoice")
log_handle = logging.StreamHandler()
log_handle.setLevel(logging.INFO)
logformat = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log_handle.setFormatter(logformat)
logger.addHandler(log_handle)


class StripeInvoiceFinalized(AbstractStripeWebhookEvent):
    def run(self):
        data = {
            "event_id": self.payload.id,
            "event_type": self.payload.type,
            "invoice_id": self.payload.data.object.id,
            "customer_id": self.payload.data.object.customer,
            "subscription_id": self.payload.data.object.subscription,
            "currency": self.payload.data.object.currency,
            "charge": self.payload.data.object.charge,
            "period_start": self.payload.data.object.period_start,
            "period_end": self.payload.data.object.period_end,
            "amount_paid": self.payload.data.object.amount_paid,
            "invoice_number": self.payload.data.object.number,
            "description": self.payload.data.object.lines.data[0].description,
            "application_fee_amount": self.payload.data.object.application_fee_amount,
            "created": self.payload.data.object.created,
        }
        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(data))


class StripeInvoicePaymentFailed(AbstractStripeWebhookEvent):
    def run(self):
        data = {
            "event_id": self.payload.id,
            "event_type": self.payload.type,
            "customer_id": self.payload.data.object.customer,
            "subscription_id": self.payload.data.object.subscription,
            "currency": self.payload.data.object.currency,
            "charge": self.payload.data.object.charge,
            "number": self.payload.data.object.number,
            "amount_due": self.payload.data.object.amount_due,
            "created": self.payload.data.object.created,
        }
        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(data))
