#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import pwd
import sys
import tempfile
import contextlib
from subhub.cfg import CFG, call, git, NotGitRepoError

from subhub.log import get_logger

logger = get_logger

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
            git("rev-parse HEAD")
            result = False
        except NotGitRepoError:
            result = True
    assert result


def test_UID():
    """
    uid
    """
    assert CFG.UID == os.getuid()


def test_GID():
    """
    gid
    """
    assert CFG.GID == pwd.getpwuid(os.getuid()).pw_gid


def test_USER():
    """
    user
    """
    assert CFG.USER == pwd.getpwuid(os.getuid()).pw_name


def test_PORT():
    """
    port
    """
    assert CFG.PORT == 5000


def test_JOBS():
    """
    jobs
    """
    assert CFG.JOBS != 0


def test_TIMEOUT():
    """
    timeout
    """
    assert CFG.TIMEOUT == 120


def test_WORKERS():
    """
    workers
    """
    assert CFG.WORKERS == 2


def test_MODULE():
    """
    module
    """
    assert CFG.MODULE == "main:app"


def test_REPO_ROOT():
    """
    repo_root
    """
    assert CFG.REPO_ROOT == git("rev-parse --show-toplevel")


def test_VERSION():
    """
    version
    """
    assert CFG.VERSION == git("describe --abbrev=7 --always")
    with cd(NON_GIT_REPO_PATH):
        os.environ["VERSION"] = "VERSION"
        assert CFG.VERSION == "VERSION"


def test_BRANCH():
    """
    branch
    """
    assert CFG.BRANCH == git("rev-parse --abbrev-ref HEAD")
    with cd(NON_GIT_REPO_PATH):
        os.environ["BRANCH"] = "BRANCH"
        assert CFG.BRANCH == "BRANCH"


def test_DEPLOY_ENV():
    """
    deployment environment
    """
    with cd(NON_GIT_REPO_PATH):
        os.environ["BRANCH"] = "master"
        assert CFG.DEPLOY_ENV == "prod"
        os.environ["BRANCH"] = "stage/example"
        assert CFG.DEPLOY_ENV == "stage"
        os.environ["BRANCH"] = "qa/example"
        assert CFG.DEPLOY_ENV == "qa"
        os.environ["BRANCH"] = "example"
        assert CFG.DEPLOY_ENV == "dev"


def test_REVISION():
    """
    version
    """
    assert CFG.REVISION == git("rev-parse HEAD")
    with cd(NON_GIT_REPO_PATH):
        os.environ["REVISION"] = "REVISION"
        assert CFG.REVISION == "REVISION"


def test_REMOTE_ORIGIN_URL():
    """
    remote origin url
    """
    assert CFG.REMOTE_ORIGIN_URL == git("config --get remote.origin.url")
    with cd(NON_GIT_REPO_PATH):
        os.environ["REMOTE_ORIGIN_URL"] = "REMOTE_ORIGIN_URL"
        assert CFG.REMOTE_ORIGIN_URL == "REMOTE_ORIGIN_URL"


def test_REPO_NAME():
    """
    repo_name
    """
    pattern = (
        r"((ssh|https)://)?(git@)?github.com[:/](?P<repo_name>[A-Za-z0-9\/\-_]+)(.git)?"
    )
    match = re.search(pattern, CFG.REMOTE_ORIGIN_URL)
    repo_name = match.group("repo_name")
    assert CFG.REPO_NAME == repo_name


def test_PROJECT_NAME():
    """
    project_name
    """
    assert CFG.PROJECT_NAME == os.path.basename(CFG.REPO_NAME)


def test_PROJECT_PATH():
    """
    project_path
    """
    assert CFG.PROJECT_PATH == os.path.join(CFG.REPO_ROOT, CFG.PROJECT_NAME)


def test_LS_REMOTE():
    """
    ls-remote
    """
    result = git(f"ls-remote https://github.com/{CFG.REPO_NAME}")
    assert CFG.LS_REMOTE == {
        refname: revision
        for revision, refname in [line.split() for line in result.split("\n")]
    }
    with cd(NON_GIT_REPO_PATH):
        try:
            os.environ["REPO_NAME"] = "mozilla/subhub"
            CFG.LS_REMOTE
            assert False
        except Exception as ex:
            assert isinstance(ex, NotGitRepoError)


def test_GSM_STATUS():
    """
    gsm status
    """
    assert CFG.GSM_STATUS != None
    with cd(NON_GIT_REPO_PATH):
        try:
            CFG.GSM_STATUS
            assert False
        except Exception as ex:
            assert isinstance(ex, NotGitRepoError)


def test_USER_TABLE():
    """
    user table
    """
    try:
        CFG.USER_TABLE
        assert True
    except:
        assert False


def test_LOCAL_FLASK_PORT():
    """
    local flask port
    """
    try:
        CFG.LOCAL_FLASK_PORT
        assert True
    except:
        assert False


def test_DYNALITE_PORT():
    """
    dynalite port
    """
    try:
        CFG.DYNALITE_PORT
        assert True
    except:
        assert False


def test_DYNALITE_FILE():
    """
    dynalite file
    """
    try:
        CFG.DYNALITE_FILE
        assert True
    except:
        assert False


def test_PAYMENT_API_KEY():
    """
    payment api key
    """
    try:
        CFG.PAYMENT_API_KEY
        assert True
    except:
        assert False


def test_SUPPORT_API_KEY():
    """
    support api key
    """
    try:
        CFG.SUPPORT_API_KEY
        assert True
    except:
        assert False


def test_AWS_EXECUTION_ENV():
    """
    aws execution env
    """
    try:
        CFG.AWS_EXECUTION_ENV
        assert True
    except:
        assert False


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


def test_call():
    """
    test the call function
    """
    assert call("echo test", nerf=True) == (None, "nerfed", "nerfed")
    assert call("echo test", verbose=True)[0] == 0
    assert call("echo test 1>&2", verbose=True)[0] == 0


def test_negative_git():
    """
    test negative git command
    """
    try:
        git("blah")
    except Exception as ex:
        assert not isinstance(ex, NotGitRepoError)
