#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys

import awsgi
import newrelic.agent

from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware

newrelic.agent.initialize()

# First some funky path manipulation so that we can work properly in
# the AWS environment
dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(dir_path)

from subhub.app import create_app
from subhub.log import get_logger

logger = get_logger()

xray_recorder.configure(service="subhub")

# Create app at module scope to cache it for repeat requests
try:
    app = create_app()
    XRayMiddleware(app.app, xray_recorder)
except Exception:  # pylint: disable=broad-except
    logger.exception("Exception occurred while loading app")
    # TODO: Add Sentry exception catch here
    raise

@newrelic.agent.lambda_handler()
def handle(event, context):
    try:
        logger.info("handling event", subhub_event=event, context=context)
        return awsgi.response(app, event, context)
    except Exception as e:  # pylint: disable=broad-except
        logger.exception("exception occurred", subhub_event=event, context=context, error=e)
        # TODO: Add Sentry exception catch here
        raise
