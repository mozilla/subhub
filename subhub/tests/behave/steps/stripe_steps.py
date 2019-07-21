import stripe
from behave import given, when, then


@given('I am using the Stripe API located at "{api_base}"')
def using_api_base(context, api_base):
    stripe.api_base = api_base
