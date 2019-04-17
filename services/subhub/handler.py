#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import os
import sys

import awsgi

# First some funky path manipulation so that we can work properly in
# the AWS environment
dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(dir_path)

from subhub.app import create_app

# Logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create app at module scope to cache it for repeat requests
try:
    app = create_app()
except Exception:  # pylint: disable=broad-except
    logger.exception("Exception occurred while loading app")
    # TODO: Add Sentry exception catch here
    raise


def handle(event, context):
    try:
        return awsgi.response(app, event, context)
    except Exception:  # pylint: disable=broad-except
        logger.exception("Exception occurred while handling %s", event)
        # TODO: Add Sentry exception catch here
