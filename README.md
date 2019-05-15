# subhub
payment subscription REST api for FxA (Firefox Accounts)

## doit
http://pydoit.org/

doit comes from the idea of bringing the power of build-tools to execute any kind of task

## install requirements to run doit
```
pip3 install -r requirements.txt
```

## list tasks available to run
```
doit list
```

## package
```
doit package
```

## deploy
```
doit deploy
```

## Running locally for development

### Ubuntu (including WSL)

* Install Docker host & tools
  * [Some tips for using Docker with Windows & WSL][docker-wsl-tips]

[docker-wsl-tips]: https://nickjanetakis.com/blog/setting-up-docker-for-windows-and-wsl-to-work-flawlessly

* Install system prerequisites

  ```zsh
  sudo apt-get install python3.7 python3.7-dev python3-venv
  ```

* Install Python prerequisites

  ```zsh
  python3 -m venv venv
  . ./venv/bin/activate
  pip install -r ./requirements.txt
  pip install -r ./subhub/requirements.txt
  ```

* Start up a local DynamoDB server

  ```zsh
  docker run -p 8011:8000 amazon/dynamodb-local
  ```

* Acquire [Stripe API keys for testing][stripe-testing]

[stripe-testing]: https://stripe.com/docs/keys#test-live-modes

* Start up a subhub dev server

  ```zsh
  PORT=8012 \
  DBD_HOST=http://localhost:8011 \
  USER_TABLE=subhub-dev \
  PAYMENT_API_KEY=abcde \
  STRIPE_API_KEY=sk_test_THIS_IS_NOT_A_REAL_KEY \
  python -m subhub.app
  ```

  * `PORT` is the local HTTP server port for the API
  * `DBD_HOST` is the URL for the local DynamoDB server
  * `USER_TABLE` is the name of the table to be used on the local DynamoDB server
  * `PAYMENT_API_KEY` is the API key expected for header authentication
  * `STRIPE_API_KEY` is the secret key to use for calls to the Stripe API (i.e. not the publishable key)

* Visit the Swagger UI at <http://localhost:8012/v1/ui>

* Try out the API

  ```zsh
  ➜  subhub git:(master) ✗ curl -H'Authorization: abcde' 'http://127.0.0.1:8012/v1/plans'
  [
    {
      "amount": 86700,
      "currency": "usd",
      "interval": "month",
      "nickname": "123Done Pro Monthly",
      "plan_id": "plan_F4bof27uz71Vk7",
      "product_id": "prod_F4boDmwsxbSyRc"
    }
  ]
  ```
