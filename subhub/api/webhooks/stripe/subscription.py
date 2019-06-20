import json

from subhub.api.webhooks.stripe.abstract import AbstractStripeWebhookEvent
from subhub.api.webhooks.routes.static import StaticRoutes

from subhub.log import get_logger

logger = get_logger()


class StripeSubscriptionCreated(AbstractStripeWebhookEvent):
    def run(self):
        data = self.create_data(
            customer_id=self.payload.data.object.id,
            subscription_created=self.payload.data.items.data[0].created,
            current_period_start=self.payload.data.current_period_start,
            current_period_end=self.payload.data.current_period_end,
            plan_amount=self.payload.data.plan.amount,
            plan_currency=self.payload.data.plan.currency,
            plan_name=self.payload.data.plan.nickname,
            created=self.payload.data.object.created,
        )
        logger.info("subscription created", data=data)
        routes = [StaticRoutes.SALESFORCE_ROUTE]
        self.send_to_routes(routes, json.dumps(data))
