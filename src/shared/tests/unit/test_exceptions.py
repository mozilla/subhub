# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from sub.shared.exceptions import (
    SubHubError,
    IntermittentError,
    ClientError,
    EntityNotFoundError,
    ValidationError,
    ServerError,
    SecretStringMissingError,
)

from hub.shared.exceptions import SubHubError as HubError


def test_subhub_error():
    message = "message"
    status_code = 513
    payload = dict(some="payload")
    ex = SubHubError(message, status_code=status_code, payload=payload)
    assert (
        str(ex)
        == "SubHubError(message=message, status_code=513, payload={'some': 'payload'})"
    )


def test_hub_error():
    message = "message"
    status_code = 513
    payload = dict(some="payload")
    ex = HubError(message, status_code=status_code, payload=payload)
    assert (
        str(ex)
        == "SubHubError(message=message, status_code=513, payload={'some': 'payload'})"
    )


def test_intermittent_error():
    message = "message"
    ex1 = IntermittentError(message)
    assert ex1.args[0] == message
    assert ex1.payload == None
    assert ex1.status_code == IntermittentError.status_code
    assert ex1.to_dict() == dict(message=message)

    status_code = 513
    payload = dict(some="payload")
    ex2 = IntermittentError(message, status_code=status_code, payload=payload)
    assert ex2.args[0] == message
    assert ex2.payload == payload
    assert ex2.status_code == status_code
    assert ex2.to_dict() == dict(message=message, some="payload")


def test_client_error():
    message = "message"
    ex1 = ClientError(message)
    assert ex1.args[0] == message
    assert ex1.payload == None
    assert ex1.status_code == ClientError.status_code
    assert ex1.to_dict() == dict(message=message)

    status_code = 513
    payload = dict(some="payload")
    ex2 = ClientError(message, status_code=status_code, payload=payload)
    assert ex2.args[0] == message
    assert ex2.payload == payload
    assert ex2.status_code == status_code
    assert ex2.to_dict() == dict(message=message, some="payload")


def test_entity_not_found_error():
    message = "Entity not found"
    error_number = 4000
    error = EntityNotFoundError(message, error_number)

    assert error.payload == {"errno": error_number}
    assert error.status_code == 404
    assert error.to_dict() == dict(message=message, errno=error_number)


def test_validation_error():
    message = "Validation error"
    error_number = 1000
    error = ValidationError(message, error_number)

    assert error.payload == {"errno": error_number}
    assert error.status_code == 400
    assert error.to_dict() == dict(message=message, errno=error_number)


def test_server_error():
    message = "message"
    ex1 = ServerError(message)
    assert ex1.args[0] == message
    assert ex1.payload == None
    assert ex1.status_code == ServerError.status_code
    assert ex1.to_dict() == dict(message=message)

    status_code = 513
    payload = dict(some="payload")
    ex2 = ServerError(message, status_code=status_code, payload=payload)
    assert ex2.args[0] == message
    assert ex2.payload == payload
    assert ex2.status_code == status_code
    assert ex2.to_dict() == dict(message=message, some="payload")


def test_SecretStringMissingError():
    secret = {"foo": "bar", "baz": "qux"}
    error = SecretStringMissingError(secret)
    assert error
