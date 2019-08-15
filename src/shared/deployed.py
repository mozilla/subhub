# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from src.shared.types import FlaskResponse
from src.shared.cfg import CFG
from src.shared.log import get_logger

logger = get_logger()


def get_deployed() -> FlaskResponse:
    deployed = dict(
        DEPLOYED_BY=CFG.DEPLOYED_BY,
        DEPLOYED_ENV=CFG.DEPLOYED_ENV,
        DEPLOYED_WHEN=CFG.DEPLOYED_WHEN,
    )
    logger.debug("deployed", deployed=deployed)
    return deployed, 200
