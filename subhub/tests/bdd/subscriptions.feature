Feature:  /v1/subscription
  As an API client
  I want an API to handle customer subscriptions.

  Background:
      Given I am using server "http://localhost:5000"
      And I am using the Stripe API located at "http://localhost:12111"
      And I set "Authorization" header to "fake_payment_api_key"
      Then I should be ready to test the API
  Scenario:
      When I send a "GET" request to "v1/customer/aliacc_1EphH5IUzFSXAEcAfYCgLj9h/subscriptions"
      Then the response status should be "404"
      And the JSON should be
            """
            {
              "message": "Customer does not exist."
            }
            """
  Scenario:
    Given I set "Content-Type" header to "application/json"
    When I send a "POST" request to "v1/customer/DOES_NOT_EXIST"
            """
            {
                "pmt_token":""
            }
            """
    Then the response status should be "404"
    And the JSON should be
            """
            {
              "message": "Customer does not exist."
            }
            """
  Scenario:
    Given I set "Content-Type" header to "application/json"
    When I send a "POST" request to "/v1/customer/cus_FSu9AT69dOjsse/subscriptions"
            """
            {
                "pmt_token":"",
                "plan_id":"plan_FSvtYLF3WH36P4",
                "email":"valid@a001ea31-2656-4ef7-948d-c541ca39d44dcustomer.com",
                "orig_system":"FXA",
                "display_name":"Jon Tester"
            }
            """
    Then the response status should be "201"
    And the JSON should be
            """
            {
              "subscriptions": [
                  {
                      "cancel_at_period_end": false,
                      "current_period_end": 1234567890,
                      "current_period_start": 1234567890,
                      "ended_at": 1234567890,
                      "plan_id": "gold",
                      "plan_name": null,
                      "status": "active",
                      "subscription_id": "sub_FKLz5hl0zyaPGd"
                  }
              ]
            }
            """