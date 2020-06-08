# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
from typing import Dict, Any

from cloudsecrets.aws import Secrets
from shared.cfg import CFG


def get_secret(secret_id) -> Dict[str, Any]:
    secrets = Secrets(f"{CFG.DEPLOYED_ENV}/{CFG.PROJECT_NAME}", version="latest")
    return dict(secrets).get(secret_id)


if CFG.AWS_EXECUTION_ENV:
    os.environ.update(get_secret(f"{CFG.DEPLOYED_ENV}/{CFG.PROJECT_NAME}"))
