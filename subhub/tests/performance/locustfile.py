# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import random

from locust import TaskSet, HttpLocust, task, seq_task


class Plans(TaskSet):
    def on_start(self):
        with open("payment_api_keys") as f:
            self.payment_api_keys = f.read().splitlines()

    @task
    def get(self):
        headers = {
            "Content-Type": "application/json",
            "Authorization": str(random.choice(self.payment_api_keys)),
        }
        self.client.get("/v1/plans", headers=headers)


class Subscriptions(TaskSet):
    def on_start(self):
        with open("uids") as f:
            self.uids = f.read().splitlines()
        with open("payment_api_keys") as f:
            self.payment_api_keys = f.read().splitlines()

    @task
    @seq_task(1)
    def create(self):
        headers = {"Authorization": str(random.choice(self.payment_api_keys))}
        self.client.post(
            f"/v1/customer/{str(random.choice(self.uids))}/subscriptions",
            {
                "pmt_token": "",
                "plan_id": "1",
                "email": "shenderson@mozilla.com",
                "orig_system": "FXA",
                "display_name": "Big Spender Account",
            },
            headers=headers,
        )

    @task
    @seq_task(2)
    def get(self):
        self.client.get(f"/v1/customer/{str(random.choice(self.uids))}/subscriptions")


class Version(TaskSet):
    def on_start(self):
        self.headers = {"Content-Type": "application/json"}

    @task
    def get(self):
        self.client.get("/v1/version", headers=self.headers)


class SubhubCustomerWorkflow(TaskSet):
    tasks = {Plans: 10, Subscriptions: 10, Version: 10}

    def on_start(self):
        with open("payment_api_keys") as f:
            self.payment_api_keys = f.read().splitlines()

    def on_stop(self):
        print("stopping subhub performance testing")


class WebsiteUser(HttpLocust):
    task_set = SubhubCustomerWorkflow
    host = "http://localhost:5000"
    stop_timeout = 20
    min_wait = 100
    max_wait = 1500
