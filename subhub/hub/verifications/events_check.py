#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from abc import ABC
import time
from datetime import datetime, timedelta

from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware

from subhub.app import create_app, g
from subhub.hub.stripe.controller import event_process
from flask import current_app
import stripe

from subhub.cfg import CFG
from subhub.log import get_logger

logger = get_logger()

xray_recorder.configure(service="subhub-missing-events")

try:
    app = create_app()
    XRayMiddleware(app.app, xray_recorder)
except Exception:  # pylint: disable=broad-except
    logger.exception("Exception occurred while loading app")
    raise


class EventCheck(ABC):
    def __init__(self, hours_back):
        self.hours_back = hours_back

    def retrieve_events(self, last_event=str()):
        retrieved_events = 0
        has_more = True
        while has_more:
            if not last_event:
                events = self.get_events()
            else:
                events = self.get_events_with_last_event(last_event)
            logger.info("events", events=events)
            logger.info("has more", has_more=events.has_more)
            for e in events.data:
                existing_event = g.hub_table.get_event(e["id"])
                logger.info("existing event", existing_event=existing_event)

                if not existing_event:
                    logger.info("is existing event", is_event=existing_event)
                    self.process_missing_event(e)
            retrieved_events += len(events.data)

            has_more = events.has_more
            if has_more:
                last_event = events.data[-1]["id"]
            logger.info("last_event", last_event=last_event)
        logger.info("number events", number_of_events=retrieved_events)

    def get_events(self):
        return stripe.Event.list(
            limit=100,
            types=CFG.PAYMENT_EVENT_LIST,
            created={"gt": self.get_time_h_hours_ago(self.hours_back)},
        )

    def get_events_with_last_event(self, last_event):
        return stripe.Event.list(
            limit=100,
            types=CFG.PAYMENT_EVENT_LIST,
            created={"gt": self.get_time_h_hours_ago(self.hours_back)},
            starting_after=last_event,
        )

    @staticmethod
    def get_time_h_hours_ago(hours_back: int) -> int:
        h_hours_ago = datetime.now() - timedelta(hours=hours_back)
        return int(time.mktime(h_hours_ago.timetuple()))

    @staticmethod
    def process_missing_event(missing_event):
        event_process(missing_event)


def process_events(hours_back: int):
    with app.app.app_context():
        g.hub_table = current_app.hub_table
        event_check = EventCheck(hours_back)
        event_check.retrieve_events("")
