"""Logging configuration and secret sanitization."""

import logging
import sys
import re


class SensitiveFilter(logging.Filter):
    """Filter that strips out sensitive tokens like Telegram Bot tokens."""

    TOKEN_PATTERN = re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b")

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.TOKEN_PATTERN.sub("[REDACTED_TELEGRAM_TOKEN]", record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: (self.TOKEN_PATTERN.sub("[REDACTED_TELEGRAM_TOKEN]", str(v)) if isinstance(v, str) else v)
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    (self.TOKEN_PATTERN.sub("[REDACTED_TELEGRAM_TOKEN]", str(v)) if isinstance(v, str) else v)
                    for v in record.args
                )
        return True


def setup_logging(log_level: str = "INFO") -> None:
    """Configures structured logging with standard formatting."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)
    console_handler.addFilter(SensitiveFilter())

    root_logger.addHandler(console_handler)

    # Silence overly verbose external loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.INFO)
