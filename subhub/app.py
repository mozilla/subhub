import os

import connexion
import stripe
import stripe.error
from flask import current_app, g
from flask_cors import CORS

from subhub.cfg import CFG
from subhub.exceptions import SubHubError
from subhub.secrets import get_secret
from subhub.subhub_dynamodb import SubHubAccount


def create_app(config=None):
    if not CFG('AWS_EXECUTION_ENV', None):
        options = {"swagger_ui": True}
        region = 'localhost'
        host = 'http://localhost:8000'
        stripe.api_key = CFG.STRIPE_API_KEY
    else:
        options = {"swagger_ui": False}
        region = 'us-west-2'
        host = None
        subhub_values = get_secret('dev/SUBHUB')
        stripe.api_key = subhub_values['stripe_api_key']

    app = connexion.FlaskApp(__name__, specification_dir='./', options=options)
    app.add_api('subhub_api.yaml', pass_context_arg_name='request',
                strict_validation=True)

    if host:
        app.app.subhub_account = SubHubAccount(table_name=CFG.USER_TABLE, region=region, host=host)
    else:
        app.app.subhub_account = SubHubAccount(table_name=CFG.USER_TABLE, region=region)
    if not app.app.subhub_account.model.exists():
        app.app.subhub_account.model.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)

    # Setup error handlers
    @app.app.errorhandler(SubHubError)
    def display_subhub_errors(e: SubHubError):
        if e.status_code == 500:
            # TODO: Log this error to Sentry
            pass
        return {"message": str(e)}, e.status_code

    # Setup Stripe Error handlers
    def intermittent_stripe_error(e):
        return {"message": "stripe error: {}".format(str(e))}, 503
    for err in (stripe.error.APIConnectionError, stripe.error.APIError,
                stripe.error.RateLimitError, stripe.error.IdempotencyError):
        app.app.errorhandler(err)(intermittent_stripe_error)

    def server_stripe_error(e):
        return {"message": "error fulfilling request: {}".format(str(e))}, 500
    for err in (stripe.error.AuthenticationError,
                stripe.error.InvalidRequestError,
                stripe.error.StripeErrorWithParamCode):
        app.app.errorhandler(err)(server_stripe_error)

    @app.app.errorhandler(stripe.error.CardError)
    def client_stripe_error(e):
        return {"message": "invalid card: {}".format(str(e))}, 400

    @app.app.before_request
    def before_request():
        g.subhub_account = current_app.subhub_account
        g.app_system_id = None
    CORS(app.app)
    return app


if __name__ == '__main__':
    print('starting app')
    port = int(os.environ.get("PORT", 5000))
    app = create_app()
    app.debug = True
    app.use_reloader=True
    app.run(host='0.0.0.0', port=port)
