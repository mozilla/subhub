from subhub.cfg import CFG
from subhub.api.types import FlaskResponse
from subhub.log import get_logger

logger = get_logger()


def get_version() -> FlaskResponse:
    logger.debug("version", version=CFG.VERSION)
    return {"message": CFG.VERSION}, 200
