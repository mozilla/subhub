#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys

import awsgi
import newrelic.agent

from os.path import join, dirname, realpath
# First some funky path manipulation so that we can work properly in
# the AWS environment
sys.path.insert(0, join(dirname(realpath(__file__)), 'src'))

newrelic.agent.initialize()

from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware

from sub.app import create_app as create_sub_app
from hub.app import create_app as create_hub_app
from hub.verifications import events_check
from shared.log import get_logger

logger = get_logger()


@newrelic.agent.lambda_handler()
def handle_sub(event, context):
    try:
        xray_recorder.configure(service="fxa.sub")
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
        xray_recorder.configure(service="fxa.hub")
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
        logger.info("handling mia event", subhub_event=event, context=context)
        events_check.process_events(6)
    except Exception as e:  # pylint: disable=broad-except
        logger.exception("exception occurred", subhub_event=event, context=context, error=e)
        # TODO: Add Sentry exception catch here
        raise
