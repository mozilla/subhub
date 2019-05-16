#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import pwd
import sys
import glob
import json
import difflib
import contextlib

from doit.tools import LongRunning
from pathlib import Path
from pkg_resources import parse_version
from subprocess import Popen, check_call, check_output, CalledProcessError, PIPE

from subhub.cfg import CFG

LOG_LEVELS = [
    'DEBUG',
    'INFO',
    'WARNING',
    'ERROR',
    'CRITICAL',
]

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
SLS = f'{CFG.APP_REPOROOT}/node_modules/serverless/bin/serverless'
DYNALITE = f'{CFG.APP_REPOROOT}/node_modules/.bin/dynalite'
SVCS = [svc for svc in os.listdir('services') if os.path.isdir(f'services/{svc}') if os.path.isfile(f'services/{svc}/serverless.yml')]

def envs(sep=' '):
    return sep.join([
        f'APP_DEPENV={CFG.APP_DEPENV}',
        f'APP_PROJNAME={CFG.APP_PROJNAME}',
        f'APP_BRANCH={CFG.APP_BRANCH}',
        f'APP_REVISION={CFG.APP_REVISION}',
        f'APP_VERSION={CFG.APP_VERSION}',
        f'APP_REMOTE_ORIGIN_URL={CFG.APP_REMOTE_ORIGIN_URL}',
    ])

@contextlib.contextmanager
def cd(path):
    old_path = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_path)

def call(cmd, stdout=PIPE, stderr=PIPE, shell=True, nerf=False, throw=True, verbose=False):
    if verbose or nerf:
        print(cmd)
    if nerf:
        return (None, 'nerfed', 'nerfed')
    process = Popen(cmd, stdout=stdout, stderr=stderr, shell=shell)
    _stdout, _stderr = [stream.decode('utf-8') for stream in process.communicate()]
    exitcode = process.poll()
    if verbose:
        if _stdout:
            print(_stdout)
        if _stderr:
            print(_stderr)
    if throw and exitcode:
        raise CalledProcessError(exitcode, f'cmd={cmd}; stdout={_stdout}; stderr={_stderr}')
    return exitcode, _stdout, _stderr

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
        check_call(f'hash {program}', shell=True, stdout=PIPE, stderr=PIPE)
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

def task_noroot():
    '''
    make sure script isn't run as root
    '''
    then = 'echo "   DO NOT RUN AS ROOT!"; echo; exit 1'
    bash = f'if [[ $(id -u) -eq 0 ]]; then {then}; fi'
    return {
        'actions': [
            f'bash -c \'{bash}\'',
        ],
    }

def task_venv():
    '''
    setup virtual env
    '''
    venv = f'{CFG.APP_PROJPATH}/.venv'
    pip3 = f'{venv}/bin/pip3'
    appreqs = f'{CFG.APP_PROJPATH}/requirements.txt'
    testreqs = f'{CFG.APP_PROJPATH}/tests/requirements.txt'
    return {
        'task_dep': [
            'noroot',
        ],
        'actions': [
            f'virtualenv --python=$(which python3.7) {venv}',
            f'{pip3} install --upgrade pip',
            f'[ -f "{appreqs}" ] && {pip3} install -r "{appreqs}" || true',
            f'[ -f "{testreqs}" ] && {pip3} install -r "{testreqs}" || true',
        ]
    }

def task_dynalite():
    '''
    start, stop the dynalite db
    '''
    cmd = f'{DYNALITE} --port {CFG.DYNALITE_PORT}'
    msg = f'dyanlite server started on {CFG.DYNALITE_PORT} logging to {CFG.DYNALITE_FILE}'
    def running():
        '''
        return pid of running dyanlite
        '''
        pid = None
        try:
            pid = call(f'lsof -i:{CFG.DYNALITE_PORT} -t')[1].strip()
        except CalledProcessError:
            return None
        try:
            args = call(f'ps -p {pid} -o args=')[1].strip()
        except CalledProcessError:
            return None
        if f'{cmd}' in args:
            return pid
        return None
    pid = running()
    yield {
        'name': 'stop',
        'task_dep': [
            'noroot',
            'check',
            'npm',
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
            'noroot',
            'check',
            'npm',
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
    python3 = f'{CFG.APP_PROJPATH}/.venv/bin/python3.7'
    aws = ' '.join([
        'AWS_ACCESS_KEY_ID=fake-id',
        'AWS_SECRET_ACCESS_KEY=fake-key',
        'PYTHONPATH=.',
    ])
    return {
        'task_dep': [
            'noroot',
            'venv',
            'dynalite:start',
        ],
        'actions': [
            f'{python3} -m setup develop',
            'echo $PATH',
            f'{aws} {python3} subhub/app.py',
        ],
    }

def task_pull():
    '''
    do a safe git pull
    '''
    submods = check_output("git submodule status | awk '{print $2}'", shell=True).decode('utf-8').split()
    test = '`git diff-index --quiet HEAD --`'
    pull = 'git pull --rebase'
    update = 'git submodule update --remote'
    dirty = 'echo "refusing to \'{cmd}\' because the tree is dirty"'
    dirty_pull, dirty_update = [dirty.format(cmd=cmd) for cmd in (pull, update)]

    yield {
        'name': 'mozilla-it/props-bot',
        'actions': [
            f'if {test}; then {pull}; else {dirty_pull}; exit 1; fi',
        ],
    }

    for submod in submods:
        yield {
            'name': submod,
            'actions': [
                f'cd {submod} && if {test}; then {update}; else {dirty_update}; exit 1; fi',
            ],
        }

def check_black():
    '''
    run black --check in subhub directory
    '''
    black_check = f'black --check {CFG.APP_PROJPATH}'
    return {
        'name': 'black',
        'actions': [
            f'{black_check} || echo "consider running \'doit black\'"; false'
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
    required = open('requirements.txt').read().strip().split('\n')
    required = [tuple(item.split('==')) if '==' in item else (item, None) for item in required]
    def uptodate():
        '''
        uptodate
        '''
        def match_one(iname, iver, rname, rver=None):
            '''
            match one
            '''
            return (iname == rname and parse_version(iver) >= parse_version(rver or iver))
        def match_any(installed, rname, rver):
            '''
            match any
            '''
            return any([match_one(iname, iver, rname, rver) for iname, iver in installed])
        return all([match_any(installed, rname, rver) for rname, rver in required])

    return {
        'name': 'reqs',
        'actions':[
            'echo "consider installing requirements.txt by running ./dodo.py"',
            'false',
        ],
        'uptodate': [
            uptodate,
        ],
    }

def task_check():
    '''
    checks: black, reqs
    '''
    yield check_black()
    yield check_reqs()

def task_npm():
    '''
    run npm install on package.json
    '''
    def uptodate():
        '''
        custom uptodate to check for outdated npm pkgs
        '''
        try:
            call('npm outdated')
            return False
        except CalledProcessError:
            return True
    return {
        'task_dep': [
            'noroot',
            'check',
        ],
        'actions': [
            '[ -d node_modules/ ] && rm -rf node_modules/ || true',
            'npm install',
        ],
        'uptodate': [
            uptodate
        ],
    }

def task_test():
    '''
    run tox in tests/
    '''
    return {
        'task_dep': [
            'noroot',
            'check',
            'npm',
        ],
        'actions': [
            f'cd {CFG.APP_REPOROOT} && tox',
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
                'noroot',
                'check',
                'npm',
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
        yield {
            'name': svc,
            'task_dep': [
                'noroot',
                'check',
                'npm',
            ],
            'actions': [
                f'cd {servicepath} && env {envs()} {SLS} deploy --stage {CFG.APP_DEPENV} -v',
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
                'noroot',
                'check',
                'npm',
            ],
            'actions': [
                f'cd {servicepath} && env {envs()} {SLS} remove -v',
            ],
        }

def task_rmcache():
    '''
    recursively delete python cache files
    '''
    rmrf = 'rm -rf "{}" \;'
    names_types = {
        '__pycache__': 'd',
        '.pytest_cache': 'd',
        'node_modules': 'd',
        '.serverless': 'd',
        '.venv': 'd',
        '.eggs': 'd',
        '.tox': 'd',
        '*.pyc': 'f',
        '.coverage': 'f',
        '.doit.db': 'f',
    }
    return {
        'actions': [
            f'sudo find {CFG.APP_REPOROOT} -depth -name {name} -type {type} -exec {rmrf}' for name, type in names_types.items()
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

def task_black():
    '''
    run black on subhub/
    '''
    return {
        'actions': [
            f'black {CFG.APP_PROJPATH}',
        ],
    }

if __name__ == '__main__':
    cmd = 'sudo python3 -m pip install -r requirements.txt'
    answer = input(cmd + '[Y/n] ')
    if answer in ('', 'Y', 'y', 'Yes', 'YES', 'yes'):
        os.system(cmd)
    else:
        print('requirements.txt NOT installed!')
