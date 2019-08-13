#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys

from subhub.hub.verifications import events_check
from subhub.log import get_logger

# First some funky path manipulation so that we can work properly in
# the AWS environment
dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(dir_path)

logger = get_logger()


def handle(event, context):
    try:
        logger.info("handling event", subhub_event=event, context=context)
        events_check.process_events(6)
    except Exception as e:  # pylint: disable=broad-except
        logger.exception("exception occurred", subhub_event=event, context=context, error=e)
        # TODO: Add Sentry exception catch here
        raise
