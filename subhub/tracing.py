import time
import cProfile
from subhub.cfg import CFG

from functools import wraps

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
    def timer(*args, **kwargs):
        if not CFG.PROFILING_ENABLED:
            return function(*args, **kwargs)
        else:
            start = time.time()
            result = function(*args, **kwargs)
            end = time.time()
            print(function.__name__, "took", end - start, "time")
            return result

    return timer
