from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from enum import Enum


class LogLevelEnum(str, Enum):
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"


@dataclass(slots=True)
class LoggerSettings:
    log_level: LogLevelEnum = LogLevelEnum.DEBUG


def build_root_logger(log_settings: LoggerSettings | None = None) -> logging.Logger:
    settings = log_settings or LoggerSettings()
    logger = logging.getLogger("restcodegen")
    logger.setLevel(settings.log_level.value)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(settings.log_level.value)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.propagate = False
    return logger


LOGGER = build_root_logger()


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
