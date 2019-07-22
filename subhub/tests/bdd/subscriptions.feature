Feature:  /v1/subscription
  As an API client
  I want an API to handle customer subscriptions.

  Background:
      Given I am using server "http://localhost:5000"
      And I set "Authorization" header to "fake_payment_api_key"
      Then I should be ready to test the API
  Scenario:
      When I send a "GET" request to "v1/customer/DOES_NOT_EXIST/subscriptions"
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
