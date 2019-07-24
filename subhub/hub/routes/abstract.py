#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from abc import ABC

import flask

from subhub.log import get_logger

logger = get_logger()


class AbstractRoute(ABC):
    def __init__(self, payload):
        self.payload = payload

    def report_route(self, payload: dict, sent_system: str):
        logger.info("report route", payload=payload, sent_system=sent_system)
        existing = flask.g.hub_table.get_event(payload["event_id"])
        if not existing:
            created = flask.g.hub_table.new_event(
                event_id=payload["event_id"], sent_system=sent_system
            )
            saved = flask.g.hub_table.save_event(created)
            logger.info("new event", created=created, saved=saved)
        else:
            updated = flask.g.hub_table.append_event(
                event_id=payload["event_id"], sent_system=sent_system
            )
            logger.info("updated event", existing=existing, updated=updated)

    def report_route_error(self, payload):
        logger.error("report route error", payload=payload)
