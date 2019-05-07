import json

from subhub import auth_validation
from subhub.cfg import CFG


def test_payment_auth():
    api_token = 'sh_test_testkey'
    payments_auth = auth_validation.payment_auth(api_token, required_scopes=None)
    assert payments_auth is True


def test_payment_auth_bad_token():
    api_token = 'blahblah'
    payments_auth = auth_validation.payment_auth(api_token, required_scopes=None)
    assert payments_auth is None


def test_get_secrets():
    secrets = json.loads(auth_validation.get_secret_values())
    assert len(secrets) == 2


def test_support_auth():
    api_token = 'sh_test_paykey'
    support_auth = auth_validation.support_auth(api_token, None)
    assert support_auth is True


def test_support_auth_bad_token():
    api_token = 'bad_paykey'
    support_auth = auth_validation.support_auth(api_token, None)
    assert support_auth is None


def test_get_support_values():
    secrets = json.loads(auth_validation.get_support_values())
    assert len(secrets) == 2
