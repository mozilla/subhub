# Serverless

## Commands

From this (`services/fxa`) directory, execute the following commands of interest.  NOTE:  If you require extra detail of the Serverless framework,
you will need to set the follow environment variable.

`export SLS_DEBUG=*`

### Offline Testing

`serverless offline start`

Once this is done, you can access the DynamoDB Javascript Shell by 
navigating [here](http://localhost:8000/shell/).  Additionally, you may interact with the application as you would on AWS via commands such as:
  * Perform a HTTP GET of `http://localhost:3000/v1/sub/version`

### Domain Creation

`sls create_domain`

### Packaging

`sls package`

You may inspect the contents of each packages with:

`zipinfo .serverless/{ARCHIVE}.zip`

Where `ARCHIVE` is a member of

* sub
* hub
* mia

### Logs

You can inspect the Serverless logs by function via the command:

`sls logs -f {FUNCTION}`

Where `FUNCTION` is a member of

* sub
* hub
* mia

#### Live Tailing of the Logs

`serverless logs -f {FUNCTION} --tail`

### Running

`sls wsgi serve`

### To-do

* [Investigate Serverless Termination Protection for Production](https://www.npmjs.com/package/serverless-termination-protection)
* [Investigate metering requests via apiKeySourceType](https://serverless.com/framework/docs/providers/aws/events/apigateway/)

## References

1. [SLS_DEBUG](https://github.com/serverless/serverless/pull/1729/files)
2. [API Gateway Resource Policy Support](https://github.com/serverless/serverless/issues/4926)
3. [Add apig resource policy](https://github.com/serverless/serverless/pull/5071)
4. [add PRIVATE endpointType](https://github.com/serverless/serverless/pull/5080)
5. [Serverless AWS Lambda Events](https://serverless.com/framework/docs/providers/aws/events/)