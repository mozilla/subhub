Feature:  /v1/plans
  As an API client
  I want an endpoint to interact with plan entities.

  Background:
      Given I am using server "http://localhost:5000"
      And I am using the Stripe API located at "http://localhost:12111"
      And I set "Authorization" header to "fake_payment_api_key"
      Then I should be ready to test the API
  Scenario:
      When I send a "GET" request to "v1/plans"
      Then the response status should be "200"
      And the JSON should be
            """
            [
                {
                    "amount": 2000,
                    "currency": "usd",
                    "interval": "month",
                    "plan_id": "gold",
                    "plan_name": null,
                    "product_id": "prod_FJaYU37yVcOAWH",
                    "product_name": "Gold Special"
                }
            ]
            """
