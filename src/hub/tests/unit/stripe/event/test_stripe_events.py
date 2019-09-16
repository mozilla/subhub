# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import time
import json
import boto3
import flask
import stripe
import requests

from flask import Response
from mockito import when, mock, unstub
from datetime import datetime, timedelta

from hub.shared.tests.unit.utils import run_view, run_event_process
from hub.verifications.events_check import EventCheck, process_events
from hub.shared.cfg import CFG
from hub.shared.log import get_logger

logger = get_logger()

CWD = os.path.realpath(os.path.dirname(__file__))


def test_hours_back():
    event_check_class = EventCheck(hours_back=1)
    assert isinstance(
        event_check_class.get_time_h_hours_ago(hours_back=event_check_class.hours_back),
        int,
    )


def test_process_missing_event():
    missing_event = "event.json"
    with open(os.path.join(CWD, missing_event)) as f:
        event_check = EventCheck(6)
        event_check.process_missing_event(json.load(f))


def test_retrieve_events():
    missing_event = "event.json"

    def get_hours_back():
        h_hours_ago = datetime.now() - timedelta(hours=6)
        return int(time.mktime(h_hours_ago.timetuple()))

    with open(os.path.join(CWD, missing_event)) as f:
        event_response = mock(json.load(f))

        when(stripe.Event).list(
            limit=100, types=CFG.PAYMENT_EVENT_LIST, created={"gt": get_hours_back()}
        ).thenReturn(event_response)
        event_check = EventCheck(6)
        event_check.retrieve_events("")
    unstub()


def test_retrieve_events_more():
    missing_event = "more_event.json"

    def get_hours_back():
        h_hours_ago = datetime.now() - timedelta(hours=6)
        return int(time.mktime(h_hours_ago.timetuple()))

    with open(os.path.join(CWD, missing_event)) as f:
        event_response = mock(json.load(f))

        when(stripe.Event).list(
            limit=100,
            types=CFG.PAYMENT_EVENT_LIST,
            created={"gt": get_hours_back()},
            starting_after="evt_001",
        ).thenReturn(event_response)
        event_check = EventCheck(6)
        event_check.get_events_with_last_event("evt_001")
    unstub()


def test_process_events():
    missing_event = "event.json"

    def get_hours_back():
        h_hours_ago = datetime.now() - timedelta(hours=6)
        return int(time.mktime(h_hours_ago.timetuple()))

    with open(os.path.join(CWD, missing_event)) as f:
        event_response = mock(json.load(f))

        when(stripe.Event).list(
            limit=100, types=CFG.PAYMENT_EVENT_LIST, created={"gt": get_hours_back()}
        ).thenReturn(event_response)
        process_events(6)
    unstub()
