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

SPACE = ' '
NEWLINE = '\n'
VENV = f'{CFG.APP_REPOROOT}/venv'
PYTHON3 = f'{VENV}/bin/python3.7'
PIP3 = f'{PYTHON3} -m pip'
NODE_MODULES = f'{CFG.APP_REPOROOT}/node_modules'
SLS = f'{NODE_MODULES}/serverless/bin/serverless'
DYNALITE = f'{NODE_MODULES}/.bin/dynalite'
SVCS = [svc for svc in os.listdir('services') if os.path.isdir(f'services/{svc}') if os.path.isfile(f'services/{svc}/serverless.yml')]

def envs(sep=' ', **kwargs):
    envs = dict(
        APP_DEPENV=CFG.APP_DEPENV,
        APP_PROJNAME=CFG.APP_PROJNAME,
        APP_BRANCH=CFG.APP_BRANCH,
        APP_REVISION=CFG.APP_REVISION,
        APP_VERSION=CFG.APP_VERSION,
        APP_REMOTE_ORIGIN_URL=CFG.APP_REMOTE_ORIGIN_URL,
        APP_LOG_LEVEL=CFG.APP_LOG_LEVEL,
        NEW_RELIC_ACCOUNT_ID=CFG.NEW_RELIC_ACCOUNT_ID,
        NEW_RELIC_TRUSTED_ACCOUNT_ID=CFG.NEW_RELIC_TRUSTED_ACCOUNT_ID,
        NEW_RELIC_SERVERLESS_MODE_ENABLED=CFG.NEW_RELIC_SERVERLESS_MODE_ENABLED,
        NEW_RELIC_DISTRIBUTED_TRACING_ENABLED=CFG.NEW_RELIC_DISTRIBUTED_TRACING_ENABLED,
    )
    return sep.join([
        f'{key}={value}' for key, value in dict(envs, **kwargs).items()
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

def pyfiles(path, exclude=None):
    pyfiles = set(Path(path).rglob('*.py')) - set(Path(exclude).rglob('*.py') if exclude else [])
    return [pyfile.as_posix() for pyfile in pyfiles]

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

def gen_file_check(name, func, *patterns):
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
        ] + ['false'] if len(failed_loads()) else [],
        'uptodate': [
            lambda: len(failed_loads()) == 0,
        ]
    }

def check_black():
    '''
    run black --check in subhub directory
    '''
    black_check = f'black --check {CFG.APP_PROJPATH}'
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
            f'black {CFG.APP_PROJPATH}',
        ],
    }

def task_venv():
    '''
    setup virtual env
    '''
    app_requirements = f'{CFG.APP_PROJPATH}/requirements.txt'
    test_requirements = f'{CFG.APP_PROJPATH}/tests/requirements.txt'
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
    msg = f'dyanlite server started on {CFG.DYNALITE_PORT} logging to {CFG.DYNALITE_FILE}'
    def running():
        pid = None
        try:
            pid = call(f'lsof -i:{CFG.DYNALITE_PORT} -t')[1].strip()
        except CalledProcessError:
            return None
        try:
            args = call(f'ps -p {pid} -o args=')[1].strip()
        except CalledProcessError:
            return None
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
    run locally
    '''
    ID='fake-id'
    KEY='fake-key'
    PP='.'
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
            f'env {envs(AWS_ACCESS_KEY_ID=ID,AWS_SECRET_ACCESS_KEY=KEY,PYTHONPATH=PP)} {PYTHON3} subhub/app.py',
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
            f'cd {CFG.APP_REPOROOT} && tox',
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
                f'cd services/{svc} && env {envs()} {SLS} package --stage {CFG.APP_DEPENV} -v',
            ],
        }

def task_deploy():
    '''
    run serverless deploy -v for every service
    '''
    for svc in SVCS:
        servicepath = f'services/{svc}'
        curl = f'curl --silent https://{CFG.APP_DEPENV}.{svc}.mozilla-subhub.app/v1/version'
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
                f'cd {servicepath} && env {envs()} {SLS} deploy --stage {CFG.APP_DEPENV} --aws-s3-accelerate -v',
                f'echo "{curl}"',
                f'{curl}',
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
                f'sudo find {CFG.APP_REPOROOT} -depth -name {name} -type {type} -exec {rmrf}' for name, type in targets.items()
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

if __name__ == '__main__':
    cmd = 'sudo python3 -m pip install -r automation_requirements.txt'
    answer = input(cmd + '[Y/n] ')
    if answer in ('', 'Y', 'y', 'Yes', 'YES', 'yes'):
        os.system(cmd)
    else:
        print('automation_requirements.txt NOT installed!')
