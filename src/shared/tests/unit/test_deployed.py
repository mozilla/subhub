# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from shared.cfg import CFG
from shared.deployed import get_deployed


def test_get_deployed():
    """
    test get_deployed
    """
    expect = dict(
        DEPLOYED_BY=CFG.DEPLOYED_BY,
        DEPLOYED_ENV=CFG.DEPLOYED_ENV,
        DEPLOYED_WHEN=CFG.DEPLOYED_WHEN,
    )
    actual, rc = get_deployed()
    assert rc == 200
    assert actual["DEPLOYED_BY"] == expect["DEPLOYED_BY"]
    assert actual["DEPLOYED_ENV"] == expect["DEPLOYED_ENV"]
