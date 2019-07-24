#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from subhub import secrets
from subhub.cfg import CFG
from subhub.log import get_logger

logger = get_logger()


def payment_auth(api_token, required_scopes=None):
    logger.info(f"api token {api_token}")
    if api_token in (CFG.PAYMENT_API_KEY,):
        return {"value": True}
    return None


def support_auth(api_token, required_scopes=None):
    logger.info(f"api token {api_token}")
    if api_token in (CFG.SUPPORT_API_KEY,):
        return {"value": True}
    return None


def hub_auth(api_token, required_scopes=None):
    logger.info(f"api token {api_token}")
    if api_token in (CFG.HUB_API_KEY,):
        return {"value": True}
    return None
