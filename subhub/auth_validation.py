from subhub import secrets
from subhub.cfg import CFG
from subhub.log import get_logger
from subhub.tracing import timed

logger = get_logger()


@timed
def payment_auth(api_token, required_scopes=None):
    logger.info(f"api token {api_token}")
    if api_token in (CFG.PAYMENT_API_KEY,):
        return {"value": True}
    return None


@timed
def support_auth(api_token, required_scopes=None):
    logger.info(f"api token {api_token}")
    if api_token in (CFG.SUPPORT_API_KEY,):
        return {"value": True}
    return None


@timed
def webhook_auth(api_token, required_scopes=None):
    logger.info(f"api token {api_token}")
    if api_token in (CFG.WEBHOOK_API_KEY,):
        return {"value": True}
    return None
