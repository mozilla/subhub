Feature:  /v1/version
  As an API client
  I want to be able to acquire the version of the deployed application

  Background:
      Given I am using server "http://localhost:5000"
      And I set "Accept" header to "application/json"
      Then I should be ready to test the API
  Scenario:
      When I send a "GET" request to "v1/version"
      Then the response status should be "200"
      And the JSON should be
            """
            {
                "message": "v0.0.2-170-ga176b6d"
            }
            """

