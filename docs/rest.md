# RESTful Interactions

## Swagger User Interface

Navigate to `http://127.0.0.1:5000/v1/ui/` in a browser of choice.


## Get Hub function version
```
curl --silent http://127.0.0.1:5001/v1/hub/version
{
  "BRANCH": "CURRENT_BRANCH",
  "REVISION": "CURRENT_REVISION",
  "VERSION": "CURRENT_VERSION"
}
```

Where,

  * `CURRENT_BRANCH` is the currently deployed branch
  * `CURRENT_REVISION` is the currently deployed revision
  * `CURRENT_VERSION` is the currently deployed version

## Get Hub function deployment information
```
curl --silent http://127.0.0.1:5001/v1/hub/deployed
{
  "DEPLOYED_BY": "root@7259f8263190",
  "DEPLOYED_ENV": "local",
  "DEPLOYED_WHEN": "2019-09-17T14:14:04.975523"
}
```

## Postman

A [Postman](https://www.getpostman.com/) URL collection is available for testing, learning,
etc [here](https://www.getpostman.com/collections/ab233178aa256e424668).
