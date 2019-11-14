import os
import re
import pwd
import sys
import glob
import json
import difflib
import itertools
import contextlib
import threading

from subprocess import PIPE, STDOUT
from ruamel import yaml
from functools import lru_cache
from doit.tools import LongRunning
from pathlib import Path
from pkg_resources import parse_version
from os.path import join, dirname, realpath

sys.path.insert(0, join(dirname(realpath(__file__)), "src"))

from shared.cfg import CFG, call, CalledProcessError

DOIT_CONFIG = {"default_tasks": ["pull", "deploy", "count"], "verbosity": 2}

HEADER = """
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""

SPACE = " "
NEWLINE = "\n"
VENV = f"{CFG.REPO_ROOT}/venv"
PYTHON3 = f"{VENV}/bin/python3.7"
PIP3 = f"{PYTHON3} -m pip"
NODE_MODULES = f"{CFG.REPO_ROOT}/node_modules"
SLS = f"{NODE_MODULES}/serverless/bin/serverless"
SVCS = [
    svc
    for svc in os.listdir("services")
    if os.path.isdir(f"services/{svc}")
    if os.path.isfile(f"services/{svc}/serverless.yml")
]
SRCS = [
    src for src in os.listdir("src/") if os.path.isdir(f"src/{src}") if src != "shared"
]

mutex = threading.Lock()


def envs(sep=" ", **kwargs):
    envs = dict(
        BRANCH=CFG.BRANCH,
        DEPLOY_DOMAIN=CFG.DEPLOY_DOMAIN,
        DEPLOYED_BY=CFG.DEPLOYED_BY,
        DEPLOYED_ENV=CFG.DEPLOYED_ENV,
        DEPLOYED_WHEN=CFG.DEPLOYED_WHEN,
        DELETED_USER_TABLE=CFG.DELETED_USER_TABLE,
        DYNALITE_PORT=CFG.DYNALITE_PORT,
        EVENT_TABLE=CFG.EVENT_TABLE,
        HUB_API_KEY=CFG.HUB_API_KEY,
        LOCAL_FLASK_PORT=CFG.LOCAL_FLASK_PORT,
        LOCAL_HUB_FLASK_PORT=CFG.LOCAL_HUB_FLASK_PORT,
        LOG_LEVEL=CFG.LOG_LEVEL,
        NEW_RELIC_ACCOUNT_ID=CFG.NEW_RELIC_ACCOUNT_ID,
        NEW_RELIC_TRUSTED_ACCOUNT_ID=CFG.NEW_RELIC_TRUSTED_ACCOUNT_ID,
        NEW_RELIC_SERVERLESS_MODE_ENABLED=CFG.NEW_RELIC_SERVERLESS_MODE_ENABLED,
        NEW_RELIC_DISTRIBUTED_TRACING_ENABLED=CFG.NEW_RELIC_DISTRIBUTED_TRACING_ENABLED,
        PAYMENT_API_KEY=CFG.PAYMENT_API_KEY,
        PROFILING_ENABLED=CFG.PROFILING_ENABLED,
        REMOTE_ORIGIN_URL=CFG.REMOTE_ORIGIN_URL,
        REVISION=CFG.REVISION,
        STRIPE_API_KEY=CFG.STRIPE_API_KEY,
        STRIPE_LOCAL=CFG.STRIPE_LOCAL,
        STRIPE_REQUEST_TIMEOUT=CFG.STRIPE_REQUEST_TIMEOUT,
        STRIPE_MOCK_HOST=CFG.STRIPE_MOCK_HOST,
        STRIPE_MOCK_PORT=CFG.STRIPE_MOCK_PORT,
        SUPPORT_API_KEY=CFG.SUPPORT_API_KEY,
        PROJECT_NAME=CFG.PROJECT_NAME,
        USER_TABLE=CFG.USER_TABLE,
        VERSION=CFG.VERSION,
    )
    return sep.join(
        [f"{key}={value}" for key, value in sorted(dict(envs, **kwargs).items())]
    )


def globs(*patterns, **kwargs):
    return itertools.chain.from_iterable(
        glob.iglob(pattern, **kwargs) for pattern in patterns
    )


def docstr_format(*args, **kwargs):
    def wrapper(func):
        func.__doc__ = func.__doc__.format(*args, **kwargs)
        return func

    return wrapper


class UnknownPkgmgrError(Exception):
    def __init__(self):
        super(UnknownPkgmgrError, self).__init__("unknown pkgmgr!")


def check_hash(program):
    try:
        call(f"hash {program}")
        return True
    except CalledProcessError:
        return False


def get_pkgmgr():
    if check_hash("dpkg"):
        return "deb"
    elif check_hash("rpm"):
        return "rpm"
    elif check_hash("brew"):
        return "brew"
    raise UnknownPkgmgrError


def has_header(content):
    return content.startswith(HEADER.lstrip())


def pyfiles(path, exclude=None):
    pyfiles = set(Path(path).rglob("*.py")) - set(
        Path(exclude).rglob("*.py") if exclude else []
    )
    return [pyfile.as_posix() for pyfile in pyfiles]


def load_serverless(svc):
    return yaml.safe_load(open(f"services/{svc}/serverless.yml"))


def get_svcs_to_funcs():
    return {svc: list(load_serverless(svc)["functions"].keys()) for svc in SVCS}


def defaults(*args, **kwargs):
    results = [None] * len(kwargs)
    len_args = len(args)
    len_kwargs = len(kwargs)
    for i, (k, v) in enumerate(kwargs.items()):
        index = i + (len_args - len_kwargs)
        if index >= 0:
            results[i] = args[index]
        else:
            results[i] = v
    return results


def get_svc_func(args):
    svc, func = defaults(*args, svc="fxa", func=None)
    assert svc in SVCS, f"{svc} is not a valid service in {SVCS}"
    if func:
        funcs = get_svcs_to_funcs()[svc]
        assert func in funcs, f"{func} is not a valid function in {funcs}"
    return svc, func


def parameterized(dec):
    def layer(*args, **kwargs):
        def repl(f):
            return dec(f, *args, **kwargs)

        return repl

    layer.__name__ = dec.__name__
    layer.__doc__ = dec.__doc__
    return layer


@parameterized
def guard(func, env):
    def wrapper(*args, **kwargs):
        task_dict = func(*args, **kwargs)
        if CFG.DEPLOYED_ENV == env and CFG("DEPLOY_TO", None) != env:
            task_dict["actions"] = [
                f"attempting to run {func.__name__} without env var DEPLOY_TO={env} set",
                "false",
            ]
        return task_dict

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


@parameterized
def skip(func, taskname):
    def wrapper(*args, **kwargs):
        task_dict = func(*args, **kwargs)
        envvar = f"SKIP_{taskname.upper()}"
        if CFG(envvar, None):
            task_dict["uptodate"] = [True]
        return task_dict

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


def task_envs():
    """
    show which environment variabls will be used in package, deploy, etc
    """
    return {"task_dep": ["check:noroot"], "actions": [lambda: print(envs("\n"))]}


def check_noroot():
    """
    make sure script isn't run as root
    """
    return {
        "name": "noroot",
        "actions": ['echo "DO NOT RUN AS ROOT!"', "false"],
        "uptodate": [lambda: os.getuid() != 0],
    }


def gen_prog_check(name, program=None):
    """
    genereate program check
    """
    return {
        "name": name,
        "task_dep": ["check:noroot"],
        "actions": [f'echo "required {name} not installed!"', "false"],
        "uptodate": [lambda: check_hash(program or name)],
    }


def gen_file_check(name, func, *patterns, message=None):
    filenames = globs(*patterns, recursive=True)

    def load_test(func, filename):
        try:
            func(open(filename))
            return True
        except:
            return False

    @lru_cache(3)
    def failed_loads():
        return [filename for filename in filenames if not load_test(func, filename)]

    return {
        "name": name,
        "task_dep": ["check:noroot"],
        "actions": [
            f'echo "{func.__module__}.{func.__name__} failed on {filename}"'
            for filename in failed_loads()
        ]
        + [f'echo "{message}"', "false"]
        if len(failed_loads())
        else [],
        "uptodate": [lambda: len(failed_loads()) == 0],
    }


def check_black():
    """
    run black --check in src/ directory
    """
    black_check = f"black --check src/"
    return {
        "name": "black",
        "task_dep": ["check:noroot"],
        "actions": [
            f"{black_check} || echo \"consider running 'doit black'\"",
            "false",
        ],
        "uptodate": [black_check],
    }


def check_precommit():
    return {
        "name": "precommit",
        "task_dep": ["check:noroot"],
        "actions": [f"pre-commit install >> /dev/null"],
    }


def check_reqs():
    """
    check requirements
    """
    installed = call("python3 -m pip freeze")[1].strip().split("\n")
    installed = [tuple(item.split("==")) for item in installed if "==" in item]
    required = [
        line
        for line in open("automation_requirements.txt").read().strip().split("\n")
        if not line.startswith("#")
    ]
    required = [
        tuple(item.split("==")) if "==" in item else (item, None) for item in required
    ]

    @lru_cache(3)
    def check():
        def match_one(iname, iver, rname, rver=None):
            return iname == rname and parse_version(iver) >= parse_version(rver or iver)

        def match_any(installed, rname, rver):
            return any(
                [match_one(iname, iver, rname, rver) for iname, iver in installed]
            )

        return [
            (rname, rver)
            for rname, rver in required
            if not match_any(installed, rname, rver)
        ]

    def report(rname, rver):
        version = f"or at version {rver}" if rver else ""
        return f'echo "-> {rname} is not installed {version}"'

    return {
        "name": "reqs",
        "task_dep": ["check:noroot"],
        "actions": [report(rname, rver) for rname, rver in check()]
        + [
            "echo \"consider running './dodo.py' or 'sudo pip install -r automation_requirements.txt'\"",
            "false",
        ]
        if len(check())
        else [],
        "uptodate": [lambda: len(check()) == 0],
    }


def check_header(f):
    content = f.read()
    if has_header(content):
        return
    msg = (
        f"filename={f.name} does contain header; consider running doit header:{f.name}"
    )
    raise Exception(msg)


def task_check():
    """
    checks: noroot, python3.7, yarn, awscli, json, yaml, black, reqs
    """
    yield check_noroot()
    yield gen_prog_check("python3.7")
    yield gen_prog_check("yarn")
    yield gen_prog_check("docker-compose")
    if not CFG("TRAVIS", None):
        yield gen_prog_check("awscli", "aws")
    yield gen_file_check("json", json.load, "services/**/*.json")
    yield gen_file_check(
        "yaml", yaml.safe_load, "services/**/*.yaml", "services/**/*.yml"
    )
    header_message = "consider running 'doit header:<filename>'"
    yield gen_file_check("header", check_header, "src/**/*.py", message=header_message)
    yield check_black()
    yield check_reqs()
    yield check_precommit()


def task_creds():
    """
    check for valid aws credentials
    """

    def creds_check():
        try:
            call("aws sts get-caller-identity")
            return True
        except CalledProcessError:
            return False

    return {
        "task_dep": ["check"],
        "actions": ['echo "missing valid AWS credentials"', "false"],
        "uptodate": [creds_check],
    }


def task_black():
    """
    run black on src/
    """
    return {"actions": [f"black src/"]}


def task_header():
    """
    apply the HEADER to all the py files under src/
    """

    def ensure_headers():
        for pyfile in pyfiles("src/"):
            with open(pyfile, "r") as old:
                content = old.read()
                if has_header(content):
                    continue
                with open(f"{pyfile}.new", "w") as new:
                    new.write(HEADER.lstrip())
                    new.write("\n")
                    new.write(content.lstrip())
                    os.rename(f"{pyfile}.new", pyfile)

    return {"actions": [ensure_headers]}


@skip("venv")
def task_venv():
    """
    setup virtual env
    """
    app_requirements = f"src/app_requirements.txt"
    test_requirements = f"src/test_requirements.txt"
    return {
        "task_dep": ["check"],
        "actions": [
            f"$(which python3.7) -m venv {VENV}",
            f"{PIP3} install --upgrade pip",
            f'[ -f "{app_requirements}" ] && {PIP3} install -r "{app_requirements}"',
            f'[ -f "{test_requirements}" ] && {PIP3} install -r "{test_requirements}"',
        ],
    }


def task_docker_compose():
    """
    full passthru to docker-compose commands
    """

    def docker_compose(args):
        docker_compose_args = " ".join(args)
        docker_compose_cmd = f"env {envs()} docker-compose {docker_compose_args}"
        call(docker_compose_cmd, stdout=None, stderr=None)

    return {
        "basename": "docker-compose",
        "task_dep": ["check", "tar"],
        "pos_arg": "args",
        "actions": [(docker_compose,)],
    }


def task_yarn():
    """
    Install packages from package.json into the node_modules directory.  Yarn will attempt
    on non-OSX operating systems to check/attempt to install fsevents.
    This is evidenced in the log files by the messages:
        info fsevents@2.0.7: The platform "linux" is incompatible with this module.
        info "fsevents@2.0.7" is an optional dependency and failed compatibility check. Excluding it from installation.
    Reference:
        1. [Filter out fsevents warning/info on non supported OS messages](https://github.com/yarnpkg/yarn/issues/2564)
        2. [Don't warn about incompatible optional dependencies](https://github.com/yarnpkg/yarn/issues/3738)
    """
    return {
        "task_dep": ["check"],
        "actions": [
            "[ -d node_modules/ ] && rm -rf node_modules/ || true",
            "yarn install",
        ],
    }


def task_perf_local():
    """
    run locustio performance tests on local deployment
    """
    FLASK_PORT = 5000
    ENVS = envs(
        LOCAL_FLASK_PORT=FLASK_PORT,
        AWS_ACCESS_KEY_ID="fake-id",
        AWS_SECRET_ACCESS_KEY="fake-key",
        PYTHONPATH=".",
    )
    cmd = f"env {ENVS} {PYTHON3} src/sub/app.py"  # FIXME: should work on hub too...
    return {
        "basename": "perf-local",
        "task_dep": ["check", "venv"],
        "actions": [
            f"{PYTHON3} -m setup develop",
            "echo $PATH",
            LongRunning(
                f"nohup env {envs} {PYTHON3} src/sub/app.py > /dev/null &"
            ),  # FIXME: same as above
            f"cd src/sub/tests/performance && locust -f locustfile.py --host=http://localhost:{FLASK_PORT}",  # FIXME: same
        ],
    }


def task_perf_remote():
    """
    run locustio performance tests on remote deployment
    """
    return {
        "basename": "perf-remote",
        "task_dep": ["check", "venv"],
        "actions": [
            f"{PYTHON3} -m setup develop",
            f"cd src/sub/tests/performance && locust -f locustfile.py --host=https://{CFG.DEPLOY_DOMAIN}",  # FIXME: same as above
        ],
    }


@skip("test")
def task_test():
    """
    run tox in tests/
    """
    return {
        "task_dep": ["check", "venv",],
        "actions": [f"cd {CFG.REPO_ROOT} && tox"],
    }


def task_pytest():
    """
    run pytest per test file
    """
    for filename in Path("src/sub/tests").glob(
        "**/*.py"
    ):  # FIXME: should work on hub too...
        yield {
            "name": filename,
            "task_dep": ["check", "yarn", "venv"],
            "actions": [f"{PYTHON3} -m pytest {filename} --disable-warnings -vxs"],
        }


def task_package():
    """
    run serverless package -v for every service
    """
    for svc in SVCS:
        yield {
            "name": svc,
            "task_dep": ["check", "yarn", "test"],
            "actions": [
                f"cd services/{svc} && env {envs()} {SLS} package --stage {CFG.DEPLOYED_ENV} -v"
            ],
        }


def task_print():
    """
    run serverless print to render the serverless.yml
    """
    return {
        "task_dep": ["yarn"],
        "actions": [
            f"cd services/fxa && env {envs()} {SLS} print --stage {CFG.DEPLOYED_ENV}"
        ],
    }


def task_env_print():
    return {
        "actions": [f"cd {CFG.REPO_ROOT} && env {envs()} > .env",],
    }


def task_tar():
    """
    tar up source files, dereferncing symlinks
    """
    excludes = " ".join(
        [
            f"--exclude={CFG.SRCTAR}",
            "--exclude=__pycache__",
            "--exclude=*.pyc",
            "--exclude=.env",
            "--exclude=sub/tests",
            "--exclude=hub/tests",
            "--exclude=shared/tests",
            "--exclude=.git",
        ]
    )
    for src in SRCS:
        ## it is important to note that this is required to keep the tarballs from
        ## genereating different checksums and therefore different layers in docker
        cmd = f'cd {CFG.REPO_ROOT}/src/{src} && echo "$(git status -s)" > {CFG.REVISION} && tar cvh {excludes} . | gzip -n > {CFG.SRCTAR} && rm {CFG.REVISION}'
        yield {
            "name": src,
            "task_dep": ["check:noroot"],
            "actions": [f'echo "{cmd}"', f"{cmd}"],
        }


def task_local():
    """
    local <svc> [<func>]
    """

    def local(args):
        svc, func = get_svc_func(args)
        local_cmd = f"env {envs()} docker-compose up --build"
        if func:
            local_cmd += f" {func}"
        call(local_cmd, stdout=None, stderr=None)

    return {"task_dep": ["check", "tar"], "pos_arg": "args", "actions": [(local,)]}


def task_local_stop():
    """
    run "docker-compose stop" on any vestigial containers left running from "local" task
    """
    return {"basename": "local-stop", "actions": [f"env {envs()} docker-compose stop"]}


@guard("prod")
def task_deploy():
    """
    deploy <svc> [<func>]
    """

    def deploy(args):
        svc, func = get_svc_func(args)
        if func:
            deploy_cmd = f"cd services/{svc} && env {envs()} {SLS} deploy function --stage {CFG.DEPLOYED_ENV} --aws-s3-accelerate -v --function {func}"
        else:
            deploy_cmd = f"cd services/{svc} && env {envs()} {SLS} deploy --stage {CFG.DEPLOYED_ENV} --aws-s3-accelerate -v"
        call(deploy_cmd, stdout=None, stderr=None)

    return {
        "task_dep": ["check", "creds", "yarn", "test"],
        "pos_arg": "args",
        "actions": [(deploy,)],
    }


@guard("prod")
def task_domain():
    """
    domain <svc> [create|delete]
    """

    def domain(args):
        svc, action = defaults(svc="fxa", action=None)
        assert action in ("create", "delete"), "provide 'create' or 'delete'"
        domain_cmd = f"cd services/{svc} && env {envs()} {SLS} {action}_domain --stage {CFG.DEPLOYED_ENV} -v"
        call(domain_cmd, stdout=None, stderr=None)

    return {
        "task_dep": ["check", "creds", "yarn"],
        "pos_arg": "args",
        "actions": [(domain,)],
    }


def task_remove():
    """
    run serverless remove -v for every service
    """
    for svc in SVCS:
        servicepath = f"services/{svc}"
        yield {
            "name": svc,
            "task_dep": ["check", "creds", "yarn"],
            "actions": [f"cd {servicepath} && env {envs()} {SLS} remove -v"],
        }


def task_pip3list():
    """
    venv/bin/pip3.7 list
    """
    return {"task_dep": ["venv"], "actions": [f"{PIP3} list"]}


def task_curl():
    """
    curl again remote deployment url: /version, /deployed
    """

    def curl(args):
        svc, func = defaults(*args, svc="fxa", func=None)
        assert svc in SVCS, f"{svc} is not a valid service in {SVCS}"
        funcs = (
            [func]
            if func
            else [func for func in get_svcs_to_funcs()[svc] if func != "mia"]
        )
        for func in funcs:
            for route in ("version", "deployed"):
                cmd = f"curl --silent https://{CFG.DEPLOYED_ENV}.{svc}.mozilla-subhub.app/v1/{func}/{route}"
                call(f'echo "{cmd}"; {cmd}', stdout=None, stderr=None)

    return {"pos_arg": "args", "actions": [(curl,)]}


def task_rmrf():
    """
    delete cached files: pycache, pytest, node, venv, doitdb
    """
    rmrf = 'rm -rf "{}" \;'
    spec = """
    pycache:
        __pycache__: d
        '*.pyc': d
    pytest:
        .pytest_cache: d
        .coverage: f
        .tox: d
    node:
        node_modules: d
    venv:
        venv: d
    doitdb:
        .doit.db: f
    """
    for name, targets in yaml.safe_load(spec).items():
        yield {
            "name": name,
            "actions": [
                f"sudo find {CFG.REPO_ROOT} -depth -name {name} -type {type} -exec {rmrf}"
                for name, type in targets.items()
            ],
        }


def task_tidy():
    """
    delete cached files
    """
    TIDY_FILES = [".doit.db", "venv/", ".pytest_cache/"]
    return {
        "actions": [
            "rm -rf " + " ".join(TIDY_FILES),
            'find . | grep -E "(__pycache__|\.pyc$)" | xargs rm -rf',
        ]
    }
