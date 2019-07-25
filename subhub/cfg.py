#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# -*- coding: utf-8 -*-
"""
config
"""
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
from subprocess import Popen, CalledProcessError, PIPE

from logging import getLogger

logger = getLogger()  # to avoid installing structlog for doit automation


class NotGitRepoError(Exception):
    """
    NotGitRepoError
    """

    def __init__(self, cwd=os.getcwd()):
        """
        init
        """
        msg = f"not a git repository error cwd={cwd}"
        super().__init__(msg)


class GitCommandNotFoundError(Exception):
    """
    GitCommandNotFoundError
    """

    def __init__(self):
        """
        init
        """
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
    process = Popen(cmd, stdout=stdout, stderr=stderr, shell=shell)
    _stdout, _stderr = [stream.decode("utf-8") for stream in process.communicate()]
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
    """
    git
    """
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
    """
    thin wrapper around AutoConfig adding some extra features
    """

    @property
    def REPO_ROOT(self):
        """
        repo_root
        """
        return git("rev-parse --show-toplevel")

    @property
    def LOG_LEVEL(self):
        """
        log level
        """
        default_level = {
            "prod": "WARNING",
            "stage": "INFO",
            "qa": "INFO",
            "dev": "DEBUG",
        }.get(self.DEPLOYED_ENV, "NOTSET")
        return self("LOG_LEVEL", default_level)

    @property
    def VERSION(self):
        """
        version
        """
        try:
            return git("describe --abbrev=7 --always")
        except (NotGitRepoError, GitCommandNotFoundError):
            return self("VERSION")

    @property
    def BRANCH(self):
        """
        branch
        """
        try:
            return git("rev-parse --abbrev-ref HEAD")
        except (NotGitRepoError, GitCommandNotFoundError):
            return self("BRANCH")

    @property
    def DEPLOYED_ENV(self):
        """
        deployment environment
        """
        branch = self.BRANCH
        if branch == "master":
            return "prod"
        elif branch.startswith("stage/"):
            return "stage"
        elif branch.startswith("qa/"):
            return "qa"
        return "dev"

    @property
    def REVISION(self):
        """
        revision
        """
        try:
            return git("rev-parse HEAD")
        except (NotGitRepoError, GitCommandNotFoundError):
            return self("REVISION")

    @property
    def REMOTE_ORIGIN_URL(self):
        """
        remote origin url
        """
        try:
            return git("config --get remote.origin.url")
        except (NotGitRepoError, GitCommandNotFoundError):
            return self("REMOTE_ORIGIN_URL")

    @property
    def REPO_NAME(self):
        """
        repo_name
        """
        pattern = r"((ssh|https)://)?(git@)?github.com[:/](?P<repo_name>[A-Za-z0-9\/\-_]+)(.git)?"
        match = re.search(pattern, self.REMOTE_ORIGIN_URL)
        return match.group("repo_name")

    @property
    def PROJECT_NAME(self):
        """
        project_name
        """
        return os.path.basename(self.REPO_NAME)

    @property
    def PROJECT_PATH(self):
        """
        project_path
        """
        return os.path.join(self.REPO_ROOT, self.PROJECT_NAME)

    @property
    def LS_REMOTE(self):
        """
        ls-remote
        """
        repo_name = self.REPO_NAME
        logger.info(f"repo_name={repo_name}")
        result = git(f"ls-remote https://github.com/{repo_name}")
        return {
            refname: revision
            for revision, refname in [line.split() for line in result.split("\n")]
        }

    @property
    def GSM_STATUS(self):
        """
        gsm status
        """
        result = git("submodule status", strip=False)
        pattern = r"([ +-])([a-f0-9]{40}) ([A-Za-z0-9\/\-_.]+)( .*)?"
        matches = re.findall(pattern, result)
        states = {
            " ": True,  # submodule is checked out the correct revision
            "+": False,  # submodule is checked out to a different revision
            "-": None,  # submodule is not checked out
        }
        return {
            repopath: [revision, states[state]]
            for state, revision, repopath, _ in matches
        }

    @property
    def USER_TABLE(self):
        """
        default value for USER_TABLE
        """
        return self("USER_TABLE", "users-testing")

    @property
    def EVENT_TABLE(self):
        """
        default value for EVENT_TABLE
        """
        return self("EVENT_TABLE", "events-testing")

    @property
    def LOCAL_FLASK_PORT(self):
        """
        local flask port
        """
        return self("LOCAL_FLASK_PORT", 5000, cast=int)

    @property
    def DYNALITE_PORT(self):
        """
        dynalite port
        """
        return self("DYNALITE_PORT", 8000, cast=int)

    @property
    def DYNALITE_FILE(self):
        """
        dynalite output file
        """
        return self("DYNALITE_FILE", "dynalite.out")

    @property
    def SALESFORCE_BASKET_URI(self):
        """
        basket uri
        """
        return self("SALESFORCE_BASKET_URI", "https://google.com?api-key=")

    @property
    def BASKET_API_KEY(self):
        """
        basket api key
        :return:
        """
        return self("BASKET_API_KEY", "fake_basket_api_key")

    @property
    def FXA_SQS_URI(self):
        """
        fxa sqs uri
        """
        return self("FXA_SQS_URI", "https://google.com")

    @property
    def AWS_REGION(self):
        """
        aws region
        """
        return self("AWS_REGION", "us-west-2")

    @property
    def PAYMENT_API_KEY(self):
        """
        payment api key
        """
        return self("PAYMENT_API_KEY", "fake_payment_api_key")

    @property
    def TOPIC_ARN_KEY(self):
        """
        topic arn for sns
        :return:
        """
        return self("TOPIC_ARN_KEY", "fake_topic_arn_key")

    @property
    def SUPPORT_API_KEY(self):
        """
        support api key
        """
        return self("SUPPORT_API_KEY", "fake_support_api_key")

    @property
    def AWS_ACCESS_KEY_ID(self):
        """
        aws access key id
        :return:
        """
        return self("AWS_ACCESS_KEY_ID", "fake_aws_access_key_id")

    @property
    def AWS_SECRET_ACCESS_KEY(self):
        """
        aws secret access key
        :return:
        """
        return self("AWS_SECRET_ACCESS_KEY", "fake_aws_secret_access_key")

    @property
    def HUB_API_KEY(self):
        """
        hub api key
        """
        return self("HUB_API_KEY", "fake_hub_api_key")

    @property
    def AWS_EXECUTION_ENV(self):
        """
        default value for aws execution env
        """
        return self("AWS_EXECUTION_ENV", None)

    @property
    def SWAGGER_UI(self):
        """
        boolean property to determine if we should swagger or not
        """
        return self.DEPLOYED_ENV in ("stage", "qa", "dev")

    @property
    def NEW_RELIC_ACCOUNT_ID(self):
        """
        NEW_RELIC_ACCOUNT_ID
        """
        return self("NEW_RELIC_ACCOUNT_ID", 2_423_519)

    @property
    def NEW_RELIC_TRUSTED_ACCOUNT_ID(self):
        """
        NEW_RELIC_TRUSTED_ACCOUNT_ID
        """
        return self("NEW_RELIC_TRUSTED_ACCOUNT_ID", 2_423_519)

    @property
    def NEW_RELIC_SERVERLESS_MODE_ENABLED(self):
        """
        NEW_RELIC_SERVERLESS_MODE_ENABLED
        """
        return self("NEW_RELIC_SERVERLESS_MODE_ENABLED", True)

    @property
    def NEW_RELIC_DISTRIBUTED_TRACING_ENABLED(self):
        """
        NEW_RELIC_DISTRIBUTED_TRACING_ENABLED
        """
        return self("NEW_RELIC_DISTRIBUTED_TRACING_ENABLED", True)

    @property
    def ALLOWED_ORIGIN_SYSTEMS(self):
        """
        ALLOWED_ORIGIN_SYSTEMS
        """
        return self("ALLOWED_ORIGIN_SYSTEMS", "fake_origin1, fake_origin2").split(",")

    @property
    def PAYMENT_EVENT_LIST(self):
        """"
        PAYMENT_EVENT_LIST
        """
        return self("PAYMENT_EVENT_LIST", "test.system, test.event").split(",")

    @property
    def PROFILING_ENABLED(self):
        """
        PROFILING_ENABLED
        """
        return ast.literal_eval(self("PROFILING_ENABLED", "False"))

    @property
    def DEPLOY_DOMAIN(self):
        """
        DEPLOY_DOMAIN
        """
        return self("DEPLOY_DOMAIN", "localhost")

    @property
    def USER(self):
        """
        user
        """
        try:
            return pwd.getpwuid(os.getuid()).pw_name
        except:
            return "unknown"

    @property
    def HOSTNAME(self):
        """
        hostname
        """
        try:
            return platform.node()
        except:
            return "unknown"

    @property
    def DEPLOYED_BY(self):
        """
        DEPLOYED_BY
        """
        return self("DEPLOYED_BY", f"{self.USER}@{self.HOSTNAME}")

    @property
    @lru_cache()
    def DEPLOYED_WHEN(self):
        """
        DEPLOYED_WHEN
        """
        return self("DEPLOYED_WHEN", datetime.utcnow().isoformat())

    def __getattr__(self, attr):
        """
        getattr
        """
        if attr == "create_doit_tasks":  # note: to keep pydoit's hands off
            return lambda: None
        result = self(attr)
        try:
            return int(result)
        except ValueError:
            return result


CFG = AutoConfigPlus()
