#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import functools

from subhub.tracing import timed, mprofiled
from random import randint, randrange


@timed
def generate_random_value():
    return randint(0, 9)


@timed
def generate_wrapped_random_value():
    return __wrapped(randint(0, 9))


@timed
def __wrapped(functor):
    @functools.wraps(functor)
    def call(*args, **kwargs):
        return functor(*args, **kwargs)

    return call


@mprofiled
def generate_random_list():
    return [randrange(1, 101, 1) for _ in range(10)]


def test_timed():
    assert type(generate_random_value()) is int


def test_timed_wrapped():
    assert type(generate_wrapped_random_value()) is int


def test_mprofile():
    collection = generate_random_list()
    assert isinstance(collection, list)
    assert isinstance(collection[0], int)
