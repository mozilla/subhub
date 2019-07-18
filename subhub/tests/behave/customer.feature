Feature:  /v1/customer
  As an API client
  I want an API to support customer interactions.

  Background:
      Given I am using server "http://localhost:5000"
      And I set "Authorization" header to "fake_payment_api_key"
      Then I should be ready to test the API
  Scenario:
      When I send a "DELETE" request to "v1/customer/DOES_NOT_EXIST"
      Then the response status should be "404"
      And the JSON should be
            """
            {
              "message": "Customer does not exist."
            }
            """
