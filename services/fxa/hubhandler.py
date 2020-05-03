#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import sys
import serverless_wsgi

from sentry_sdk import init, capture_message
from os.path import join, dirname, realpath

serverless_wsgi.TEXT_MIME_TYPES.append("application/custom+json")

# First some funky path manipulation so that we can work properly in
# the AWS environment
sys.path.insert(0, join(dirname(realpath(__file__)), "src"))

from hub.app import create_app
from shared.cfg import CFG
from shared.log import get_logger

init(CFG.SENTRY_URL)
logger = get_logger()
hub_app = create_app()

# NOTE: The context object has the following available to it.
#   https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html#python-context-object-props
# NOTE: Available environment passed to the Flask from serverless-wsgi
#   https://github.com/logandk/serverless-wsgi/blob/2911d69a87ae8057110a1dcf0c21288477e07ce1/serverless_wsgi.py#L126
def handle(event, context):
    try:
        return serverless_wsgi.handle_request(hub_app.app, event, context)
    except Exception as e:  # pylint: disable=broad-except
        logger.exception(
            "exception occurred", subhub_event=event, context=context, error=e
        )
        raise
    finally:
        logger.info("handling hub event", subhub_event=event, context=context)
