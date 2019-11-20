# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import flask

from abc import ABC

from src.shared.log import get_logger

logger = get_logger()


class AbstractRoute(ABC):
    def __init__(self, payload) -> None:
        self.payload = payload

    def report_route(self, payload: dict, sent_system: str) -> None:
        logger.info("report route", payload=payload, sent_system=sent_system)
        if payload.get("event_id"):
            event_id = payload["event_id"]
        else:
            event_id = payload["eventId"]
        existing = flask.g.hub_table.get_event(event_id)
        if not existing:
            created_event = flask.g.hub_table.new_event(
                event_id=event_id, sent_system=sent_system
            )
            saved = flask.g.hub_table.save_event(created_event)
            try:
                logger.info("new event created", created_event=created_event)
            except Exception as e:
                logger.error("Error logging created", error=e)
            try:
                logger.info("new event saved", saved=saved)
            except Exception as e:
                logger.error("Error logging saved", error=e)
        else:
            updated = flask.g.hub_table.append_event(
                event_id=event_id, sent_system=sent_system
            )
            logger.info("updated event", existing=existing, updated=updated)

    def report_route_error(self, payload) -> None:
        logger.error("report route error", payload=payload)
