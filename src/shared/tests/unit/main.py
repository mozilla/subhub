# TODO(mid): Fix the git failure when not in-tree
import test_version
import test_deployed
import test_exceptions
import test_headers
import test_secrets
import test_vendor

if __name__ == "__main__" :
    import pytest
    raise SystemExit(pytest.main([__file__]))