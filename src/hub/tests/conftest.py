# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import sys
import signal
import subprocess
import logging
import psutil
import pytest
import stripe

from flask import g

from hub.shared.cfg import CFG
from hub.app import create_app
from shared.log import get_logger
from shared.dynamodb import dynamodb

logger = get_logger()


def pytest_configure():
    # Latest boto3 now wants fake credentials around, so here we are.
    os.environ["AWS_ACCESS_KEY_ID"] = "fake"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "fake"
    os.environ["EVENT_TABLE"] = "events-testing"
    os.environ["ALLOWED_ORIGIN_SYSTEMS"] = "Test_system,Test_System,Test_System1"
    sys._called_from_test = True


@pytest.fixture(autouse=True, scope="module")
def app(dynamodb):
    os.environ["DYNALITE_URL"] = dynamodb
    app = create_app()
    with app.app.app_context():
        g.hub_table = app.app.hub_table
        g.subhub_deleted_users = app.app.subhub_deleted_users
        yield app