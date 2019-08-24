# Performance

This directory contains the performance test framework for Subhub.

## Running the Performance Tests

After provisioning `doit` per the root directory's README.md` file:

* `doit remote_perf`: This command runs the performance tests against a deployed
instance of the application running at the configuration value of `CFG.DEPLOY_DOMAIN`.
* `doit perf`: This command starts a local instance of the hub.application and also
instance of the performance test running against it.

## Author(s)

Stewart Henderson