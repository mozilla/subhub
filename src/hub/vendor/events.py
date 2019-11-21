# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import time

from abc import ABC, abstractmethod
from typing import Dict, Any
from attrdict import AttrDict

from shared.cfg import CFG
from shared.log import get_logger

logger = get_logger()


class EventMaker(ABC):
    def __init__(self, payload) -> None:
        self.payload = AttrDict(payload)

    def get_complete_event(self) -> Dict[str, Any]:
        logger.debug(
            "complete pay", payload=self.payload, event_type=self.payload["type"]
        )
        return self.payload
