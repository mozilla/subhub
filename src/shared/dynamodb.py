# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import backoff
import docker
import psutil
import pytest
import socket
import requests
import string
import random
import json

from deprecated import deprecated
from shared.log import get_logger

logger = get_logger()

def random_label(length: int) -> str:
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(length))


# Amazon's DynamoDB Local
# https://hub.docker.com/r/amazon/dynamodb-local
IMAGE = "amazon/dynamodb-local:latest"
CONTAINER_FOR_TESTING_LABEL = random_label(128)


def get_free_tcp_port():
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.bind(("", 0))
    addr, port = tcp.getsockname()
    logger.debug("port", port=port)
    tcp.close()
    return port


def pull_image(image):
    docker_client = docker.from_env()
    response = docker_client.api.pull(image)
    lines = [line for line in response.splitlines() if line]
    pull_result = json.loads(lines[-1])
    if "error" in pull_result:
        raise Exception("Could not pull {}: {}".format(image, pull_result["error"]))


@deprecated(reason="Migrated to Google Cloud Spanner")
@pytest.yield_fixture(scope="module", autouse=True)
def dynamodb():
    pull_image(IMAGE)
    docker_client = docker.from_env()
    host_port = get_free_tcp_port()
    port_bindings = {8000: host_port}
    host_config = docker_client.api.create_host_config(port_bindings=port_bindings)
    container = docker_client.api.create_container(
        image=IMAGE,
        labels=[CONTAINER_FOR_TESTING_LABEL],
        host_config=host_config,
        ports=[4567],
    )
    docker_client.api.start(container=container["Id"])
    container_info = docker_client.api.inspect_container(container.get("Id"))
    host_ip = container_info["NetworkSettings"]["Ports"]["8000/tcp"][0]["HostIp"]
    host_port = container_info["NetworkSettings"]["Ports"]["8000/tcp"][0]["HostPort"]
    url = f"http://{host_ip}:{host_port}"
    _check_container(url)
    yield url
    docker_client.api.remove_container(container=container["Id"], force=True)


@backoff.on_exception(backoff.fibo, Exception, max_tries=8)
def _check_container(url):
    return requests.get(url)
