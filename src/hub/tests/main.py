import src.hub.tests.unit.test_stripe_controller
import src.hub.tests.unit.stripe.charge.test_stripe_charge
import src.hub.tests.unit.stripe.customer.test_stripe_customer
import src.hub.tests.unit.stripe.event.test_stripe_events
import src.hub.tests.unit.stripe.invoice.test_stripe_invoice
import src.hub.tests.unit.stripe.payment.test_stripe_payments

if __name__ == "__main__" :
    import pytest
    raise SystemExit(pytest.main([__file__]))