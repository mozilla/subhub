# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
import mock

from shared.log import get_logger
from google.cloud import spanner
from shared.cfg import CFG

logger = get_logger()

@pytest.fixture
def patch_instance():
    original_instance = spanner.Client.instance

    def new_instance(self, unused_instance_name):
        return original_instance(self, CFG.SPANNER_INSTANCE)

    instance_patch = mock.patch(
        'google.cloud.spanner.Client.instance',
        side_effect=new_instance,
        autospec=True)

    with instance_patch:
        yield

@pytest.fixture
def patch_database():
    spanner_client = spanner.Client()
    instance = spanner_client.instance(CFG.SPANNER_INSTANCE)
    database = instance.database(CFG.SPANNER_DATABASE)

    if not database.exists():
        database.create()

    yield