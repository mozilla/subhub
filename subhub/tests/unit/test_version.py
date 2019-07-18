from subhub.cfg import CFG
from subhub.api.version import get_version


def test_get_version():
    """
    test get_version
    """
    assert get_version() == ({"message": CFG.VERSION}, 200)
