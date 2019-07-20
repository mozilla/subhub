from subhub.exceptions import SecretStringMissingError


def test_SecretStringMissingError():
    secret = {"foo": "bar", "baz": "qux"}
    error = SecretStringMissingError(secret)
    assert error
