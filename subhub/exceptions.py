#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


class SubHubError(Exception):
    """Base SubHub Exception"""

    status_code = 500

    def __init__(self, message, status_code, payload):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        result = dict(self.payload or ())
        result["message"] = self.args[0]
        return result

    def __repr__(self):
        return f"{self.__class__.__name__}(message={self.args[0]}, status_code={self.status_code}, payload={self.payload})"

    __str__ = __repr__


class IntermittentError(SubHubError):
    """Intermittent  Exception"""

    status_code = 503

    def __init__(self, message, status_code=None, payload=None):
        super().__init__(
            message,
            status_code=status_code or IntermittentError.status_code,
            payload=payload,
        )


class ClientError(SubHubError):
    """Client  Exception"""

    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        super().__init__(
            message, status_code=status_code or ClientError.status_code, payload=payload
        )


class ServerError(SubHubError):
    """Server  Exception"""

    status_code = 500

    def __init__(self, message, status_code=None, payload=None):
        super().__init__(
            message, status_code=status_code or ServerError.status_code, payload=payload
        )


class SecretStringMissingError(Exception):
    def __init__(self, secret):
        message = f"SecretString missing from secret={secret}"
        super().__init__(message)
