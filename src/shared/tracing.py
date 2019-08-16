# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Memory Profile a function
Requires the environment variable, PYTHONTRACEMALLOC to be set prior
or you will get the following run-tine exception:
    `the tracemalloc module must be tracing memory allocations to take a snapshot`

Calling syntax:
    @mprofiled
    def some_function():
        pass
"""

import functools
import time
import cProfile

from functools import wraps

from shared.cfg import CFG


def mprofiled(func):
    import tracemalloc
    import os

    def profiled(*args, **kwargs):
        if not CFG.PROFILING_ENABLED:
            return func(*args, **kwargs)
        else:
            if "PYTHONTRACEMALLOC" not in os.environ:
                os.environ["PYTHONTRACEMALLOC"] = "1"
            tracemalloc.start()
            memory_before = tracemalloc.take_snapshot()
            result = func(*args, **kwargs)
            memory_after = tracemalloc.take_snapshot()
            top_stats = memory_after.compare_to(memory_before, "lineno")
            for stat in top_stats[:10]:
                print(stat)
            tracemalloc.stop()
            return result

    return profiled


"""
cProfile of a provided function.
Calling syntax:
    @cprofiled
    def some_function():
        pass
"""


def cprofiled(func):
    def profiled(*args, **kwargs):
        if not CFG.PROFILING_ENABLED:
            return func(*args, **kwargs)
        else:
            profile = cProfile.Profile()
            try:
                profile.enable()
                result = func(*args, **kwargs)
                profile.disable()
                return result
            finally:
                profile.print_stats()

    return profiled


"""
Elapsed timing of a provided function.
Calling syntax;
    @timed
    def some_function():
        passs
"""


def timed(function):
    from inspect import isfunction

    def timer(*args, **kwargs):
        if not CFG.PROFILING_ENABLED:
            result = function(*args, **kwargs)
            if isfunction(result):
                return result.__wrapped__
            else:
                return result
        else:
            start = time.time()
            result = function(*args, **kwargs)
            if isfunction(result):
                result = result.__wrapped__
            end = time.time()
            print(function.__name__, "took", end - start, "time")
            return result

    return timer
