# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import sys
import pytest

from flask import g

from src.hub.shared.cfg import CFG
from src.hub.app import create_app
from src.hub.shared.log import get_logger
# from src.hub.shared.dynamodb import patch_database

logger = get_logger()


# def pytest_configure():
#     os.environ["ALLOWED_ORIGIN_SYSTEMS"] = "Test_system,Test_System,Test_System1"
#     sys._called_from_test = True
#
#
# @pytest.fixture(autouse=True, scope="module")
# def app(patch_database):
#     app = create_app()
#     with app.app.app_context():
#         yield app
