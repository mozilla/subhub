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
                    "amount": 0,
                    "currency": "usd",
                    "interval": "month",
                    "plan_id": "plan_FKMbsUQUfJGv2G",
                    "plan_name": "Free",
                    "product_id": "prod_EtMczoDntN9YEa",
                    "product_name": "Moz_Sub"
                },
                {
                    "amount": 100,
                    "currency": "usd",
                    "interval": "day",
                    "plan_id": "plan_F4G9jB3x5i6Dpj",
                    "plan_name": "Daily Subscription",
                    "product_id": "prod_EtMczoDntN9YEa",
                    "product_name": "Moz_Sub"
                },
                {
                    "amount": 10000,
                    "currency": "usd",
                    "interval": "year",
                    "plan_id": "plan_Ex9bCAjGvHv7Rv",
                    "plan_name": "Yearly",
                    "product_id": "prod_Ex9Z1q5yVydhyk",
                    "product_name": "Vulpes Vulpes"
                },
                {
                    "amount": 1000,
                    "currency": "usd",
                    "interval": "month",
                    "plan_id": "plan_Ex9azKcjjvGzB5",
                    "plan_name": "Monthly",
                    "product_id": "prod_Ex9Z1q5yVydhyk",
                    "product_name": "Vulpes Vulpes"
                },
                {
                    "amount": 6000,
                    "currency": "usd",
                    "interval": "year",
                    "plan_id": "plan_EuPRQDU7BxhfCD",
                    "plan_name": "Yearly",
                    "product_id": "prod_EtMczoDntN9YEa",
                    "product_name": "Moz_Sub"
                },
                {
                    "amount": 1000,
                    "currency": "usd",
                    "interval": "month",
                    "plan_id": "plan_EtMcOlFMNWW4nd",
                    "plan_name": "Mozilla_Subscription",
                    "product_id": "prod_EtMczoDntN9YEa",
                    "product_name": "Moz_Sub"
                }
            ]
            """
