import os
import sys

import connexion
import stripe
import stripe.error
from flask import current_app, g, jsonify
from flask_cors import CORS
from flask import request

from subhub import secrets
from subhub.cfg import CFG
from subhub.exceptions import SubHubError
from subhub.subhub_dynamodb import SubHubAccount, WebHookEvent

from subhub.log import get_logger

logger = get_logger()


def create_app(config=None):
    logger.info("creating flask app", config=config)
    if not CFG.AWS_EXECUTION_ENV:
        region = "localhost"
        host = f"http://localhost:{CFG.DYNALITE_PORT}"
        stripe.api_key = CFG.STRIPE_API_KEY
    else:
        region = "us-west-2"
        host = None
        stripe.api_key = CFG.STRIPE_API_KEY
    options = dict(swagger_ui=CFG.SWAGGER_UI)

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
        return jsonify({"message": f"{e.user_message}"}), 503

    for err in (
        stripe.error.APIConnectionError,
        stripe.error.APIError,
        stripe.error.RateLimitError,
        stripe.error.IdempotencyError,
    ):
        app.app.errorhandler(err)(intermittent_stripe_error)

    def server_stripe_error(e):
        return jsonify({"message": f"{e.user_message}", "code": f"{e.code}"}), 500

    for err in (stripe.error.AuthenticationError,):
        app.app.errorhandler(err)(server_stripe_error)

    def server_stripe_error_with_params(e):
        return (
            jsonify(
                {
                    "message": f"{e.user_message}",
                    "params": f"{e.param}",
                    "code": f"{e.code}",
                }
            ),
            500,
        )

    for err in (
        stripe.error.InvalidRequestError,
        stripe.error.StripeErrorWithParamCode,
    ):
        app.app.errorhandler(err)(server_stripe_error_with_params)

    def server_stripe_card_error(e):
        return (jsonify({"message": f"{e.user_message}", "code": f"{e.code}"}), 402)

    for err in (stripe.error.CardError,):
        app.app.errorhandler(err)(server_stripe_card_error)

    @app.app.before_request
    def before_request():
        g.subhub_account = current_app.subhub_account
        g.webhook_table = current_app.webhook_table
        g.app_system_id = None
        if CFG.PROFILING_ENABLED:
            if "profile" in request.args and not hasattr(sys, "_called_from_test"):
                from pyinstrument import Profiler

                g.profiler = Profiler()
                g.profiler.start()

    @app.app.after_request
    def after_request(response):
        if not hasattr(g, "profiler") or hasattr(sys, "_called_from_test"):
            return response
        if CFG.PROFILING_ENABLED:
            g.profiler.stop()
            output_html = g.profiler.output_html()
            return app.app.make_response(output_html)
        return response

    CORS(app.app)
    return app


if __name__ == "__main__":
    app = create_app()
    app.debug = True
    app.use_reloader = True
    app.run(host="0.0.0.0", port=CFG.LOCAL_FLASK_PORT)
