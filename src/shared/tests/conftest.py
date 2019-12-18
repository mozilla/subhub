# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import sys
import signal
import subprocess
import uuid
import logging
import json
import psutil
import pytest
import stripe

from unittest.mock import Mock, MagicMock, PropertyMock

from sub.shared.cfg import CFG
from shared.log import get_logger
from shared.dynamodb import dynamodb


logger = get_logger()

THIS_PATH = os.path.join(os.path.realpath(os.path.dirname(__file__)))


def pytest_configure():
    os.environ["AWS_ACCESS_KEY_ID"] = "fake"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "fake"
