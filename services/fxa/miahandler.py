# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import sys
import serverless_wsgi
import structlog

from sentry_sdk import init, capture_message
from os.path import join, dirname, realpath

# First some funky path manipulation so that we can work properly in
# the AWS environment
sys.path.insert(0, join(dirname(realpath(__file__)), "src"))

from hub.verifications import events_check
from shared.log import get_logger
from shared.cfg import CFG

init(CFG.SENTRY_URL)

logger = get_logger()

# NOTE: The context object has the following available to it.
#   https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html#python-context-object-props
# NOTE: Available environment passed to the Flask from serverless-wsgi
#   https://github.com/logandk/serverless-wsgi/blob/2911d69a87ae8057110a1dcf0c21288477e07ce1/serverless_wsgi.py#L126
def handle(event, context):
    try:
        processing_duration = int(os.getenv("PROCESS_EVENTS_HOURS", "6"))
        events_check.process_events(processing_duration)
    except Exception as e:  # pylint: disable=broad-except
        logger.exception(
            "exception occurred", subhub_event=event, context=context, error=e
        )
        raise
    finally:
        logger.info("handling mia event", subhub_event=event, context=context)
