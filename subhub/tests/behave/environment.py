from subhub.tests.behave.utils.stripe_utils import StripeUtils


def before_all(context):
    context.stripe_utils = StripeUtils(context)


def before_scenario(context, scenario):
    context.headers = {}
    context.data = u""
    context.query = {}
