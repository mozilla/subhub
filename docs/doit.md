# [doit](http://pydoit.org/)

`doit` comes from the idea of bringing the power of build-tools to execute any kind of task
The `doit` program is used to solve a dependency of tasks just like `make` does but written in `python` for easier writing and maintaining.  It also has some capabilities that `make` does not.  Visit the website above for more details.

## Install requirements to run doit
Either of the following commands should install the minimum requirements to run `doit` and load the `CFG`

```
python3 ./dodo.py

```
```
pip3 install -r requirements.txt
```

## List tasks available to run

The list task is a built-in `doit` task that lists any functions in `dodo.py` that start with `task_` (similar to pytest, `test_`).  If this runs, `doit` is installed and working.

```
doit list
```

## Run black formatter on subhub code

This task will run the `black` code formatter on the `subhub/` directory.

```
doit black
```

## Install npm packages

The npm task installs packages defined in the `package.json` file.  These are for use with `serverless` and `dynalite`.

```
doit npm
```

## Run checks

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
- `doit check:reqs` This compares automation_requirements.txt vs what is installed via pip freeze.

## Setup the virtualenv (venv)

This task will create the virtual env and install all of the requirements for use in running code locally.

```
doit venv
```

## Dynalite

The `dynalite` `npm` package is a database webserver.

### Start dynalite

This starts, if not already running, the `dynalite process` on the `DYNALITE_PORT` (default: `8000`)

```
doit dynalite:start
```

### Stop dynalite

This stops, if already running,  the `dynalite` process on the `DYNALITE_PORT` (default: `8000`)
```
doit dynalite:stop
```

## Run locally

This task does all the steps required to get the `subhub` flask server running in docker.  This also requires ths
existence of 3 environment variables:

* STRIPE_API_KEY
* SUPPORT_API_KEY
* PAYMENT_API_KEY

Where the value of the `STRIPE_API_KEY` is not a real Stripe API key used in the system but a fake one for testing.  The
testing used `sk_test_123` as the value for validation here.
```
doit local
```

If you choose to run locally but communicate with the actual Stripe API then doit local should be pre-pended with STRIPE_LOCAL=True.
Doing this requires the use a a valid Stripe API Test key.
```
STRIPE_LOCAL=True doit local
```

## Run tests and coverage

This runs the `pytests` via `tox` and `setup.py` specifications.  Currently, `STRIPE_API_KEY` must be set for tests to run successfully.

```
doit test
```
Note: The `test` task is a dependency of `package`, `local` and `deploy` tasks, however you can skip them by setting `SKIP_TESTS=<something>`.

## Run package

This runs the `serverless package` command to zip up the `subhub` code and its dependencies.

```
doit package
```

## Ensure creds

This checks to see if `aws sts get-caller-identity` can successfully run, verifying that valid AWS credentials are present.  This is a dependency for `deploy`, the next task, to run.

```
doit creds
```

## Deploy

This run the `serverless deploy` command and requires the user to be logged into the AWS Account for `subhub`.

```
doit deploy
```

Alternatively you may deploy a subset of the `deploy` function by specifying the component as such:

```
doit deploy SERVICE FUNCTION
```

Where,
    SERVICE is the service that you are deploying from the set of fxa.
    FUNCTION is the function that you are deploying from the set of sub, hub, mia.
