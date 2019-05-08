#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sh
import pwd
import sys
import tempfile
import contextlib
from subhub.cfg import CFG, git, NotGitRepoError

NON_GIT_REPO_PATH = tempfile.mkdtemp()


@contextlib.contextmanager
def cd(path):
    old_path = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_path)


def test_NotGitRepoError():
    """
    NotGitRepoError
    """
    with cd(NON_GIT_REPO_PATH):
        try:
            git("rev-parse", "HEAD")
            result = False
        except NotGitRepoError:
            result = True
    assert result


def test_APP_UID():
    """
    uid
    """
    assert CFG.APP_UID == os.getuid()


def test_APP_GID():
    """
    gid
    """
    assert CFG.APP_GID == pwd.getpwuid(os.getuid()).pw_gid


def test_APP_USER():
    """
    user
    """
    assert CFG.APP_USER == pwd.getpwuid(os.getuid()).pw_name


def test_APP_PORT():
    """
    port
    """
    assert CFG.APP_PORT == 5000


def test_APP_JOBS():
    """
    jobs
    """
    try:
        expected = sh.nproc()
    except:
        expected = 1
    assert CFG.APP_JOBS == int(expected)


def test_APP_TIMEOUT():
    """
    timeout
    """
    assert CFG.APP_TIMEOUT == 120


def test_APP_WORKERS():
    """
    workers
    """
    assert CFG.APP_WORKERS == 2


def test_APP_MODULE():
    """
    module
    """
    assert CFG.APP_MODULE == "main:app"


def test_APP_REPOROOT():
    """
    reporoot
    """
    assert CFG.APP_REPOROOT == git("rev-parse", "--show-toplevel")


def test_APP_VERSION():
    """
    version
    """
    assert CFG.APP_VERSION == git("describe", "--abbrev=7", "--always")
    with cd(NON_GIT_REPO_PATH):
        os.environ["APP_VERSION"] = "APP_VERSION"
        assert CFG.APP_VERSION == "APP_VERSION"


def test_APP_BRANCH():
    """
    branch
    """
    assert CFG.APP_BRANCH == git("rev-parse", "--abbrev-ref", "HEAD")
    with cd(NON_GIT_REPO_PATH):
        os.environ["APP_BRANCH"] = "APP_BRANCH"
        assert CFG.APP_BRANCH == "APP_BRANCH"


def test_DEPENV():
    """
    deployment environment
    """
    with cd(NON_GIT_REPO_PATH):
        os.environ["APP_BRANCH"] = "master"
        assert CFG.APP_DEPENV == "prod"
        os.environ["APP_BRANCH"] = "stage/example"
        assert CFG.APP_DEPENV == "stage"
        os.environ["APP_BRANCH"] = "qa/example"
        assert CFG.APP_DEPENV == "qa"
        os.environ["APP_BRANCH"] = "example"
        assert CFG.APP_DEPENV == "dev"


def test_APP_REVISION():
    """
    version
    """
    assert CFG.APP_REVISION == git("rev-parse", "HEAD")
    with cd(NON_GIT_REPO_PATH):
        os.environ["APP_REVISION"] = "APP_REVISION"
        assert CFG.APP_REVISION == "APP_REVISION"


def test_APP_REMOTE_ORIGIN_URL():
    """
    remote origin url
    """
    assert CFG.APP_REMOTE_ORIGIN_URL == git("config", "--get", "remote.origin.url")
    with cd(NON_GIT_REPO_PATH):
        os.environ["APP_REMOTE_ORIGIN_URL"] = "APP_REMOTE_ORIGIN_URL"
        assert CFG.APP_REMOTE_ORIGIN_URL == "APP_REMOTE_ORIGIN_URL"


def test_APP_REPONAME():
    """
    reponame
    """
    pattern = (
        r"((ssh|https)://)?(git@)?github.com[:/](?P<reponame>[A-Za-z0-9\/\-_]+)(.git)?"
    )
    match = re.search(pattern, CFG.APP_REMOTE_ORIGIN_URL)
    reponame = match.group("reponame")
    assert CFG.APP_REPONAME == reponame


def test_APP_PROJNAME():
    """
    projname
    """
    assert CFG.APP_PROJNAME == os.path.basename(CFG.APP_REPONAME)


def test_APP_PROJPATH():
    """
    projpath
    """
    assert CFG.APP_PROJPATH == os.path.join(CFG.APP_REPOROOT, CFG.APP_PROJNAME)


def test_APP_LS_REMOTE():
    """
    ls-remote
    """
    result = git("ls-remote", f"https://github.com/{CFG.APP_REPONAME}")
    assert CFG.APP_LS_REMOTE == {
        refname: revision
        for revision, refname in [line.split() for line in result.split("\n")]
    }
    with cd(NON_GIT_REPO_PATH):
        try:
            os.environ["APP_REPONAME"] = "mozilla/subhub"
            CFG.APP_LS_REMOTE
            assert False
        except Exception as ex:
            assert isinstance(ex, NotGitRepoError)


def test_APP_GSM_STATUS():
    """
    gsm status
    """
    assert CFG.APP_GSM_STATUS != None
    with cd(NON_GIT_REPO_PATH):
        try:
            CFG.APP_GSM_STATUS
            assert False
        except Exception as ex:
            assert isinstance(ex, NotGitRepoError)


def test_default():
    """
    default
    """
    assert CFG("foo", "bar") == "bar"


def test_keep_pydoits_hands_off():
    """
    keep pydoit's hands off
    """
    func = CFG.create_doit_tasks
    assert callable(func)
    assert func() == None


def test_negative_git():
    """
    test negative git command
    """
    try:
        git("blah")
    except Exception as ex:
        assert not isinstance(ex, NotGitRepoError)
