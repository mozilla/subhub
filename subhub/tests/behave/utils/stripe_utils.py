import stripe


class StripeUtils:
    def __init__(self, context):
        userdata = context.config.userdata
        stripe.api_key = userdata.get("stripe_api_key", "sk_test_12345")
        stripe.api_base = userdata.get("stripe_api_base", "http://localhost:12111")

    def create_customer(self):
        api_resource = stripe.Customer.create(
            source="subhub", metadata={"userid": "customer123"}
        )
        if api_resource is None:
            raise Exception("Stripe customer not created")
        return api_resource

    def create_plan(self):
        api_resource = stripe.Plan.create(interval="month", currency="usd")
        if api_resource is None:
            raise Exception("Stripe plan not created")
        return api_resource
