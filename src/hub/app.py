# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import sys
import connexion
import stripe
import pynamodb

from flask import current_app, g, jsonify
from flask_cors import CORS
from flask import request
from typing import Any

from shared import secrets
from shared.exceptions import SubHubError
from shared.db import HubEvent, SubHubDeletedAccount
from shared.headers import dump_safe_headers
from shared.cfg import CFG
from shared.log import get_logger

logger = get_logger()


# Setup Stripe Error handlers
def intermittent_stripe_error(e):
    logger.error("intermittent stripe error", error=e)
    return jsonify({"message": f"{e.user_message}"}), 503


def server_stripe_error(e):
    logger.error("server stripe error", error=e)
    return (
        jsonify(
            {"message": "Internal Server Error", "params": None, "code": f"{e.code}"}
        ),
        500,
    )


def server_stripe_error_with_params(e):
    logger.error("server stripe error with params", error=e)
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


def server_stripe_card_error(e):
    logger.error("server stripe card error", error=e)
    return jsonify({"message": f"{e.user_message}", "code": f"{e.code}"}), 402


def database_connection_error(e):
    logger.error("unable to connect to db", error=e)
    return jsonify({"message": "Server Error", "status_code": "bad_connection"}), 500


def is_docker() -> bool:
    path = "/proc/self/cgroup"
    return (
        os.path.exists("/.dockerenv")
        or os.path.isfile(path)
        and any("docker" in line for line in open(path))
    )


# excluding from coverage as this is for local testing only
if is_docker():  # pragma: no cover
    stripe.log = "DEBUG"
    if CFG.STRIPE_LOCAL is not True:
        stripe.verify_ssl_certs = False
        stripe.api_base = (
            stripe.upload_api_base
        ) = f"https://{CFG.STRIPE_MOCK_HOST}:{CFG.STRIPE_MOCK_PORT}"
    logger.info("Stripe API URL", url=stripe.api_base, local=CFG.STRIPE_LOCAL)


def create_app(config=None) -> Any:
    stripe.timeout = CFG.STRIPE_REQUEST_TIMEOUT
    logger.info("creating flask app", config=config)
    region = "localhost"
    host = f"http://dynamodb:{CFG.DYNALITE_PORT}" if is_docker() else CFG.DYNALITE_URL
    stripe.api_key = CFG.STRIPE_API_KEY
    logger.debug("aws", aws=CFG.AWS_EXECUTION_ENV)
    if CFG.AWS_EXECUTION_ENV:
        region = "us-west-2"
        host = None
    options = dict(swagger_ui=CFG.SWAGGER_UI)

    app = connexion.FlaskApp(__name__, specification_dir=".", options=options)
    app.add_api("swagger.yaml", pass_context_arg_name="request", strict_validation=True)

    app.app.hub_table = HubEvent(table_name=CFG.EVENT_TABLE, region=region, host=host)
    app.app.subhub_deleted_users = SubHubDeletedAccount(
        table_name=CFG.DELETED_USER_TABLE, region=region, host=host
    )

    # Setup error handlers
    @app.app.errorhandler(SubHubError)
    def display_subhub_errors(e: SubHubError):
        if e.status_code == 500:
            logger.error("display hub errors", error=e)
        response = jsonify(e.to_dict())
        response.status_code = e.status_code
        return response

    if not app.app.hub_table.model.exists():
        app.app.hub_table.model.create_table(
            read_capacity_units=1, write_capacity_units=1, wait=True
        )

    if not app.app.subhub_deleted_users.model.exists():
        app.app.subhub_deleted_users.model.create_table(
            read_capacity_units=1, write_capacity_units=1, wait=True
        )

    for error in (
        stripe.error.APIConnectionError,
        stripe.error.APIError,
        stripe.error.RateLimitError,
        stripe.error.IdempotencyError,
    ):
        app.app.errorhandler(error)(intermittent_stripe_error)

    for error in (stripe.error.AuthenticationError,):
        app.app.errorhandler(error)(server_stripe_error)

    for error in (
        stripe.error.InvalidRequestError,
        stripe.error.StripeErrorWithParamCode,
    ):
        app.app.errorhandler(error)(server_stripe_error_with_params)

    for error in (stripe.error.CardError,):
        app.app.errorhandler(error)(server_stripe_card_error)

    for error in (pynamodb.exceptions.GetError,):
        app.app.errorhandler(error)(database_connection_error)

    @app.app.before_request
    def before_request():
        headers = dump_safe_headers(request.headers)
        logger.debug("Request headers", headers=headers)
        logger.debug("Request body", body=request.get_data())
        g.hub_table = current_app.hub_table
        g.subhub_deleted_users = current_app.subhub_deleted_users
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
    app.run(host="0.0.0.0", port=CFG.LOCAL_HUB_FLASK_PORT)
    logger.info("hub running", app=app)
