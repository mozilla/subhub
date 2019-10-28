# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


class MockCustomer:
    id = None
    object = "customer"
    subscriptions = [{"data": "somedata"}]

    def properties(self, cls):
        return [i for i in cls.__dict__.keys() if i[:1] != "_"]

    def __contains__(self, key, default=None):
        properties = self.properties(MockCustomer)
        if key in properties:
            return key
        else:
            return default

    def get(self, key, default=None):
        properties = self.properties(MockCustomer)
        if key in properties:
            return key
        else:
            return default
