# -*- coding: utf-8 -*-
"""
config
"""

import os
import re
import pwd
import sys
import time
import logging
import sh

from decouple import UndefinedValueError, AutoConfig, config

LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

LOG_LEVEL = config("LOG_LEVEL", logging.WARNING, cast=int)

log = logging.getLogger(__name__)


class NotGitRepoError(Exception):
    """
    NotGitRepoError
    """

    def __init__(self, cwd=os.getcwd()):
        """
        init
        """
        msg = f"not a git repository error cwd={cwd}"
        super(NotGitRepoError, self).__init__(msg)


def git(*args, strip=True, **kwargs):
    """
    git
    """
    try:
        sh.contrib.git("rev-parse", "--is-inside-work-tree")
    except sh.ErrorReturnCode as e:
        stderr = e.stderr.decode("utf-8")
        if "not a git repository" in stderr.lower():
            raise NotGitRepoError
    try:
        result = str(sh.contrib.git(*args, **kwargs))  # pylint: disable=no-member
        if result:
            result = result.strip()
        return result
    except sh.ErrorReturnCode as e:
        log.error(e)
        raise e


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
            result = sh.nproc()
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
        return git("rev-parse", "--show-toplevel")

    @property
    def APP_VERSION(self):
        """
        version
        """
        try:
            return git("describe", "--abbrev=7", "--always")
        except NotGitRepoError:
            return self("APP_VERSION")

    @property
    def APP_BRANCH(self):
        """
        branch
        """
        try:
            return git("rev-parse", "--abbrev-ref", "HEAD")
        except NotGitRepoError:
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
            return git("rev-parse", "HEAD")
        except NotGitRepoError:
            return self("APP_REVISION")

    @property
    def APP_REMOTE_ORIGIN_URL(self):
        """
        remote origin url
        """
        try:
            return git("config", "--get", "remote.origin.url")
        except NotGitRepoError:
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
        log.info(f"reponame={reponame}")
        result = git("ls-remote", f"https://github.com/{reponame}")
        return {
            refname: revision
            for revision, refname in [line.split() for line in result.split("\n")]
        }

    @property
    def APP_GSM_STATUS(self):
        """
        gsm status
        """
        result = git("submodule", "status", strip=False)
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

    def __getattr__(self, attr):
        """
        getattr
        """
        log.info(f"attr = {attr}")
        if attr == "create_doit_tasks":  # note: to keep pydoit's hands off
            return lambda: None
        result = self(attr)
        try:
            return int(result)
        except ValueError:
            return result


CFG = AutoConfigPlus()
