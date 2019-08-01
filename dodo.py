#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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

from ruamel import yaml
from functools import lru_cache
from doit.tools import LongRunning
from pathlib import Path
from pkg_resources import parse_version

from subhub.cfg import CFG, call, CalledProcessError

DOIT_CONFIG = {
    'default_tasks': [
        'pull',
        'deploy',
        'count'
    ],
    'verbosity': 2,
}

HEADER = '''
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
'''

SPACE = ' '
NEWLINE = '\n'
VENV = f'{CFG.REPO_ROOT}/venv'
PYTHON3 = f'{VENV}/bin/python3.7'
PIP3 = f'{PYTHON3} -m pip'
NODE_MODULES = f'{CFG.REPO_ROOT}/node_modules'
SLS = f'{NODE_MODULES}/serverless/bin/serverless'
DYNALITE = f'{NODE_MODULES}/.bin/dynalite'
SVCS = [
    svc for svc in os.listdir('services')
    if os.path.isdir(f'services/{svc}') if os.path.isfile(f'services/{svc}/serverless.yml')
]

mutex = threading.Lock()

def envs(sep=' ', **kwargs):
    envs = dict(
        DEPLOYED_ENV=CFG.DEPLOYED_ENV,
        PROJECT_NAME=CFG.PROJECT_NAME,
        BRANCH=CFG.BRANCH,
        REVISION=CFG.REVISION,
        VERSION=CFG.VERSION,
        REMOTE_ORIGIN_URL=CFG.REMOTE_ORIGIN_URL,
        LOG_LEVEL=CFG.LOG_LEVEL,
        NEW_RELIC_ACCOUNT_ID=CFG.NEW_RELIC_ACCOUNT_ID,
        NEW_RELIC_TRUSTED_ACCOUNT_ID=CFG.NEW_RELIC_TRUSTED_ACCOUNT_ID,
        NEW_RELIC_SERVERLESS_MODE_ENABLED=CFG.NEW_RELIC_SERVERLESS_MODE_ENABLED,
        NEW_RELIC_DISTRIBUTED_TRACING_ENABLED=CFG.NEW_RELIC_DISTRIBUTED_TRACING_ENABLED,
        PROFILING_ENABLED=CFG.PROFILING_ENABLED,
        DEPLOY_DOMAIN=CFG.DEPLOY_DOMAIN,
        DEPLOYED_BY=CFG.DEPLOYED_BY,
        DEPLOYED_WHEN=CFG.DEPLOYED_WHEN,
    )
    return sep.join([
        f'{key}={value}' for key, value in sorted(dict(envs, **kwargs).items())
    ])

def globs(*patterns, **kwargs):
    return itertools.chain.from_iterable(glob.iglob(pattern, **kwargs) for pattern in patterns)

def docstr_format(*args, **kwargs):
    def wrapper(func):
        func.__doc__ = func.__doc__.format(*args, **kwargs)
        return func
    return wrapper

class UnknownPkgmgrError(Exception):
    def __init__(self):
        super(UnknownPkgmgrError, self).__init__('unknown pkgmgr!')

def check_hash(program):
    try:
        call(f'hash {program}')
        return True
    except CalledProcessError:
        return False

def get_pkgmgr():
    if check_hash('dpkg'):
        return 'deb'
    elif check_hash('rpm'):
        return 'rpm'
    elif check_hash('brew'):
        return 'brew'
    raise UnknownPkgmgrError

def has_header(content):
    return content.startswith(HEADER.lstrip())

def pyfiles(path, exclude=None):
    pyfiles = set(Path(path).rglob('*.py')) - set(Path(exclude).rglob('*.py') if exclude else [])
    return [pyfile.as_posix() for pyfile in pyfiles]

# TODO: This needs to check for the existence of the dependency prior to execution or update project requirements.
def task_count():
    '''
    use the cloc utility to count lines of code
    '''
    excludes = [
        'dist',
        'venv',
        '__pycache__',
        '*.egg-info',
    ]
    excludes = '--exclude-dir=' + ','.join(excludes)
    scandir = os.path.dirname(__file__)
    return {
        'actions': [
            f'cloc {excludes} {scandir}',
        ],
        'uptodate': [
            lambda: not check_hash('cloc'),
        ],
    }

def task_envs():
    '''
    show which environment variabls will be used in package, deploy, etc
    '''
    return {
        'task_dep': [
            'check:noroot',
        ],
        'actions': [
            lambda: print(envs('\n')),
        ],
    }

def check_noroot():
    '''
    make sure script isn't run as root
    '''
    return {
        'name': 'noroot',
        'actions': [
            'echo "DO NOT RUN AS ROOT!"',
            'false',
        ],
        'uptodate': [
            lambda: os.getuid() != 0,
        ],
    }

def gen_prog_check(name, program=None):
    '''
    genereate program check
    '''
    return {
        'name': name,
        'task_dep': [
            'check:noroot',
        ],
        'actions': [
            f'echo "required {name} not installed!"',
            'false',
        ],
        'uptodate': [
            lambda: check_hash(program or name)
        ]
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
        'name': name,
        'task_dep': [
            'check:noroot',
        ],
        'actions': [
            f'echo "{func.__module__}.{func.__name__} failed on {filename}"' for filename in failed_loads()
        ] + [
            f'echo "{message}"',
            'false'
        ] if len(failed_loads()) else [],
        'uptodate': [
            lambda: len(failed_loads()) == 0,
        ]
    }

def check_black():
    '''
    run black --check in subhub directory
    '''
    black_check = f'black --check {CFG.PROJECT_PATH}'
    return {
        'name': 'black',
        'task_dep': [
            'check:noroot',
        ],
        'actions': [
            f'{black_check} || echo "consider running \'doit black\'"',
            'false',
        ],
        'uptodate': [
            black_check,
        ]
    }

def check_reqs():
    '''
    check requirements
    '''
    installed = call('python3 -m pip freeze')[1].strip().split('\n')
    installed = [tuple(item.split('==')) for item  in installed if '==' in item]
    required = [line for line in open('automation_requirements.txt').read().strip().split('\n') if not line.startswith('#')]
    required = [tuple(item.split('==')) if '==' in item else (item, None) for item in required]
    @lru_cache(3)
    def check():
        def match_one(iname, iver, rname, rver=None):
            return (iname == rname and parse_version(iver) >= parse_version(rver or iver))
        def match_any(installed, rname, rver):
            return any([match_one(iname, iver, rname, rver) for iname, iver in installed])
        return [(rname, rver) for rname, rver in required if not match_any(installed, rname, rver)]
    def report(rname, rver):
        version = f'or at version {rver}' if rver else ''
        return f'echo "-> {rname} is not installed {version}"'
    return {
        'name': 'reqs',
        'task_dep': [
            'check:noroot',
        ],
        'actions': [
            report(rname, rver) for rname, rver in check()
        ] + [
            'echo "consider running \'./dodo.py\' or \'sudo pip install -r automation_requirements.txt\'"',
            'false',
        ] if len(check()) else [],
        'uptodate': [
            lambda: len(check()) == 0,
        ],
    }

def check_header(f):
    content = f.read()
    if has_header(content):
        return
    msg = f'filename={f.name} does contain header; consider running doit header:{f.name}'
    raise Exception(msg)

def task_check():
    '''
    checks: noroot, python3.7, yarn, awscli, json, yaml, black, reqs
    '''
    yield check_noroot()
    yield gen_prog_check('python3.7')
    yield gen_prog_check('yarn')
    if not CFG('TRAVIS', None):
        yield gen_prog_check('awscli', 'aws')
    yield gen_file_check('json', json.load, 'services/**/*.json')
    yield gen_file_check('yaml', yaml.safe_load, 'services/**/*.yaml', 'services/**/*.yml')
    header_message = "consider running 'doit header:<filename>'"
    yield gen_file_check('header', check_header, 'subhub/**/*.py', message=header_message)
    yield check_black()
    yield check_reqs()

def task_creds():
    '''
    check for valid aws credentials
    '''
    def creds_check():
        try:
            call('aws sts get-caller-identity')
            return True
        except CalledProcessError:
            return False
    return {
        'task_dep': [
            'check',
        ],
        'actions': [
            'echo "missing valid AWS credentials"',
            'false',
        ],
        'uptodate': [
            creds_check
        ],
    }

def task_stripe():
    '''
    check to see if STRIPE_API_KEY is set
    '''
    def stripe_check():
        if os.environ.get('SKIP_TESTS', None):
            return True
        try:
            CFG.STRIPE_API_KEY
        except:
            return False
        return True
    return {
        'task_dep': [
            'check',
        ],
        'actions': [
            'echo "missing STRIPE_API_KEY env var or .env entry"',
            'false',
        ],
        'uptodate': [
            stripe_check,
        ]
    }

def task_black():
    '''
    run black on subhub/
    '''
    return {
        'actions': [
            f'black {CFG.PROJECT_PATH}',
        ],
    }

def task_header():
    '''
    apply the HEADER to all the py files under subhub/
    '''
    def ensure_headers():
        for pyfile in pyfiles('subhub/'):
            with open(pyfile, 'r') as old:
                content = old.read()
                if has_header(content):
                    continue
                with open(f'{pyfile}.new', 'w') as new:
                    new.write(HEADER.lstrip())
                    new.write('\n')
                    new.write(content.lstrip())
                    os.rename(f'{pyfile}.new', pyfile)
    return {
        'actions': [
            ensure_headers,
        ],
    }

def task_venv():
    '''
    setup virtual env
    '''
    app_requirements = f'{CFG.PROJECT_PATH}/requirements.txt'
    test_requirements = f'{CFG.PROJECT_PATH}/tests/requirements.txt'
    return {
        'task_dep': [
            'check',
        ],
        'actions': [
            f'virtualenv --python=$(which python3.7) {VENV}',
            f'{PIP3} install --upgrade pip',
            f'[ -f "{app_requirements}" ] && {PIP3} install -r "{app_requirements}"',
            f'[ -f "{test_requirements}" ] && {PIP3} install -r "{test_requirements}"',
        ],
        'uptodate': [
            lambda: os.environ.get('SKIP_VENV', None),
        ],
    }

def task_dynalite():
    '''
    dynalite db for testing and local runs: start, stop
    '''
    cmd = f'{DYNALITE} --port {CFG.DYNALITE_PORT}'
    msg = f'dynalite server started on {CFG.DYNALITE_PORT} logging to {CFG.DYNALITE_FILE}'
    def running():
        mutex.acquire()
        pid = None
        try:
            pid = call(f'lsof -i:{CFG.DYNALITE_PORT} -t')[1].strip()
        except CalledProcessError:
            return None
        finally:
            mutex.release()
        mutex.acquire()
        try:
            args = call(f'ps -p {pid} -o args=')[1].strip()
        except CalledProcessError:
            return None
        finally:
            mutex.release()
        if cmd in args:
            return pid
        return None
    pid = running()
    yield {
        'name': 'stop',
        'task_dep': [
            'check',
            'yarn',
        ],
        'actions': [
            f'kill {pid}',
        ],
        'uptodate': [
            lambda: pid is None
        ],
    }
    yield {
        'name': 'start',
        'task_dep': [
            'check',
            'yarn',
            'dynalite:stop',
        ],
        'actions': [
            LongRunning(f'nohup {cmd} > {CFG.DYNALITE_FILE} &'),
            f'echo "{msg}"',
        ],
        'uptodate': [
            lambda: pid,
        ],
    }

def task_local():
    '''
    run local deployment
    '''
    ENVS=envs(
        AWS_ACCESS_KEY_ID='fake-id',
        AWS_SECRET_ACCESS_KEY='fake-key',
        PYTHONPATH='.'
    )
    return {
        'task_dep': [
            'check',
            'stripe',
            'venv',
            'test',
            'dynalite:start',
        ],
        'actions': [
            f'{PYTHON3} -m setup develop',
            'echo $PATH',
            f'env {ENVS} {PYTHON3} subhub/app.py',
        ],
    }

def task_yarn():
    '''
    run yarn install on package.json
    '''
    return {
        'task_dep': [
            'check',
        ],
        'actions': [
            '[ -d node_modules/ ] && rm -rf node_modules/ || true',
            'yarn install',
        ],
    }

def task_perf_local():
    '''
    run locustio performance tests on local deployment
    '''
    FLASK_PORT=5000
    ENVS=envs(
        LOCAL_FLASK_PORT=FLASK_PORT,
        AWS_ACCESS_KEY_ID='fake-id',
        AWS_SECRET_ACCESS_KEY='fake-key',
        PYTHONPATH='.'
    )
    cmd = f'env {ENVS} {PYTHON3} subhub/app.py'
    return {
        'basename': 'perf-local',
        'task_dep':[
            'check',
            'stripe',
            'venv',
            'dynalite:start'
        ],
        'actions':[
            f'{PYTHON3} -m setup develop',
            'echo $PATH',
            LongRunning(f'nohup env {envs} {PYTHON3} subhub/app.py > /dev/null &'),
            f'cd subhub/tests/performance && locust -f locustfile.py --host=http://localhost:{FLASK_PORT}'
        ]
    }

def task_perf_remote():
    '''
    run locustio performance tests on remote deployment
    '''
    return {
        'basename': 'perf-remote',
        'task_dep':[
            'check',
            'stripe',
            'venv',
        ],
        'actions':[
            f'{PYTHON3} -m setup develop',
            f'cd subhub/tests/performance && locust -f locustfile.py --host=http://{CFG.DEPLOY_DOMAIN}'
        ]
    }


def task_test():
    '''
    run tox in tests/
    '''
    return {
        'task_dep': [
            'check',
            'stripe',
            'yarn',
            'venv',
            'dynalite:stop',
        ],
        'actions': [
            f'cd {CFG.REPO_ROOT} && tox',
        ],
        'uptodate': [
            lambda: os.environ.get('SKIP_TESTS', None),
        ],
    }

def task_pytest():
    '''
    run pytest per test file
    '''
    for filename in Path('subhub/tests').glob('**/*.py'):
        yield {
            'name': filename,
            'task_dep': [
                'check',
                'stripe',
                'yarn',
                'venv',
                'dynalite:stop',
            ],
            'actions': [
                f'{PYTHON3} -m pytest {filename} --disable-warnings -vxs',
            ],
        }

def task_package():
    '''
    run serverless package -v for every service
    '''
    for svc in SVCS:
        yield {
            'name': svc,
            'task_dep': [
                'check',
                'yarn',
                'test',
            ],
            'actions': [
                f'cd services/{svc} && env {envs()} {SLS} package --stage {CFG.DEPLOYED_ENV} -v',
            ],
        }

def task_deploy():
    '''
    run serverless deploy -v for every service
    '''
    for svc in SVCS:
        servicepath = f'services/{svc}'
        if svc != "missing-events":
            curl = f'curl --silent https://{CFG.DEPLOYED_ENV}.{svc}.mozilla-subhub.app/v1/version'
            describe = 'git describe --abbrev=7'
            yield {
                'name': svc,
                'task_dep': [
                    'check',
                    'creds',
                    'stripe',
                    'yarn',
                    'test',
                ],
                'actions': [
                    f'cd {servicepath} && env {envs()} {SLS} deploy --stage {CFG.DEPLOYED_ENV} --aws-s3-accelerate -v',
                    f'echo "{curl}"',
                    f'{curl}',
                    f'echo "{describe}"',
                    f'{describe}',
                ],
            }
        else:
            describe = 'git describe --abbrev=7'
            yield {
                'name': svc,
                'task_dep': [
                    'check',
                    'creds',
                    'stripe',
                    'yarn',
                    'test',
                ],
                'actions': [
                    f'cd {servicepath} && env {envs()} {SLS} deploy --stage {CFG.DEPLOYED_ENV} --aws-s3-accelerate -v',
                    f'echo "{describe}"',
                    f'{describe}',
                ],
            }


def task_remove():
    '''
    run serverless remove -v for every service
    '''
    for svc in SVCS:
        servicepath = f'services/{svc}'
        yield {
            'name': svc,
            'task_dep': [
                'check',
                'creds',
                'yarn',
            ],
            'actions': [
                f'cd {servicepath} && env {envs()} {SLS} remove -v',
            ],
        }

def task_pip3list():
    '''
    venv/bin/pip3.7 list
    '''
    return {
        'task_dep': [
            'venv',
        ],
        'actions': [
            f'{PIP3} list',
        ],
    }

def task_curl():
    '''
    curl again remote deployment url: /version, /deployed
    '''
    for route in ('deployed', 'version'):
        yield {
            'name': route,
            'actions': [
                f'curl --silent https://{CFG.DEPLOYED_ENV}.fxa.mozilla-subhub.app/v1/{route}',
            ],
        }

def task_rmrf():
    '''
    delete cached files: pycache, pytest, node, venv, doitdb
    '''
    rmrf = 'rm -rf "{}" \;'
    spec = '''
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
    '''
    for name, targets in yaml.safe_load(spec).items():
        yield {
            'name': name,
            'actions': [
                f'sudo find {CFG.REPO_ROOT} -depth -name {name} -type {type} -exec {rmrf}' for name, type in targets.items()
            ],
        }

def task_tidy():
    '''
    delete cached files
    '''
    TIDY_FILES = [
        '.doit.db',
        'venv/',
        '.pytest_cache/',
    ]
    return {
        'actions': [
            'rm -rf ' + ' '.join(TIDY_FILES),
            'find . | grep -E "(__pycache__|\.pyc$)" | xargs rm -rf',
        ],
    }

def task_draw():
    """generate image from a dot file"""
    return {
        'file_dep': ['tasks.dot'],
        'targets': ['tasks.png'],
        'actions': ['dot -Tpng %(dependencies)s -o %(targets)s'],
    }

if __name__ == '__main__':
    cmd = 'sudo python3 -m pip install -r automation_requirements.txt'
    answer = input(cmd + '[Y/n] ')
    if answer in ('', 'Y', 'y', 'Yes', 'YES', 'yes'):
        os.system(cmd)
    else:
        print('automation_requirements.txt NOT installed!')
