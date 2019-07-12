"""
Usage example:
    from subhub.log import get_logger
    log = get_logger()
    log.info('my_event', my_key1='val 1', my_key2=5, my_key3=[1, 2, 3], my_key4={'a': 1, 'b': 2})
List of metadata keys in each log message:
    event
    func
    level
    module
    lineno
    event_uuid
    timestamp_utc
Limitations: multithreading is supported but not multiprocessing.
"""

import os
import sys
import time
import uuid
import datetime
import inspect
import logging
import logging.config
import platform
import tempfile
import threading
import collections
import structlog

from subhub.cfg import CFG

IS_CONFIGURED = False
EVENT_UUID = str(uuid.uuid4())
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"()": logging.StreamHandler, "level": CFG.APP_LOG_LEVEL}},
    "loggers": {
        CFG.APP_PROJNAME: {
            "propagate": False,
            "handlers": ["console"],
            "level": "DEBUG",
        }
    },
}


def _event_uppercase(logger, method_name, event_dict):
    event_dict["event"] = event_dict["event"].upper()
    return event_dict


def _add_timestamp(logger, method_name, event_dict):
    dt_utc = datetime.datetime.fromtimestamp(time.time(), datetime.timezone.utc)
    event_dict["timestamp_utc"] = dt_utc.isoformat()
    return event_dict


def _add_caller_info(logger, method_name, event_dict):
    # Typically skipped funcs: _add_caller_info, _process_event, _proxy_to_logger, _proxy_to_logger
    frame = inspect.currentframe()
    while frame:
        frame = frame.f_back
        module = frame.f_globals["__name__"]
        if module.startswith("structlog."):
            continue
        event_dict["module"] = module
        event_dict["lineno"] = frame.f_lineno
        event_dict["func"] = frame.f_code.co_name
        return event_dict


def _add_log_level(logger, method_name, event_dict):
    event_dict["level"] = method_name.upper()
    return event_dict


def _add_event_uuid(logger, method_name, event_dict):
    event_dict["event_uuid"] = EVENT_UUID
    return event_dict


def _order_keys(logger, method_name, event_dict):
    return collections.OrderedDict(
        sorted(event_dict.items(), key=lambda item: (item[0] != "event", item))
    )


def _setup_once():

    structlog.configure_once(
        processors=[
            structlog.stdlib.filter_by_level,
            _add_caller_info,
            _add_log_level,
            _add_event_uuid,
            _event_uppercase,
            structlog.stdlib.PositionalArgumentsFormatter(True),
            _add_timestamp,
            _order_keys,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.config.dictConfig(LOGGING_CONFIG)
    logger = get_logger(__name__)
    logger.info(
        "logging initialized",
        APP_DEPENV=CFG.APP_DEPENV,
        APP_PROJNAME=CFG.APP_PROJNAME,
        APP_BRANCH=CFG.APP_BRANCH,
        APP_REVISION=CFG.APP_REVISION,
        APP_VERSION=CFG.APP_VERSION,
        APP_REMOTE_ORIGIN_URL=CFG.APP_REMOTE_ORIGIN_URL,
        APP_LOG_LEVEL=CFG.APP_LOG_LEVEL,
    )


def get_logger(logger_name=None):
    global IS_CONFIGURED
    if not IS_CONFIGURED:
        IS_CONFIGURED = True
        _setup_once()
    if logger_name is None:
        logger_name = inspect.currentframe().f_back.f_globals["__name__"]
    logger_name = CFG.APP_PROJNAME if logger_name == "__main__" else logger_name
    return structlog.wrap_logger(logging.getLogger(logger_name))


if __name__ == "__main__":
    logger = get_logger()
    logger.debug("test")
