import logging ,json ,sys


class JsonFormatter(logging.Formatter):
    RESERVED_ATTRS = {
        "args","msg","levelname","levelno","pathname","filename",
        "module","exc_info","exc_text","stack_info","lineno",
        "funcName","created","msecs","relativeCreated","thread",
        "threadName","processName","process","name"
    }

    def format(self, record):
        # basic log structure
        log_record = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "service": getattr(record, "service", "unknown"),
            "logger": record.name,
            "stage": getattr(record, "stage", "unknown"),
            "status": getattr(record, "status", "unknown"),
            "message": record.getMessage(),
        }

        # mange custom attributes (exclude reserved ones and empty values)
        for key, value in record.__dict__.items():
            if key not in log_record and key not in self.RESERVED_ATTRS:
                if value not in (None, "", []):
                    log_record[key] = value

        return json.dumps(log_record, ensure_ascii=False)


class ContextLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        extra = kwargs.get("extra", {})
        
        # merge context with log-specific extra (log-specific takes precedence)
        merged = {**self.extra, **extra}
        kwargs["extra"] = merged
        
        return msg, kwargs


def get_logger(
    service: str = "etl",
    logger_name: str = "etl_logger",
    stage: str = "local",
):

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    return ContextLoggerAdapter(
        logger,
        {
            "service": service,
            "stage": stage,
            "status": "ok",
        },
    )