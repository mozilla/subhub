from subhub import auth_validation
from subhub.cfg import CFG


def test_payment_auth():
    payments_auth = auth_validation.payment_auth(
        "fake_payment_api_key", required_scopes=None
    )
    assert payments_auth["value"] is True


def test_payment_auth_bad_token():
    payments_auth = auth_validation.payment_auth(
        "bad_payment_api_key", required_scopes=None
    )
    assert payments_auth is None


def test_support_auth():
    support_auth = auth_validation.support_auth("fake_support_api_key", None)
    assert support_auth["value"] is True


def test_support_auth_bad_token():
    support_auth = auth_validation.support_auth("bad_support_api_key", None)
    assert support_auth is None
