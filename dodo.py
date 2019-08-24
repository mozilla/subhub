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
from os.path import join, dirname, realpath

sys.path.insert(0, join(dirname(realpath(__file__)), 'src'))

from shared.cfg import CFG, call, CalledProcessError

DOIT_CONFIG = {
    'default_tasks': [
        'pull',
        'deploy',
        'count'
    ],
    'verbosity': 2,
}

HEADER = '''
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
'''

SPACE = ' '
NEWLINE = '\n'
VENV = f'{CFG.REPO_ROOT}/venv'
PYTHON3 = f'{VENV}/bin/python3.7'
PIP3 = f'{PYTHON3} -m pip'
MYPY = f'{VENV}/bin/mypy'
NODE_MODULES = f'{CFG.REPO_ROOT}/node_modules'
SLS = f'{NODE_MODULES}/serverless/bin/serverless'
DYNALITE = f'{NODE_MODULES}/.bin/dynalite'
SVCS = [
    svc for svc in os.listdir('services')
    if os.path.isdir(f'services/{svc}') if os.path.isfile(f'services/{svc}/serverless.yml')
]
SRCS = [
    src for src in os.listdir('src/')
    if os.path.isdir(f'src/{src}') if src != 'shared'
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

def load_serverless(svc):
    return yaml.safe_load(open(f'services/{svc}/serverless.yml'))

def get_svcs_to_funcs():
    return {svc: list(load_serverless(svc)['functions'].keys()) for svc in SVCS}

def svc_func(svc, func=None):
    assert svc in SVCS, f"svc '{svc}' not in {SVCS}"
    funcs = get_svcs_to_funcs()[svc]
    if func:
        assert func in funcs, f"for svc '{svc}', func '{func}' not in {funcs}"
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
        if CFG.DEPLOYED_ENV == env and CFG('DEPLOY_TO', None) != env:
            task_dict['actions'] = [
                f'attempting to run {func.__name__} without env var DEPLOY_TO={env} set',
                'false',
            ]
        return task_dict
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper

@parameterized
def skip(func, taskname):
    def wrapper(*args, **kwargs):
        task_dict = func(*args, **kwargs)
        envvar = f'SKIP_{taskname.upper()}'
        if CFG(envvar, None):
            task_dict['uptodate'] = [True]
        return task_dict
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper

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
    run black --check in src/ directory
    '''
    black_check = f'black --check src/'
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
    yield gen_file_check('header', check_header, 'src/**/*.py', message=header_message)
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

@skip('test')
def task_stripe():
    '''
    check to see if STRIPE_API_KEY is set
    '''
    def stripe_check():
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
    run black on src/
    '''
    return {
        'actions': [
            f'black src/'
        ],
    }

def task_header():
    '''
    apply the HEADER to all the py files under src/
    '''
    def ensure_headers():
        for pyfile in pyfiles('src/'):
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

@skip('venv')
def task_venv():
    '''
    setup virtual env
    '''
    app_requirements = f'src/app_requirements.txt'
    test_requirements = f'src/test_requirements.txt'
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
    yield {
        'name': 'stop',
        'task_dep': [
            'check',
            'yarn',
        ],
        'actions': [
            f'kill {running()}',
        ],
        'uptodate': [
            lambda: running() is None
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
            lambda: running(),
        ],
    }

def task_local():
    '''
    run local deployment
    '''
    return {
        'task_dep': [
            'check',
        ],
        'actions': [
            f'docker-compose up --build'
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
    cmd = f'env {ENVS} {PYTHON3} src/sub/app.py' #FIXME: should work on hub too...
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
            LongRunning(f'nohup env {envs} {PYTHON3} src/sub/app.py > /dev/null &'), #FIXME: same as above
            f'cd src/sub/tests/performance && locust -f locustfile.py --host=http://localhost:{FLASK_PORT}' #FIXME: same
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
            f'cd src/sub/tests/performance && locust -f locustfile.py --host=https://{CFG.DEPLOY_DOMAIN}' #FIXME: same as above
        ]
    }

@skip('mypy')
def task_mypy():
    '''
    run mpyp, a static type checker for Python 3
    '''
    for pkg in ('sub', 'hub'):
        yield {
            'name': pkg,
            'task_dep': [
                'check',
                'yarn',
                'venv',
            ],
            'actions': [
                f'cd {CFG.REPO_ROOT}/src && {envs(MYPYPATH="../venv")} {MYPY} -p {pkg}'
            ],
        }

@skip('test')
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
            #'mypy', FIXME: this needs to be activated once mypy is figured out
        ],
        'actions': [
            f'cd {CFG.REPO_ROOT} && tox',
        ],
    }

def task_pytest():
    '''
    run pytest per test file
    '''
    for filename in Path('src/sub/tests').glob('**/*.py'): #FIXME: should work on hub too...
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

def task_tar():
    '''
    tar up source files, dereferncing symlinks
    '''
    excludes = ' '.join([
        f'--exclude={CFG.SRCTAR}',
        '--exclude=__pycache__',
        '--exclude=*.pyc',
        '--exclude=.env',
        '--exclude=.git',
    ])
    for src in SRCS:
        ## it is important to note that this is required to keep the tarballs from
        ## genereating different checksums and therefore different layers in docker
        cmd = f'cd {CFG.REPO_ROOT}/src/{src} && echo "$(git status -s)" > {CFG.REVISION} && tar cvh {excludes} . | gzip -n > {CFG.SRCTAR} && rm {CFG.REVISION}'
        yield {
            'name': src,
            'task_dep': [
                'check:noroot',
                'test',
            ],
            'actions': [
                f'echo "{cmd}"',
                f'{cmd}',
            ],
        }

@guard('prod')
def task_deploy():
    '''
    deploy <svc> [<func>]
    '''
    def deploy(args):
        svc, func = svc_func(*args)
        if func:
            deploy_cmd = f'cd services/{svc} && env {envs()} {SLS} deploy function --stage {CFG.DEPLOYED_ENV} --aws-s3-accelerate -v --function {func}'
        else:
            deploy_cmd = f'cd services/{svc} && env {envs()} {SLS} deploy --stage {CFG.DEPLOYED_ENV} --aws-s3-accelerate -v'
        call(deploy_cmd, stdout=None, stderr=None)
    return {
        'task_dep': [
            'check',
            'creds',
            'stripe',
            'yarn',
            'test',
        ],
        'pos_arg': 'args',
        'actions': [(deploy,)],
    }

@guard('prod')
def task_domain():
    '''
    domain <svc> [create|delete]
    '''
    def domain(args):
        svc, action = svc_func(*args)
        assert action in ('create', 'delete'), "provide 'create' or 'delete'"
        domain_cmd = f'cd services/{svc} && env {envs()} {SLS} {action}_domain --stage {CFG.DEPLOYED_ENV} -v'
        call(domain_cmd, stdout=None, stderr=None)
    return {
        'pos_arg': 'args',
        'actions': [(domain,)],
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
    def curl(args):
        svc, func = svc_func(*args)
        funcs = [func] if func else [func for func in get_svcs_to_funcs()[svc] if func != 'mia']
        for func in funcs:
            for route in ('version', 'deployed'):
                cmd = f'curl --silent https://{CFG.DEPLOYED_ENV}.{svc}.mozilla-subhub.app/v1/{func}/{route}'
                call(f'echo "{cmd}"; {cmd}', stdout=None, stderr=None)
    return {
        'pos_arg': 'args',
        'actions': [(curl,)],
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
                f'sudo find {CFG.REPO_ROOT} -depth -name {name} -type {type} -exec {rmrf}'
                for name, type in targets.items()
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
