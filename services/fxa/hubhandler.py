#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys

# TODO!
# import newrelic.agent
import serverless_wsgi

serverless_wsgi.TEXT_MIME_TYPES.append("application/custom+json")

from os.path import join, dirname, realpath
# First some funky path manipulation so that we can work properly in
# the AWS environment
sys.path.insert(0, join(dirname(realpath(__file__)), 'src'))

# TODO!
# newrelic.agent.initialize()

from aws_xray_sdk.core import xray_recorder, patch_all
from aws_xray_sdk.core.context import Context
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware

from hub.app import create_app
from shared.log import get_logger

logger = get_logger()

xray_recorder.configure(service="fxa.hub")
patch_all()

hub_app = create_app()
XRayMiddleware(hub_app.app, xray_recorder)

# TODO!
# @newrelic.agent.lambda_handler()
def handle(event, context):
    try:
        logger.info("handling hub event", subhub_event=event, context=context)
        return serverless_wsgi.handle_request(hub_app.app, event, context)
    except Exception as e:  # pylint: disable=broad-except
        logger.exception("exception occurred", subhub_event=event, context=context, error=e)
        # TODO: Add Sentry exception catch here
        raise
