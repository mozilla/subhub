# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from sub.shared.version import get_version
from sub.shared.cfg import CFG


def test_get_version():
    """
    test get_version
    """
    version = dict(BRANCH=CFG.BRANCH, VERSION=CFG.VERSION, REVISION=CFG.REVISION)
    assert get_version() == (version, 200)
