# -*- coding: utf-8 -*-
"""
config
"""

import os
import re
import pwd
import sys
import time
from decouple import UndefinedValueError, AutoConfig, config
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
        logger.info("verbose", cmd=cmd)
    if nerf:
        return (None, "nerfed", "nerfed")
    process = Popen(cmd, stdout=stdout, stderr=stderr, shell=shell)
    _stdout, _stderr = [stream.decode("utf-8") for stream in process.communicate()]
    exitcode = process.poll()
    if verbose:
        if _stdout:
            logger.info("verbose", stdout=_stdout)
        if _stderr:
            logger.info("verbose", stderr=_stderr)
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
    def APP_UID(self):
        """
        uid
        """
        return os.getuid()

    @property
    def APP_GID(self):
        """
        gid
        """
        return pwd.getpwuid(self.APP_UID).pw_gid

    @property
    def APP_USER(self):
        """
        user
        """
        return pwd.getpwuid(self.APP_UID).pw_name

    @property
    def APP_PORT(self):
        """
        port
        """
        return self("APP_PORT", 5000, cast=int)

    @property
    def APP_JOBS(self):
        """
        jobs
        """
        try:
            result = call("nproc")[1]
        except:
            result = 1
        return int(result)

    @property
    def APP_TIMEOUT(self):
        """
        timeout
        """
        return self("APP_TIMEOUT", 120, cast=int)

    @property
    def APP_WORKERS(self):
        """
        workers
        """
        return self("APP_WORKERS", 2, cast=int)

    @property
    def APP_MODULE(self):
        """
        module
        """
        return self("APP_MODULE", "main:app")

    @property
    def APP_REPOROOT(self):
        """
        reporoot
        """
        return git("rev-parse --show-toplevel")

    @property
    def APP_LOG_LEVEL(self):
        """
        log level
        """
        default_level = {
            "prod": "WARNING",
            "stage": "INFO",
            "qa": "INFO",
            "dev": "DEBUG",
        }.get(self.APP_DEPENV, "NOTSET")
        try:
            return self("APP_LOG_LEVEL", default_level)
        except:
            pass

    @property
    def APP_VERSION(self):
        """
        version
        """
        try:
            return git("describe --abbrev=7 --always")
        except (NotGitRepoError, GitCommandNotFoundError):
            return self("APP_VERSION")

    @property
    def APP_BRANCH(self):
        """
        branch
        """
        try:
            return git("rev-parse --abbrev-ref HEAD")
        except (NotGitRepoError, GitCommandNotFoundError):
            return self("APP_BRANCH")

    @property
    def APP_DEPENV(self):
        """
        deployment environment
        """
        branch = self.APP_BRANCH
        if branch == "master":
            return "prod"
        elif branch.startswith("stage/"):
            return "stage"
        elif branch.startswith("qa/"):
            return "qa"
        return "dev"

    @property
    def APP_REVISION(self):
        """
        revision
        """
        try:
            return git("rev-parse HEAD")
        except (NotGitRepoError, GitCommandNotFoundError):
            return self("APP_REVISION")

    @property
    def APP_REMOTE_ORIGIN_URL(self):
        """
        remote origin url
        """
        try:
            return git("config --get remote.origin.url")
        except (NotGitRepoError, GitCommandNotFoundError):
            return self("APP_REMOTE_ORIGIN_URL")

    @property
    def APP_REPONAME(self):
        """
        reponame
        """
        pattern = r"((ssh|https)://)?(git@)?github.com[:/](?P<reponame>[A-Za-z0-9\/\-_]+)(.git)?"
        match = re.search(pattern, self.APP_REMOTE_ORIGIN_URL)
        return match.group("reponame")

    @property
    def APP_PROJNAME(self):
        """
        projname
        """
        return os.path.basename(self.APP_REPONAME)

    @property
    def APP_PROJPATH(self):
        """
        projpath
        """
        return os.path.join(self.APP_REPOROOT, self.APP_PROJNAME)

    @property
    def APP_LS_REMOTE(self):
        """
        ls-remote
        """
        reponame = self.APP_REPONAME
        logger.info(f"reponame={reponame}")
        result = git(f"ls-remote https://github.com/{reponame}")
        return {
            refname: revision
            for revision, refname in [line.split() for line in result.split("\n")]
        }

    @property
    def APP_GSM_STATUS(self):
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
    def WEBHOOK_API_KEY(self):
        """
        webhook api key
        """
        return self("WEBHOOK_API_KEY", "fake_webhook_api_key")

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
        return self.APP_DEPENV in ("stage", "qa", "dev")

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
