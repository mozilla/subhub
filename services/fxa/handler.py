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
sys.path.append(f"{os.path.dirname(os.path.realpath(__file__))}/src")

from src.sub.app import create_app as create_sub_app
from src.hub.app import create_app as create_hub_app
from src.shared.log import get_logger
from src.hub.verifications import events_check

logger = get_logger()

xray_recorder.configure(service="sub")


@newrelic.agent.lambda_handler()
def handle_sub(event, context):
    try:
        logger.info("handling sub event", subhub_event=event, context=context)
        sub_app = create_sub_app()
        XRayMiddleware(sub_app.app, xray_recorder)
        return awsgi.response(sub_app, event, context)
    except Exception as e:  # pylint: disable=broad-except
        logger.exception("exception occurred", subhub_event=event, context=context, error=e)
        # TODO: Add Sentry exception catch here
        raise

@newrelic.agent.lambda_handler()
def handle_hub(event, context):
    try:
        logger.info("handling hub event", subhub_event=event, context=context)
        hub_app = create_hub_app()
        XRayMiddleware(hub_app.app, xray_recorder)
        return awsgi.response(hub_app, event, context)
    except Exception as e:  # pylint: disable=broad-except
        logger.exception("exception occurred", subhub_event=event, context=context, error=e)
        # TODO: Add Sentry exception catch here
        raise

# TODO: Discuss
@newrelic.agent.lambda_handler()
def handle_mia(event, context):
    try:
        logger.info("handling event", subhub_event=event, context=context)
        events_check.process_events(6)
    except Exception as e:  # pylint: disable=broad-except
        logger.exception("exception occurred", subhub_event=event, context=context, error=e)
        # TODO: Add Sentry exception catch here
        raise
