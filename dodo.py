#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sh
import pwd
import sys
import glob

from doit import get_var
from ruamel import yaml
from pathlib import Path
from subprocess import check_call, check_output, CalledProcessError, PIPE

from subhub.cfg import CFG

## https://docs.docker.com/compose/compose-file/compose-versioning/
#MINIMUM_DOCKER_COMPOSE_VERSION = '1.13' # allows compose format 3.0

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
        'rmimages',
        'rmvolumes',
        'count'
    ],
    'verbosity': 2,
}

SPACE = ' '
NEWLINE = '\n'

SLS = f'{CFG.APP_REPOROOT}/node_modules/serverless/bin/serverless'
SVCS = [svc for svc in os.listdir('services') if os.path.isdir(f'services/{svc}')]

def envs(sep):
    return sep.join([
        f'APP_PROJNAME={CFG.APP_PROJNAME}',
        f'APP_DEPENV={CFG.APP_DEPENV}',
        f'APP_VERSION={CFG.APP_VERSION}',
        f'APP_BRANCH={CFG.APP_BRANCH}',
        f'APP_DEPENV={CFG.APP_DEPENV}',
        f'APP_REVISION={CFG.APP_REVISION}',
        f'APP_REMOTE_ORIGIN_URL={CFG.APP_REMOTE_ORIGIN_URL}',
        f'APP_INSTALLPATH={CFG.APP_INSTALLPATH}',
    ])

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

def task_checkreqs():
    '''
    check for required software
    '''
    DEBS = [
        'docker-ce',
    ]
    RPMS = [
        'docker-ce',
    ]
    return {
        'deb': {
            'actions': [f'dpkg -s {deb} 2>&1 >/dev/null' for deb in DEBS],
        },
        'rpm': {
            'actions': ['rpm -q ' + rpm for rpm in RPMS], #FIXME: probably silent this?
        },
        'brew': {
            'actions': ['true'], #FIXME: check that this works?
        }
    }[get_pkgmgr()]

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

def task_test():
    '''
    run tox in tests/
    '''
    return {
        'task_dep': [
            'noroot',
        ],
        'actions': [
            f'cd {CFG.APP_PROJPATH} && tox',
        ],
    }

ESCAPE_REGEX = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
OUTDATED_REGEX = re.compile(' +'.join([
    '(?P<package>.*)',
    '(?P<current>MISSING|[0-9]+(\.[0-9]+)+)',
    '(?P<wanted>[0-9]+(\.[0-9]+)+)',
    '(?P<latest>[0-9]+(\.[0-9]+)+)',
    '(?P<location>.*)',
]))
def task_setup():
    '''
    run all of the setup steps
    '''
    def uptodate():
        '''
        custom uptodate to check for outdated npm pkgs
        '''
        result = sh.npm('outdated').strip()
        for line in result.split('\n'):
            print(line)
            line = ESCAPE_REGEX.sub('', line)
            if line.startswith('Package') or line.startswith('undefined'):
                continue
            match = OUTDATED_REGEX.match(line)
            if match.groupdict()['current'] != match.groupdict()['wanted']:
                return False
        return True
    return {
        'task_dep': [
            'noroot',
        ],
        'actions': [
            'npm install',
        ],
        'uptodate': [
            uptodate,
        ],
    }

def task_deploy():
    '''
    run serverless deploy -v for every service
    '''
    for svc in SVCS:
        yield {
            'name': svc,
            'task_dep': [
                'noroot',
                'setup',
            ],
            'actions': [
                f'cd services/{svc} && {SLS} deploy -v',
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
        '.venv': 'd',
        '.eggs': 'd',
        '.tox': 'd',
        '*.pyc': 'f',
        '.coverage': 'f',
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

def task_nuke():
    '''
    git clean and reset
    '''
    return {
        'task_dep': ['tidy'],
        'actions': [
            'docker-compose kill',
            'docker-compose rm -f',
            'git clean -fd',
            'git reset --hard HEAD',
        ],
    }

def task_prune():
    '''
    prune stopped containers
    '''
    return {
        'actions': ['docker rm `docker ps -q -f "status=exited"`'],
        'uptodate': ['[ -n "`docker ps -q -f status=exited`" ] && exit 1 || exit 0']
    }

if __name__ == '__main__':
    print('should be run with doit installed')
    import doit
    doit.run(globals())
