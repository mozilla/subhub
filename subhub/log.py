import logging.handlers
from pythonjsonlogger import jsonlogger
import datetime


def setup(logger, level=loggin.INFO):
    for handler in logger.handlers:
        logger.removeHandler(handler)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(extra=dict(hostname=socket.gethostname())))
    logger.addHandler(handler)
    logger.setLevel(level)
    return logger


FMT = "%(asctime) %(name) %(processName) %(filename) %(funcName) %(levelname) %(lineno) %(module) %(threadName) %(message)"


class JsonFormatter(jsonlogger.JsonFormatter, object):
    def __init__(
        self,
        fmt=FMT,
        datefmt="%Y-%m-%dT%H:%M:%SZ%z",
        style="%",
        extra={},
        *args,
        **kwargs
    ):
        self._extra = extra
        jsonlogger.JsonFormatter.__init__(
            self, fmt=fmt, datefmt=datefmt, *args, **kwargs
        )

    def process_log_record(self, log_record):
        if "asctime" in log_record:
            log_record["timestamp"] = log_record["asctime"]
        else:
            log_record["timestamp"] = datetime.datetime.utcnow().strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ%z"
            )

        if self._extra is not None:
            for key, value in self._extra.items():
                log_record[key] = value
        return super(JsonFormatter, self).process_log_record(log_record)


class SysLogJsonHandler(logging.handlers.SysLogHandler, object):
    def __init__(
        self,
        address=("localhost", logging.handlers.SYSLOG_UDP_PORT),
        facility=logging.handlers.SysLogHandler.LOG_USER,
        socktype=None,
        prefix="",
    ):
        super(SysLogJsonHandler, self).__init__(address, facility, socktype)
        self._prefix = prefix
        if self._prefix != "":
            self._prefix = prefix + ": "

    def format(self, record):
        return self._prefix + super(SysLogJsonHandler, self).format(record)
