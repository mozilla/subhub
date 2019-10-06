# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import json
import os
import sys
import signal
import subprocess
import logging

import backoff
import docker
import psutil
import pytest
import requests
import stripe
from flask import g

from hub.app import create_app
from hub.shared.cfg import CFG
from shared.log import get_logger

logger = get_logger()

IMAGE = "vitarn/dynalite:latest"
CONTAINERS_FOR_TESTING_LABEL = "pytest_docker_log"


def _docker_client():
    return docker.DockerClient("unix://var/run/docker.sock", version="auto")


def pytest_configure():
    """Called before testing begins"""
    global ddb_process
    for name in ("boto3", "botocore"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    if os.getenv("AWS_LOCAL_DYNAMODB") is None:
        os.environ["AWS_LOCAL_DYNAMODB"] = f"http://127.0.0.1:{CFG.DYNALITE_PORT}"

    # Latest boto3 now wants fake credentials around, so here we are.
    os.environ["AWS_ACCESS_KEY_ID"] = "fake"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "fake"
    os.environ["EVENT_TABLE"] = "events-testing"
    os.environ["ALLOWED_ORIGIN_SYSTEMS"] = "Test_system,Test_System,Test_System1"
    sys._called_from_test = True


def get_free_tcp_port():
    import socket

    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.bind(("", 0))
    addr, port = tcp.getsockname()
    tcp.close()
    return port


def _docker_client():
    return docker.from_env()


def pull_image(image):
    docker_client = _docker_client()
    response = docker_client.api.pull(image)
    lines = [line for line in response.splitlines() if line]
    pull_result = json.loads(lines[-1])
    if "error" in pull_result:
        raise Exception("Could not pull {}: {}".format(image, pull_result["error"]))


@pytest.yield_fixture(scope="module", autouse=True)
def dynamodb():
    pull_image(IMAGE)
    docker_client = _docker_client()
    host_port = get_free_tcp_port()
    port_bindings = {4567: host_port}
    host_config = docker_client.api.create_host_config(port_bindings=port_bindings)
    container = docker_client.api.create_container(
        image=IMAGE,
        labels=[CONTAINERS_FOR_TESTING_LABEL],
        host_config=host_config,
        ports=[4567],
    )
    docker_client.api.start(container=container["Id"])
    container_info = docker_client.api.inspect_container(container.get("Id"))

    host_ip = container_info["NetworkSettings"]["Ports"]["4567/tcp"][0]["HostIp"]
    host_port = container_info["NetworkSettings"]["Ports"]["4567/tcp"][0]["HostPort"]
    yield f"http://{host_ip}:{host_port}"
    docker_client.api.remove_container(container=container["Id"], force=True)


@backoff.on_exception(backoff.fibo, Exception, max_tries=8)
def _check_container(url):
    return requests.get(url)


@pytest.fixture(autouse=True, scope="module")
def app(dynamodb):
    os.environ["DYNALITE_URL"] = dynamodb
    _check_container(dynamodb)
    app = create_app()
    with app.app.app_context():
        g.hub_table = app.app.hub_table
        yield app
