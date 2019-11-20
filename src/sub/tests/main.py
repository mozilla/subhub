# import conftest
import src.sub.tests.unit.test_app
import src.sub.tests.unit.test_authentication
import src.sub.tests.unit.test_cfg
import src.sub.tests.unit.test_customer
import src.sub.tests.unit.test_messages
import src.sub.tests.unit.test_payment_calls
import src.sub.tests.unit.test_payment_mock
import src.sub.tests.unit.test_payments
import src.sub.tests.unit.test_subhub

if __name__ == "__main__" :
    import pytest
    raise SystemExit(pytest.main([__file__]))