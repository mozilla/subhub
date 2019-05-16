#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from subhub.exceptions import SubHubError, IntermittentError, ClientError, ServerError


def test_SubHubError():
    message = "message"
    status_code = 513
    payload = dict(some="payload")
    ex = SubHubError(message, status_code=status_code, payload=payload)
    assert (
        str(ex)
        == "SubHubError(message=message, status_code=513, payload={'some': 'payload'})"
    )


def test_IntermittentError():
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


def test_ClientError():
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


def test_ServerError():
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
