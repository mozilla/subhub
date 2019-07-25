#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import re
import pwd
import sys
import tempfile
import contextlib
from subhub.cfg import CFG, call, git, NotGitRepoError, GitCommandNotFoundError

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


def test_GitCommandNotFoundError():
    """
    GitCommandNotFoundError
    """
    error = GitCommandNotFoundError()
    assert error


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


def test_DEPLOYED_ENV():
    """
    deployment environment
    """
    with cd(NON_GIT_REPO_PATH):
        os.environ["BRANCH"] = "master"
        assert CFG.DEPLOYED_ENV == "prod"
        os.environ["BRANCH"] = "stage/example"
        assert CFG.DEPLOYED_ENV == "stage"
        os.environ["BRANCH"] = "qa/example"
        assert CFG.DEPLOYED_ENV == "qa"
        os.environ["BRANCH"] = "example"
        assert CFG.DEPLOYED_ENV == "dev"


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


def test_SALESFORCE_BASKET_URI():
    """
    salesforce basket uri
    """
    try:
        CFG.SALESFORCE_BASKET_URI
        assert True
    except:
        assert False


def test_BASKET_API_KEY():
    """
    basket api key
    """
    try:
        CFG.BASKET_API_KEY
        assert True
    except:
        assert False


def test_FXA_SQS_URI():
    """
    fxa sqs uri
    """
    try:
        CFG.FXA_SQS_URI
        assert True
    except:
        assert False


def test_AWS_REGION():
    """
    aws region
    """
    try:
        CFG.AWS_REGION
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


def test_SWAGGER_UI():
    """
    swagger ui
    """
    try:
        CFG.SWAGGER_UI
        assert True
    except:
        assert False


def test_NEW_RELIC_ACCOUNT_ID():
    """
    new relic account id
    """
    try:
        CFG.NEW_RELIC_ACCOUNT_ID
        assert True
    except:
        assert False


def test_NEW_RELIC_TRUSTED_ACCOUNT_ID():
    """
    new relic trusted account id
    """
    try:
        CFG.NEW_RELIC_TRUSTED_ACCOUNT_ID
        assert True
    except:
        assert False


def test_NEW_RELIC_SERVERLESS_MODE_ENABLED():
    """
    new relic serverless mode enabled
    """
    try:
        CFG.NEW_RELIC_SERVERLESS_MODE_ENABLED
        assert True
    except:
        assert False


def test_NEW_RELIC_DISTRIBUTED_TRACING_ENABLED():
    """
    new relic distributed tracing enabled
    """
    try:
        CFG.NEW_RELIC_DISTRIBUTED_TRACING_ENABLED
        assert True
    except:
        assert False


def test_ALLOWED_ORIGIN_SYSTEMS():
    """
    allowed origin systems
    """
    assert isinstance(CFG.ALLOWED_ORIGIN_SYSTEMS, list)


def test_PAYMENT_EVENT_LIST():
    """
    payment event list
    :return:
    """
    assert isinstance(CFG.PAYMENT_EVENT_LIST, list)


def test_PROFILING_ENABLED():
    """
    profiling enabled
    """
    try:
        CFG.PROFILING_ENABLED
        assert True
    except:
        assert False


def test_DEPLOY_DOMAIN():
    """
    deploy domain
    """
    try:
        CFG.DEPLOY_DOMAIN
        assert True
    except:
        assert False


def test_USER():
    """
    user
    """
    try:
        CFG.USER
        assert True
    except:
        assert False


def test_HOSTNAME():
    """
    hostname
    """
    try:
        CFG.HOSTNAME
        assert True
    except:
        assert False


def test_DEPLOYED_BY():
    """
    deployed by
    """
    try:
        CFG.DEPLOYED_BY
        assert True
    except:
        assert False


def test_DEPLOYED_WHEN():
    """
    deployed when
    """
    try:
        CFG.DEPLOYED_WHEN
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
