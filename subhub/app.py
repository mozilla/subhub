import os

import connexion
import stripe
import stripe.error
from flask import current_app, g, jsonify
from flask_cors import CORS

from subhub.cfg import CFG
from subhub.exceptions import SubHubError
from subhub.subhub_dynamodb import SubHubAccount, WebHookEvent


def create_app(config=None):
    if not CFG.AWS_EXECUTION_ENV:
        options = {"swagger_ui": True}
        region = "localhost"
        host = f"http://localhost:{CFG.DYNALITE_PORT}"
        stripe.api_key = CFG.STRIPE_API_KEY
    else:
        options = {"swagger_ui": False}
        region = "us-west-2"
        host = None
        stripe.api_key = CFG.STRIPE_API_KEY

    app = connexion.FlaskApp(__name__, specification_dir="./", options=options)
    app.add_api(
        "subhub_api.yaml", pass_context_arg_name="request", strict_validation=True
    )

    if host:
        app.app.subhub_account = SubHubAccount(
            table_name=CFG.USER_TABLE, region=region, host=host
        )
        app.app.webhook_table = WebHookEvent(
            table_name=CFG.EVENT_TABLE, region=region, host=host
        )
    else:
        app.app.subhub_account = SubHubAccount(table_name=CFG.USER_TABLE, region=region)
        app.app.webhook_table = WebHookEvent(table_name=CFG.EVENT_TABLE, region=region)
    if not app.app.subhub_account.model.exists():
        app.app.subhub_account.model.create_table(
            read_capacity_units=1, write_capacity_units=1, wait=True
        )
    if not app.app.webhook_table.model.exists():
        app.app.webhook_table.model.create_table(
            read_capacity_units=1, write_capacity_units=1, wait=True
        )

    # Setup error handlers
    @app.app.errorhandler(SubHubError)
    def display_subhub_errors(e: SubHubError):
        if e.status_code == 500:
            # TODO: Log this error to Sentry
            pass
        response = jsonify(e.to_dict())
        response.status_code = e.status_code
        return response

    # Setup Stripe Error handlers
    def intermittent_stripe_error(e):
        return (jsonify({"message": "{}".format(str(e.user_message))}), 503)

    for err in (
        stripe.error.APIConnectionError,
        stripe.error.APIError,
        stripe.error.RateLimitError,
        stripe.error.IdempotencyError,
    ):
        app.app.errorhandler(err)(intermittent_stripe_error)

    def server_stripe_error(e):
        return (jsonify({"message": "{}".format(str(e.user_message))}), 500)

    for err in (
        stripe.error.AuthenticationError,
        stripe.error.InvalidRequestError,
        stripe.error.StripeErrorWithParamCode,
    ):
        app.app.errorhandler(err)(server_stripe_error)

    @app.app.errorhandler(stripe.error.CardError)
    def client_stripe_error(e):
        return (jsonify({"message": "{}".format(str(e.user_message))}), 400)

    @app.app.before_request
    def before_request():
        g.subhub_account = current_app.subhub_account
        g.webhook_table = current_app.webhook_table
        g.app_system_id = None

    CORS(app.app)
    return app


if __name__ == "__main__":
    print("starting app")
    app = create_app()
    app.debug = True
    app.use_reloader = True
    app.run(host="0.0.0.0", port=CFG.LOCAL_FLASK_PORT)
