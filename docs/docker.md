# Docker

This project uses docker and docker-compose for running the project locally.  As opposed a typical docker build in which artifacts are placed into a docker container 
during the build process, this project requires external work to overcome obstacles 
with symbolic links.  This is done via the build system and can be ran via the `doit tar` task.  This method of operation though does create some unfortunate side effects of not being directly able to debug the application with tools such as the 
[GNU Project Debugger](https://www.gnu.org/software/gdb/).

## Running

You may run locally with the task, `doit local`.  This spins up a few components out of the box:

* sub
* hub
* stripe-mock
* Dynamodb mock

These components allow for isolated testing of the ensemble but comes with some caveats.  The Stripe API key for the interactions with stripe-mock should be in the 
form of `sk_test_123`.  This is required should you set the environment with the variable of `STRIPE_LOCAL` to be `true`.  If this is not set to `true` then the application will not proxy to the docker container but to `api.stripe.com`.  In this case, the application will require a `STRIPE_API_KEY` as setup from Stripe.