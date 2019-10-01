# Environment

## Important Environment Variables
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

### STRIPE_API_KEY
This value is used for production deployments as well as testing (testing key).

### USER_TABLE
This is the name of the table to be created in `dynamodb`.  Defaults to `testing` if not specified.

### LOCAL_FLASK_PORT
This value is used only when running the `subhub` flask app locally.  Defaults to `5000`.

### DYNALITE_PORT
This value is used only when running `dynalite` locally.  Defaults to `8000`.

### DYNALITE_FILE
This is the value of the file that will be written to by the `dynalite process`.  Defaults to `dynalite.out`.

### PAYMENT_API_KEY
This is the payment api key.  Defaults to `fake_payment_api_key`

### SUPPORT_API_KEY
This is the support api key.  Defaults to `fake_support_api_key`

## Other Important CFG Properties
These values are calculated and not to be set by a user.  They are mentioned here for clarity.

### DEPLOYED_ENV
The deployment environment is determined by the branch name:
- master: `prod`
- stage/*: `stage`
- qa/*: `qa`
- *: `dev`

### REPO_ROOT
This is the path to the root of the checked out `mozilla/subhub` git repo.  This value only makes sense in the git repo, not in the AWS Lambda environment.

### PROJECT_NAME
This is the project's name, `subhub`, as determined by the second part of the reposlug `mozilla/subhub`.

### PROJECT_PATH
This is the path to the project code in the git repo.  It is `REPO_PATH + PROJECT_NAME`.  It is only valid in the git repo, not in the AWS Lambda environment.

### BRANCH
This is the branch name of the deployed code.  Should be available locally as well as when deployed to AWS Lambda.

### REVISION
This is the 40 digit sha1 commit hash for the code.  This is available in the git repo as well as when deployed to AWS Lambda.

### VERSION
This is the `git describe --abbrev=7` value, useful for describing the code version.  This is available in the git repo as well as when deployed to AWS Lambda.

### PROFILING_ENABLED
This is a Boolean flag to indicate if profiling is enabled in the application.
