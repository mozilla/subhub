# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# -*- coding: utf-8 -*-

import os
import re
import ast
import pwd
import sys
import time
import platform

from datetime import datetime
from decouple import UndefinedValueError, AutoConfig, config
from functools import lru_cache
from subprocess import Popen, CalledProcessError, PIPE  # nosec
from structlog import get_logger  # because circular dep otherwise

logger = get_logger()


class NotGitRepoError(Exception):
    def __init__(self, cwd=os.getcwd()):
        msg = f"not a git repository error cwd={cwd}"
        super().__init__(msg)


class GitCommandNotFoundError(Exception):
    def __init__(self):
        msg = "git: command not found"
        super().__init__(msg)


def call(
    cmd, stdout=PIPE, stderr=PIPE, shell=True, nerf=False, throw=True, verbose=False
):
    if verbose or nerf:
        logger.info(f"verbose cmd={cmd}")
        pass
    if nerf:
        return (None, "nerfed", "nerfed")
    process = Popen(cmd, stdout=stdout, stderr=stderr, shell=shell)  # nosec
    _stdout, _stderr = [
        stream.decode("utf-8") if stream != None else None
        for stream in process.communicate()
    ]
    exitcode = process.poll()
    if verbose:
        if _stdout:
            logger.info(f"verbose stdout={_stdout}")
        if _stderr:
            logger.info(f"verbose stderr={_stderr}")
            pass
    if throw and exitcode:
        raise CalledProcessError(
            exitcode, f"cmd={cmd}; stdout={_stdout}; stderr={_stderr}"
        )
    return exitcode, _stdout, _stderr


def git(args, strip=True, **kwargs):
    try:
        _, stdout, stderr = call("git rev-parse --is-inside-work-tree")
    except CalledProcessError as ex:
        if "not a git repository" in str(ex):
            raise NotGitRepoError
        elif "git: command not found" in str(ex):
            raise GitCommandNotFoundError
        else:
            logger.error("failed repo check but NOT a NotGitRepoError???", ex=ex)
    try:
        _, result, _ = call(f"git {args}", **kwargs)
        if result:
            result = result.strip()
        return result
    except CalledProcessError as ex:
        logger.error(ex)
        raise ex


class AutoConfigPlus(AutoConfig):  # pylint: disable=too-many-public-methods
    @property
    def REPO_ROOT(self):
        return git("rev-parse --show-toplevel")

    @property
    def LOG_LEVEL(self):
        default_level = {
            "prod": "WARNING",
            "stage": "INFO",
            "qa": "INFO",
            "dev": "DEBUG",
            "fab": "DEBUG",
        }.get(self.DEPLOYED_ENV, "NOTSET")
        return self("LOG_LEVEL", default_level)

    @property
    def VERSION(self):
        try:
            return git("describe --abbrev=7 --always")
        except (NotGitRepoError, GitCommandNotFoundError):
            return self("VERSION")

    @property
    def BRANCH(self):
        try:
            return git("rev-parse --abbrev-ref HEAD")
        except (NotGitRepoError, GitCommandNotFoundError):
            return self("BRANCH")

    @property
    def DEPLOYED_ENV(self):
        deployed_env = self("DEPLOYED_ENV", None)
        if deployed_env:
            return deployed_env
        branch = self.BRANCH
        if branch == "master":
            return "prod"
        elif branch.startswith("stage/"):
            return "stage"
        elif branch.startswith("qa/"):
            return "qa"
        return "dev"

    @property
    def DEPLOYED_BY(self):
        return self("DEPLOYED_BY", f"{self.USER}@{self.HOSTNAME}")

    @property  # type: ignore
    @lru_cache()
    def DEPLOYED_WHEN(self):
        return self("DEPLOYED_WHEN", datetime.utcnow().isoformat())

    @property
    def REVISION(self):
        try:
            return git("rev-parse HEAD")
        except (NotGitRepoError, GitCommandNotFoundError):
            return self("REVISION")

    @property
    def REMOTE_ORIGIN_URL(self):
        try:
            return git("config --get remote.origin.url")
        except (NotGitRepoError, GitCommandNotFoundError):
            return self("REMOTE_ORIGIN_URL")

    @property
    def REPO_NAME(self):
        pattern = r"^((https|ssh)://)?(git@)?github.com[:/](?P<repo_name>[A-Za-z0-9\/\-_]+)(.git)?$"
        match = re.search(pattern, self.REMOTE_ORIGIN_URL)
        return match.group("repo_name")

    @property
    def PROJECT_NAME(self):
        return os.path.basename(self.REPO_NAME)

    @property
    def PROJECT_PATH(self):
        return os.path.join(self.REPO_ROOT, self.PROJECT_NAME)

    @property
    def LS_REMOTE(self):
        repo_name = self.REPO_NAME
        logger.info(f"repo_name={repo_name}")
        result = git(f"ls-remote https://github.com/{repo_name}")
        return {
            refname: revision
            for revision, refname in [line.split() for line in result.split("\n")]
        }

    @property
    def USER_TABLE(self):
        return self("USER_TABLE", f"users-{CFG.DEPLOYED_ENV}")

    @property
    def DELETED_USER_TABLE(self):
        return self("DELETED_USER_TABLE", f"deleted-users-{CFG.DEPLOYED_ENV}")

    @property
    def EVENT_TABLE(self):
        return self("EVENT_TABLE", f"events-{CFG.DEPLOYED_ENV}")

    @property
    def STRIPE_REQUEST_TIMEOUT(self):
        return self("STRIPE_REQUEST_TIMEOUT", 9, cast=int)

    @property
    def STRIPE_MOCK_HOST(self):
        return self("STRIPE_MOCK_HOST", "stripe")

    @property
    def STRIPE_MOCK_PORT(self):
        return self("STRIPE_MOCK_PORT", 12112, cast=int)

    @property
    def STRIPE_LOCAL(self):
        return self("STRIPE_LOCAL", False, cast=bool)

    @property
    def STRIPE_API_KEY(self):
        return self("STRIPE_API_KEY", "sk_test_123")

    @property
    def LOCAL_FLASK_PORT(self):
        return self("LOCAL_FLASK_PORT", 5000, cast=int)

    @property
    def LOCAL_HUB_FLASK_PORT(self):
        return self("LOCAL_HUB_FLASK_PORT", 5001, cast=int)

    @property
    def DYNALITE_URL(self):
        """
        dynalite url
        """
        return self("DYNALITE_URL", "http://127.0.0.1:8000")

    @property
    def DYNALITE_PORT(self):
        return self("DYNALITE_PORT", 8000, cast=int)

    @property
    def SALESFORCE_BASKET_URI(self):
        return self("SALESFORCE_BASKET_URI", "https://google.com?api-key=")

    @property
    def BASKET_API_KEY(self):
        return self("BASKET_API_KEY", "fake_basket_api_key")

    @property
    def FXA_SQS_URI(self):
        return self("FXA_SQS_URI", "https://google.com")

    @property
    def AWS_REGION(self):
        return self("AWS_REGION", "us-west-2")

    @property
    def SUPPORTED_COUNTRIES(self):
        return self("SUPPORTED_COUNTRIES", "US, CA").split(",")

    @property
    def PAYMENT_API_KEY(self):
        return self("PAYMENT_API_KEY", "fake_payment_api_key")

    @property
    def TOPIC_ARN_KEY(self):
        return self("TOPIC_ARN_KEY", "fake_topic_arn_key")

    @property
    def SUPPORT_API_KEY(self):
        return self("SUPPORT_API_KEY", "fake_support_api_key")

    @property
    def AWS_ACCESS_KEY_ID(self):
        return self("AWS_ACCESS_KEY_ID", "fake_aws_access_key_id")

    @property
    def AWS_SECRET_ACCESS_KEY(self):
        return self("AWS_SECRET_ACCESS_KEY", "fake_aws_secret_access_key")

    @property
    def HUB_API_KEY(self):
        return self("HUB_API_KEY", "fake_hub_api_key")

    @property
    def AWS_EXECUTION_ENV(self):
        return self("AWS_EXECUTION_ENV", None)

    @property
    def SWAGGER_UI(self):
        return self.DEPLOYED_ENV in ("stage", "qa", "dev", "fab")

    @property
    def NEW_RELIC_ACCOUNT_ID(self):
        return self("NEW_RELIC_ACCOUNT_ID", 2_423_519)

    @property
    def NEW_RELIC_TRUSTED_ACCOUNT_ID(self):
        return self("NEW_RELIC_TRUSTED_ACCOUNT_ID", 2_423_519)

    @property
    def NEW_RELIC_SERVERLESS_MODE_ENABLED(self):
        return self("NEW_RELIC_SERVERLESS_MODE_ENABLED", True)

    @property
    def NEW_RELIC_DISTRIBUTED_TRACING_ENABLED(self):
        return self("NEW_RELIC_DISTRIBUTED_TRACING_ENABLED", True)

    @property
    def ALLOWED_ORIGIN_SYSTEMS(self):
        return self("ALLOWED_ORIGIN_SYSTEMS", "fake_origin1, fake_origin2").split(",")

    @property
    def PAYMENT_EVENT_LIST(self):
        return self("PAYMENT_EVENT_LIST", "test.system, test.event").split(",")

    @property
    def PROFILING_ENABLED(self):
        return ast.literal_eval(self("PROFILING_ENABLED", "False"))

    @property
    def DEPLOY_DOMAIN(self):
        return self("DEPLOY_DOMAIN", "localhost")

    @property
    def SRCTAR(self):
        return self("SRCTAR", ".src.tar.gz")

    @property
    def USER(self):
        try:
            return pwd.getpwuid(os.getuid()).pw_name
        except:
            return "unknown"

    @property
    def HOSTNAME(self):
        try:
            return platform.node()
        except:
            return "unknown"

    def __getattr__(self, attr):
        if attr == "create_doit_tasks":  # note: to keep pydoit's hands off
            return lambda: None
        result = self(attr)
        try:
            return int(result)
        except ValueError:
            return result


CFG = AutoConfigPlus()
