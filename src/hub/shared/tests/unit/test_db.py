# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from src.hub.shared.db import Database

from google.cloud import spanner
from unittest.mock import MagicMock

def test_insert_event():
    spanner.Client = MagicMock()
    database = Database()
    database.insert_event("event_id", "sent_system")
