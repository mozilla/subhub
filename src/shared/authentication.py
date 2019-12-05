# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from shared import secrets
from shared.cfg import CFG
from shared.log import get_logger

logger = get_logger()


def test_token(test_api_token, cfg_api_token):
    # Make sure the config API token has a meaningful value set,
    # to avoid an auth bypass on empty comparisons
    if cfg_api_token in (None, "None", ""):
        return None

    if test_api_token == cfg_api_token:
        return {"value": True}

    return None


def payment_auth(api_token, required_scopes=None):
    return test_token(api_token, CFG.PAYMENT_API_KEY)


def support_auth(api_token, required_scopes=None):
    return test_token(api_token, CFG.SUPPORT_API_KEY)


def hub_auth(api_token, required_scopes=None):
    return test_token(api_token, CFG.HUB_API_KEY)
