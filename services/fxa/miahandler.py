# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import sys
import newrelic.agent
import serverless_wsgi
import structlog

from os.path import join, dirname, realpath

# First some funky path manipulation so that we can work properly in
# the AWS environment
sys.path.insert(0, join(dirname(realpath(__file__)), "src"))

newrelic.agent.initialize()

from aws_xray_sdk.core import xray_recorder, patch_all
from aws_xray_sdk.core.context import Context
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware

from hub.verifications import events_check
from shared.log import get_logger

logger = get_logger()

xray_recorder.configure(service="fxa.mia")
patch_all()

# NOTE: The context object has the following available to it.
#   https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html#python-context-object-props
# NOTE: Available environment passed to the Flask from serverless-wsgi
#   https://github.com/logandk/serverless-wsgi/blob/2911d69a87ae8057110a1dcf0c21288477e07ce1/serverless_wsgi.py#L126
@newrelic.agent.lambda_handler()
def handle_mia(event, context):
    try:
        processing_duration = int(os.getenv("PROCESS_EVENTS_HOURS", "6"))
        events_check.process_events(processing_duration)
    except Exception as e:  # pylint: disable=broad-except
        logger.exception(
            "exception occurred", subhub_event=event, context=context, error=e
        )
        # TODO: Add Sentry exception catch here
        raise
    finally:
        logger.info("handling mia event", subhub_event=event, context=context)
