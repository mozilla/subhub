# Subhub Behave Tests

This directory provides [behave](https://github.com/behave/behave) tests for the subhub API.  

## Prerequisites

* [stripe-mock](https://github.com/stripe/stripe-mock)

When using [homebrew](https://brew.sh/), you can leverage the command, 

`brew install stripe/stripe-mock/stripe-mock`

## Configuration

This test can be configured to run against either Stripe or a Stripe mock instance in the [behave.ini](./behave.ini) 
file.  This requires the configuration of 2 variables:

* stripe_api_base: This is the base address consisting of the schema and authority.  This variable excludes any fragment 
beyond authority such as path, query, or fragment.
* stripe_api_key: This is the secret key to be used by the application from either Stripe or stripe-mock


## Running

1. Start the `stripe-mock` process.

2. Start the `doit local` command to start the local server.

3. From one of the following command line statements from the repository root directory:

### Execute a single feature file

```
behave subhub/tests/behave/subscriptions.feature 
Feature: /v1/subscription # subhub/tests/behave/subscriptions.feature:1
  As an API client
  I want an API to handle customer subscriptions.
  Background:   # subhub/tests/behave/subscriptions.feature:5

  Scenario:                                                                                    # subhub/tests/behave/subscriptions.feature:10
    Given I am using server "http://localhost:5000"                                            # subhub/tests/behave/steps/rest_steps.py:15 0.000s
    And I am using the Stripe API located at "http://localhost:12111"                          # subhub/tests/behave/steps/stripe_steps.py:7 0.000s
    And I set "Authorization" header to "fake_payment_api_key"                                 # subhub/tests/behave/steps/rest_steps.py:20 0.000s
    Then I should be ready to test the API                                                     # subhub/tests/behave/steps/rest_steps.py:36 0.000s
    When I send a "GET" request to "v1/customer/aliacc_1EphH5IUzFSXAEcAfYCgLj9h/subscriptions" # subhub/tests/behave/steps/rest_steps.py:66 0.011s
    Then the response status should be "404"                                                   # subhub/tests/behave/steps/rest_steps.py:58 0.000s
    And the JSON should be                                                                     # subhub/tests/behave/steps/rest_steps.py:79 0.000s
      """
      {
        "message": "Customer does not exist."
      }
      """

  Scenario:                                                           # subhub/tests/behave/subscriptions.feature:19
    Given I am using server "http://localhost:5000"                   # subhub/tests/behave/steps/rest_steps.py:15 0.000s
    And I am using the Stripe API located at "http://localhost:12111" # subhub/tests/behave/steps/stripe_steps.py:7 0.000s
    And I set "Authorization" header to "fake_payment_api_key"        # subhub/tests/behave/steps/rest_steps.py:20 0.000s
    Then I should be ready to test the API                            # subhub/tests/behave/steps/rest_steps.py:36 0.000s
    Given I set "Content-Type" header to "application/json"           # subhub/tests/behave/steps/rest_steps.py:20 0.000s
    When I send a "POST" request to "v1/customer/DOES_NOT_EXIST"      # subhub/tests/behave/steps/rest_steps.py:66 0.008s
      """
      {
          "pmt_token":""
      }
      """
    Then the response status should be "404"                          # subhub/tests/behave/steps/rest_steps.py:58 0.000s
    And the JSON should be                                            # subhub/tests/behave/steps/rest_steps.py:79 0.000s
      """
      {
        "message": "Customer does not exist."
      }
      """

  Scenario:                                                                         # subhub/tests/behave/subscriptions.feature:34
    Given I am using server "http://localhost:5000"                                 # subhub/tests/behave/steps/rest_steps.py:15 0.000s
    And I am using the Stripe API located at "http://localhost:12111"               # subhub/tests/behave/steps/stripe_steps.py:7 0.000s
    And I set "Authorization" header to "fake_payment_api_key"                      # subhub/tests/behave/steps/rest_steps.py:20 0.000s
    Then I should be ready to test the API                                          # subhub/tests/behave/steps/rest_steps.py:36 0.000s
    Given I set "Content-Type" header to "application/json"                         # subhub/tests/behave/steps/rest_steps.py:20 0.000s
    When I send a "POST" request to "/v1/customer/cus_FSu9AT69dOjsse/subscriptions" # subhub/tests/behave/steps/rest_steps.py:66 0.025s
      """
      {
          "pmt_token":"",
          "plan_id":"plan_FSvtYLF3WH36P4",
          "email":"valid@a001ea31-2656-4ef7-948d-c541ca39d44dcustomer.com",
          "orig_system":"FXA",
          "display_name":"Jon Tester"
      }
      """
    Then the response status should be "201"                                        # subhub/tests/behave/steps/rest_steps.py:58 0.000s
    And the JSON should be                                                          # subhub/tests/behave/steps/rest_steps.py:79 0.000s
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

1 feature passed, 0 failed, 0 skipped
3 scenarios passed, 0 failed, 0 skipped
23 steps passed, 0 failed, 0 skipped, 0 undefined
Took 0m0.047s
```

### Execute all features

```
behave subhub/tests/behave
Feature: /v1/plans # subhub/tests/behave/plans.feature:1
  As an API client
  I want an endpoint to interact with plan entities.
  Background:   # subhub/tests/behave/plans.feature:5

  Scenario:                                                           # subhub/tests/behave/plans.feature:10
    Given I am using server "http://localhost:5000"                   # subhub/tests/behave/steps/rest_steps.py:15 0.000s
    And I am using the Stripe API located at "http://localhost:12111" # subhub/tests/behave/steps/stripe_steps.py:7 0.000s
    And I set "Authorization" header to "fake_payment_api_key"        # subhub/tests/behave/steps/rest_steps.py:20 0.000s
    Then I should be ready to test the API                            # subhub/tests/behave/steps/rest_steps.py:36 0.000s
    When I send a "GET" request to "v1/plans"                         # subhub/tests/behave/steps/rest_steps.py:66 0.011s
    Then the response status should be "200"                          # subhub/tests/behave/steps/rest_steps.py:58 0.000s
    And the JSON should be                                            # subhub/tests/behave/steps/rest_steps.py:79 0.000s
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

Feature: /v1/subscription # subhub/tests/behave/subscriptions.feature:1
  As an API client
  I want an API to handle customer subscriptions.
  Background:   # subhub/tests/behave/subscriptions.feature:5

  Scenario:                                                                                    # subhub/tests/behave/subscriptions.feature:10
    Given I am using server "http://localhost:5000"                                            # subhub/tests/behave/steps/rest_steps.py:15 0.000s
    And I am using the Stripe API located at "http://localhost:12111"                          # subhub/tests/behave/steps/stripe_steps.py:7 0.000s
    And I set "Authorization" header to "fake_payment_api_key"                                 # subhub/tests/behave/steps/rest_steps.py:20 0.000s
    Then I should be ready to test the API                                                     # subhub/tests/behave/steps/rest_steps.py:36 0.000s
    When I send a "GET" request to "v1/customer/aliacc_1EphH5IUzFSXAEcAfYCgLj9h/subscriptions" # subhub/tests/behave/steps/rest_steps.py:66 0.009s
    Then the response status should be "404"                                                   # subhub/tests/behave/steps/rest_steps.py:58 0.000s
    And the JSON should be                                                                     # subhub/tests/behave/steps/rest_steps.py:79 0.000s
      """
      {
        "message": "Customer does not exist."
      }
      """

  Scenario:                                                           # subhub/tests/behave/subscriptions.feature:19
    Given I am using server "http://localhost:5000"                   # subhub/tests/behave/steps/rest_steps.py:15 0.000s
    And I am using the Stripe API located at "http://localhost:12111" # subhub/tests/behave/steps/stripe_steps.py:7 0.000s
    And I set "Authorization" header to "fake_payment_api_key"        # subhub/tests/behave/steps/rest_steps.py:20 0.000s
    Then I should be ready to test the API                            # subhub/tests/behave/steps/rest_steps.py:36 0.000s
    Given I set "Content-Type" header to "application/json"           # subhub/tests/behave/steps/rest_steps.py:20 0.000s
    When I send a "POST" request to "v1/customer/DOES_NOT_EXIST"      # subhub/tests/behave/steps/rest_steps.py:66 0.008s
      """
      {
          "pmt_token":""
      }
      """
    Then the response status should be "404"                          # subhub/tests/behave/steps/rest_steps.py:58 0.000s
    And the JSON should be                                            # subhub/tests/behave/steps/rest_steps.py:79 0.000s
      """
      {
        "message": "Customer does not exist."
      }
      """

  Scenario:                                                                         # subhub/tests/behave/subscriptions.feature:34
    Given I am using server "http://localhost:5000"                                 # subhub/tests/behave/steps/rest_steps.py:15 0.000s
    And I am using the Stripe API located at "http://localhost:12111"               # subhub/tests/behave/steps/stripe_steps.py:7 0.000s
    And I set "Authorization" header to "fake_payment_api_key"                      # subhub/tests/behave/steps/rest_steps.py:20 0.000s
    Then I should be ready to test the API                                          # subhub/tests/behave/steps/rest_steps.py:36 0.000s
    Given I set "Content-Type" header to "application/json"                         # subhub/tests/behave/steps/rest_steps.py:20 0.000s
    When I send a "POST" request to "/v1/customer/cus_FSu9AT69dOjsse/subscriptions" # subhub/tests/behave/steps/rest_steps.py:66 0.023s
      """
      {
          "pmt_token":"",
          "plan_id":"plan_FSvtYLF3WH36P4",
          "email":"valid@a001ea31-2656-4ef7-948d-c541ca39d44dcustomer.com",
          "orig_system":"FXA",
          "display_name":"Jon Tester"
      }
      """
    Then the response status should be "201"                                        # subhub/tests/behave/steps/rest_steps.py:58 0.000s
    And the JSON should be                                                          # subhub/tests/behave/steps/rest_steps.py:79 0.000s
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

Feature: /v1/version # subhub/tests/behave/version.feature:1
  As an API client
  I want to be able to acquire the version of the deployed application
  Background:   # subhub/tests/behave/version.feature:5

  Scenario:                                         # subhub/tests/behave/version.feature:9
    Given I am using server "http://localhost:5000" # subhub/tests/behave/steps/rest_steps.py:15 0.000s
    And I set "Accept" header to "application/json" # subhub/tests/behave/steps/rest_steps.py:20 0.000s
    Then I should be ready to test the API          # subhub/tests/behave/steps/rest_steps.py:36 0.000s
    When I send a "GET" request to "v1/version"     # subhub/tests/behave/steps/rest_steps.py:66 0.066s
    Then the response status should be "200"        # subhub/tests/behave/steps/rest_steps.py:58 0.000s

3 features passed, 0 failed, 0 skipped
5 scenarios passed, 0 failed, 0 skipped
35 steps passed, 0 failed, 0 skipped, 0 undefined
Took 0m0.121s
```

#### Notes

You may generate `JUnit` style reports by adding the `--junit` option to the above `behave` commands.

## Author(s)

Stewart Henderson