#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
#from cfg import CFG #FIXME: this causes import errors

with open("README.md", "r") as fh:
    long_description = fh.read()

requirements = [
    'attrdict',
    'aws-wsgi',
    'boto3',
    'botocore',
    'certifi',
    'chardet',
    'colorama',
    'connexion',
    'connexion[swagger-ui]',
    'docutils',
    'Flask',
    'Flask-Cors',
    'idna',
    'inflection',
    'itsdangerous',
    'Jinja2',
    'jmespath',
    'jsonschema==2.5.1',
    'MarkupSafe',
    'newrelic',
    'openapi-spec-validator==0.2.7',
    'pathlib',
    'psutil',
    'pynamodb',
    'python-dateutil',
    'python-decouple',
    'python-json-logger',
    'PyYAML==5.1.1',
    'requests',
    's3transfer',
    'six',
    'stripe',
    'structlog',
    'urllib3',
]

setup_requirements = [
    'pytest-runner',
    'setuptools>=40.5.0',
]

test_requirements = [
    'mockito',
    'pytest',
    'pytest-cov',
    'pytest-mock',
    'flake8',
    'mock',
    'mockito',
    'mockito',
    'patch',
    'pytest',
    'pytest',
    'pytest-cov',
    'pytest-cov',
    'pytest-mock',
    'pytest-mock',
    'pytest-watch',
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
    install_requires=requirements,
    license='Mozilla Public License 2.0',
    include_package_data=True,
    packages=find_packages(include=['subhub']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    extras_require=extras,
    zip_safe=False,
)
