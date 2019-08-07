# SubHub

[![Build Status](https://travis-ci.org/mozilla/subhub.svg?branch=master)](https://travis-ci.org/mozilla/subhub)

Payment subscription REST api for customers:
- FxA (Firefox Accounts)

## Required Software
- python3.7: requires python3.7 interpreter for creating virtual envionments for testing and running subhub
- yarn (https://yarnpkg.com): package manager for node modules for setting up serverless for running and deploying subhub
- cloc
- [GraphViz](https://graphviz.org/)

## Important Environment Variables
The CFG object is for accessing values either from the `subhub/.env` file and|or superceeded by env vars.
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
This value is used for producion deployments as well as testing (testing key).

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
This is the Boolean flag to indicate if profiling is enabled in the application.

## doit
http://pydoit.org/

`doit` comes from the idea of bringing the power of build-tools to execute any kind of task
The `doit` program is used to solve a dependency of tasks just like `make` does but written in `python` for easier writing and maintaining.  It also has some capabilities that `make` does not.  Visit the website above for more details.

## install requirements to run doit
Either of the following commands should install the minimum requirements to run `doit` and load the `CFG`
```
python3 ./dodo.py
```
```
pip3 install -r requirements.txt
```

## list tasks available to run
The list task is a built-in `doit` task that lists any functions in `dodo.py` that start with `task_` (similar to pytest, `test_`).  If this runs, `doit` is installed and working.
```
doit list
```

## run black formatter on subhub code
This task will run the `black` code formatter on the `subhub/` directory.
```
doit black
```

## install npm packages
The npm task installs packages defined in the `package.json` file.  These are for use with `serverless` and `dyanlite`.
```
doit npm
```

## run checks
These are a series of checks which help ensure that the system is in good order to run other `doit` tasks.
```
doit check
```
Running `doit check` will run all of the subtasks listed below.

The `check` task have several subtasks:

- `doit check:noroot` This makes sure the doit command is not run as a root user.
- `doit check:python3.7` This makes sure the python3.7 interpreter is installed.
- `doit check:awscli` This makes sure the awscli is installed (unless running in travis-ci)
- `doit check:json` This makes sure all of the json files in the git repo can be loaded.
- `doit check:yaml` This makes sure all of the yaml files in the git repo can be loaded.
- `doit check:black` This runs `black --check` to ensure formatting.
- `doit check:reqs` This compares subhub/requirements.txt vs what is installed via pip freeze.

## setup the virtualenv (venv)
This task will create the virtual env and install all of the requirements for use in running code locally.
```
doit venv
```

## dynalite
The `dynalite` `npm` package is a database webserver.

### start dynalite
This starts, if not already running, the `dynalite process` on the `DYNALITE_PORT` (default: `8000`)
```
doit dynalite:start
```

### stop dynalite
This stops, if already running,  the `dynalite` process on the `DYNALITE_PORT` (default: `8000`)
```
doit dynalite:stop
```

## run locally
This task does all the steps required to get the `subhub` flask server running in a venv.
```
doit local
```

## run tests and coverage
This runs the `pytests` via `tox` and `setup.py` specifications.  Currently, `STRIPE_API_KEY` must be set for tests to run successfully.
```
doit test
```
Note: The `test` task is a dependency of `package`, `local` and `deploy` tasks, however you can skip them by setting `SKIP_TESTS=<something>`.

## run package
This runs the `serverless package` command to zip up the `subhub` code and its dependencies.
```
doit package
```

## ensure creds
This checks to see if `aws sts get-caller-identity` can successfully run, verifying that valid AWS credentials are present.  This is a dependency for `deploy`, the next task, to run.
```
doit creds
```

## deploy
This run the `serverless deploy` command and requires the user to be logged into the AWS Account for `subhub`.
```
doit deploy
```

## dependency graph
This command will generate a GraphViz `dot` file that can be used to generate a media file.
```
doit graph
```

## dependency graph image 
This command will generate a PNG of the dependency graph.
```
doit draw
```

### Docker
* build: `docker build -t mozilla/subhub .`
* run: `docker run -it mozilla/subhub`

### Docker Compose
* build and run: `docker-compose up --build`
* run: `docker-compose up`

## Postman

A [Postman](https://www.getpostman.com/) URL collection is available for testing, learning,
etc [here](https://www.getpostman.com/collections/ab233178aa256e424668).

## [Performance Tests](./subhub/tests/performance/README.md)

## Behave Tests

The `behave` tests for this project are located in the `subhub/tests/bdd` directory.  The
steps that are available presently are available in the `steps`subdirectory.  You can run this in a
few ways:
  * Jetbrain's PyCharm: A runtime configuration is loaded in that allows for debugging and running of the feature files.
  * Command line: `cd subhub/tests/bdd && behave` after satisfying the `requirements.txt` in that directory.