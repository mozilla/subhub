#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from subhub.cfg import CFG
from subhub.api.types import FlaskResponse
from subhub.log import get_logger

logger = get_logger()


def get_version() -> FlaskResponse:
    logger.debug("version", version=CFG.VERSION)
    return {"message": CFG.VERSION}, 200
