import logging

from subhub.cfg import CFG
from subhub import secrets

logger = logging.getLogger()
logger.setLevel(logging.INFO)


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


def webhook_auth(api_token, required_scopes=None):
    logger.info(f"api token {api_token}")
    if api_token in (CFG.WEBHOOK_API_KEY,):
        return {"value": True}
    return None
