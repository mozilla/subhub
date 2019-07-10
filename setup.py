#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
#from cfg import CFG #FIXME: this causes import errors

with open("README.md", "r") as fh:
    long_description = fh.read()

with open('subhub/requirements.txt') as f:
    app_requirements = f.read().splitlines()

with open('subhub/tests/requirements.txt') as f:
    test_requirements = f.read().splitlines()

setup_requirements = [
    'pytest-runner',
    'setuptools>=40.5.0',
]

extras = {'test': test_requirements}

setup(
    name='subhub',
    #version=CFG.APP_VERSION, #FIXME: would be nice to have this
    version='v0.1',
    author='Scott Idler',
    author_email='sidler@mozilla.com',
    description='Flask application for facilitating Subscription Services',
    long_description=long_description,
    url='https://github.com/mozilla-it/subhub',
    classifiers=(
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: Mozilla Public License',
        'Operating System :: OS Independent',
    ),
    install_requires=app_requirements,
    license='Mozilla Public License 2.0',
    include_package_data=True,
    packages=find_packages(include=['subhub']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    extras_require=extras,
    zip_safe=False,
)
