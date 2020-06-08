# Environment

## Environment Configuration

The CFG object is for accessing values either from the `subhub/.env` file and|or superseded by env vars.

A value that is known to be set or have a default can be accessed:

```
CFG.SOME_VALUE
```

Otherwise the value can be accessed and given a default if it doesn't exist:

```
CFG("OTHER_VALUE", "SOME_DEFAULT")
```

These values can be enabled as an env var or listed in a `.env` in the subhub/ directory.

## Environment Variables

The environment variables as read from the application, in alphabetical order are as follows:

### ALLOWED_ORIGIN_SYSTEMS
<details>
  <summary>Learn more.</summary>

  #### Allowed Origin Systems

  This list of values provides SubHub with a way of identifying the originating sending system,
  this was developed as a way of pre-planning for future SubHub customers.

</details>

### BASKET_API_KEY
<details>
  <summary>Learn more.</summary>

  #### Basket Application Programming Interface (API) Key

  Valid API Key issued to SubHub to authenticate in API calls to the Mozilla Basket service.

</details>

### BRANCH
<details>
  <summary>Learn more.</summary>

  #### Version Control System (VCS) branch

  This is the branch name of the deployed code.  Should be available locally as well as when deployed to AWS Lambda.

</details>

### LOG_LEVEL
<details>
  <summary>Learn more.</summary>

  #### Log level of the application

  From reference 2,

  ```
  When you set a logging level in Python using the standard module, you’re telling the library you want to handle all events from that level on up. If you set the log level to INFO, it will include NOTSET, DEBUG, and INFO messages.
  ```

  ##### References
  1. [Python Logging Levels](https://docs.python.org/3/library/logging.html#logging-levels)
  2. [Ultimate Guide to Logging](https://www.loggly.com/ultimate-guide/python-logging-basics/)

</details>

### DELETED_USER_TABLE
<details>
  <summary>Learn more.</summary>

  #### Amazon Web Services, DynamoDB Users Table

  This environment variable is used for the sub and hub applications for the curation of users that have
  been deleted from the applications.  It is defaulted if not specified.  This is the common use case for
  local testing with `doit local`.

</details>

### DEPLOYED_BY
<details>
  <summary>Learn more.</summary>

  #### The name of the entity to deploy the environment.

  Ideally this would not be a human and done by a system such as a continuous deployment
  service such as TravisCI, CircleCI, or Jenkins.

</details>

### DEPLOY_DOMAIN
<details>
  <summary>Learn more.</summary>

  #### The domain entry of the deployed environment.

</details>

### DEPLOYED_ENV
<details>
  <summary>Learn more.</summary>

  #### DEPLOYED_ENV

  The deployment environment is determined by the branch name:
  - master: `prod`
  - stage/*: `stage`
  - qa/*: `qa`
  - *: `dev`

  There is a dev and fab environment available as well.  The determination of how this works in those
  cases is left open for future refinement.

</details>

### DEPLOYED_WHEN
<details>
  <summary>Learn more.</summary>

  #### DEPLOYED_WHEN

  This value provides the timestamp for when the application was deployed.

</details>


### DYNALITE_PORT
<details>
  <summary>Learn more.</summary>

   #### DYNALITE_PORT

   This value is used only when running `dynalite` locally.  Defaults to `8000`.

</details>

### DYNALITE_URL
<details>
  <summary>Learn more.</summary>

   #### DYNALITE_URL

   This configuration value is the fully qualified uniform resource
   locator (URL) for a dockerized instance of an API vending the
   AWS DynamDB interface.

</details>

### EVENT_TABLE
<details>
  <summary>Learn more.</summary>

  #### EVENT_TABLE

  This environment variable sets the name of the Amazon DynamoDB events table that is used by the hub
  application.  It is defaulted if not specified.  This is the common use case for
  local testing with `doit local`.

</details>

### FXA_SQS_URI
<details>
  <summary>Learn more.</summary>


</details>

### HUB_API_KEY
<details>
  <summary>Learn more.</summary>

  #### HUB_API_KEY

  API Key issued from Stripe to identify and validate calls originated from Stripe.

</details>

### LOCAL_FLASK_PORT
<details>
  <summary>Learn more.</summary>

  #### Flask server, local port

  This value is used only when running the `subhub` flask app locally.  It is defaulted to port, `5000`.

</details>

### NEW_RELIC_ACCOUNT_ID
<details>
  <summary>Learn more.</summary>


</details>

### NEW_RELIC_TRUSTED_ACCOUNT_ID
<details>
  <summary>Learn more.</summary>


</details>

### NEW_RELIC_SERVERLESS_MODE_ENABLED
<details>
  <summary>Learn more.</summary>


</details>

### NEW_RELIC_DISTRIBUTED_TRACING_ENABLED
<details>
  <summary>Learn more.</summary>


</details>

### PAYMENT_API_KEY
<details>
  <summary>Learn more.</summary>

  #### PAYMENT_API_KEY

  API Key issued to SubHub customers to authenticate transactions incoming to SubHub.


</details>

### PAYMENT_EVENT_LIST
<details>
  <summary>Learn more.</summary>

  #### PAYMENT_API_KEY

  List of Stripe webhook events that will be monitored by SubHub.  To be monitored
  by SubHub, the event must be in this list otherwise it will not be listened for by hub.

</details>

### PROFILING_ENABLED
<details>
  <summary>Learn more.</summary>

  #### PROFILING_ENABLED

  This is a Boolean flag to indicate if profiling is enabled in the application.

</details>

### PROJECT_NAME
<details>
  <summary>Learn more.</summary>

  #### PROJECT_NAME

  This is the project's name, `subhub`, as determined by the second part of the reposlug `mozilla/subhub`.

</details>

### REMOTE_ORIGIN_URL
<details>
  <summary>Learn more.</summary>

  #### REMOTE_ORIGIN_URL

  This is the git remote origin URL of the repository that you are presently in.

</details>

### REVISION
<details>
  <summary>Learn more.</summary>

  #### REVISION

  This is the 40 digit sha1 commit hash for the deployed code.  This is available in the git repo as well as
  when deployed to AWS Lambda.

</details>

### SALESFORCE_BASKET_URI
<details>
  <summary>Learn more.</summary>

  #### SALESFORCE_BASKET_URI

  A URL to send customer data to Mozilla Basket service.

</details>

### SRCTAR
<details>
  <summary>Learn more.</summary>


</details>

### STRIPE_LOCAL
<details>
  <summary>Learn more.</summary>


</details>

### STRIPE_MOCK_HOST
<details>
  <summary>Learn more.</summary>


</details>

### STRIPE_MOCK_PORT
<details>
  <summary>Learn more.</summary>


</details>

### STRIPE_API_KEY
<details>
  <summary>Learn more.</summary>

  #### Stripe API Key

  This value is used for production deployments as well as testing (testing key).

</details>

### SUPPORT_API_KEY
<details>
  <summary>Learn more.</summary>

  #### SUPPORT_API_KEY

  This is the support api key.  Defaults to `fake_support_api_key`

</details>

### VERSION
<details>
  <summary>Learn more.</summary>

  #### Application Version

  This is the `git describe --abbrev=7` value, useful for describing the code version.  This is available in the
  git repo as well as when deployed to AWS Lambda.

</details>
