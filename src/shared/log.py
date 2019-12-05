# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging.config

from shared.cfg import CFG
from typing import Any

LOGGER = None
CENSORED_EVENT_VALUES_BY_EVENT_KEY = {
    "headers": ["Authorization", "X-Forwarded-For"],
    "multiValueHeaders": ["Authorization"],
}

dict_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": "%(message)s %(lineno)d %(pathname)s %(levelname)-8s %(threadName)s",
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
        }
    },
    "handlers": {"json": {"class": "logging.StreamHandler", "formatter": "json"}},
    "loggers": {
        "": {"handlers": ["json"], "level": CFG.LOG_LEVEL},
        "werkzeug": {"level": "ERROR", "handlers": ["json"], "propagate": False},
        "pytest": {"level": "ERROR", "handlers": ["json"], "propagate": False},
        "pynamodb": {"level": "ERROR", "handlers": ["json"], "propagate": False},
        "botocore": {"level": "ERROR", "handlers": ["json"], "propagate": False},
        "urllib3": {"level": "ERROR", "handlers": ["json"], "propagate": False},
        "connexion": {"level": "ERROR", "handlers": ["json"], "propagate": False},
        "connexion.decorators.validation": {
            "level": CFG.LOG_LEVEL,
            "handlers": ["json"],
            "propagate": False,
        },
        "openapi_spec_validator": {
            "level": CFG.LOG_LEVEL,
            "handlers": ["json"],
            "propagate": False,
        },
    },
}


def event_uppercase(logger, method_name, event_dict):
    event_dict["event"] = event_dict["event"].upper()
    return event_dict


def censor_event_dict(event_dict):
    for k, v in event_dict.items():
        if isinstance(v, dict):
            censor_event_dict(v)
        else:
            for event_key, event_values in CENSORED_EVENT_VALUES_BY_EVENT_KEY.items():
                if event_dict is not None:
                    _event_key = event_dict.get(event_key)
                    if _event_key:
                        for event_value in event_values:
                            _event_value = _event_key.get(event_value)
                            if _event_key:
                                event_dict[event_key][event_value] = "*CENSORED*"
            return event_dict


def censor_header(logger, method_name, event_dict):
    return censor_event_dict(event_dict)


def get_logger() -> Any:
    global LOGGER
    if not LOGGER:
        from structlog import configure, processors, stdlib, threadlocal, get_logger
        from pythonjsonlogger import jsonlogger

        logging.config.dictConfig(dict_config)

        configure(
            context_class=threadlocal.wrap_dict(dict),
            logger_factory=stdlib.LoggerFactory(),
            wrapper_class=stdlib.BoundLogger,
            processors=[
                # Filter only the required log levels into the log output
                stdlib.filter_by_level,
                # Adds logger=module_name (e.g __main__)
                stdlib.add_logger_name,
                # Uppercase structlog's event name which shouldn't be convoluted with AWS events.
                event_uppercase,
                # Censor secure data
                censor_header,
                # Allow for string interpolation
                stdlib.PositionalArgumentsFormatter(),
                # Render timestamps to ISO 8601
                processors.TimeStamper(fmt="iso"),
                # Include the stack dump when stack_info=True
                processors.StackInfoRenderer(),
                # Include the application exception when exc_info=True
                # e.g log.exception() or log.warning(exc_info=True)'s behavior
                processors.format_exc_info,
                # Decodes the unicode values in any kv pairs
                processors.UnicodeDecoder(),
                # Creates the necessary args, kwargs for log()
                stdlib.render_to_log_kwargs,
            ],
            cache_logger_on_first_use=True,
        )
        LOGGER = get_logger()
    return LOGGER
