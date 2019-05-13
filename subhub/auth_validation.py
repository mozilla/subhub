from subhub.cfg import CFG
from subhub import secrets


def payment_auth(api_token, required_scopes=None):
    if api_token in (CFG.PAYMENT_API_KEY,):
        return {"value": True}
    return None


def support_auth(api_token, required_scopes=None):
    if api_token in (CFG.SUPPORT_API_KEY,):
        return {"value": True}
    return None
