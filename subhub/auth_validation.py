import json

from subhub.cfg import CFG
from subhub.secrets import get_secret


def payment_auth(api_token, required_scopes=None):
    secrets = json.loads(get_secret_values())
    print(f'secrets {secrets}')
    if api_token in secrets:
        print(f'token {api_token}')
        return {"token": api_token}
    return None


def get_secret_values():
    if CFG('AWS_EXECUTION_ENV', None) is None:
        secret_values = CFG.PAYMENT_API_KEY
    else:  # pragma: no cover
        subhub_values = get_secret('dev/SUBHUB')
        secret_values = subhub_values['payment_api_key']
    return secret_values


def support_auth(api_token, required_scopes=None):
    secrets = json.loads(get_support_values())
    print(f'auth secrets {secrets}')
    print(f'secrets type {type(secrets)}')
    if api_token in secrets:
        return {"token": api_token}
    return None


def get_support_values():
    if CFG('AWS_EXECUTION_ENV', None) is None:
        secret_values = CFG.SUPPORT_API_KEY
    else:  # pragma: no cover
        subhub_values = get_secret('dev/SUBHUB')
        secret_values = subhub_values['support_api_key']
    return secret_values
