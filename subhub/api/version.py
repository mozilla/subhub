import logging

from subhub.cfg import CFG
from subhub.api.types import FlaskResponse

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_version() -> FlaskResponse:
    return {"message": CFG.APP_VERSION}, 200
