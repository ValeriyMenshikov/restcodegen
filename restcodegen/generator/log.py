from __future__ import annotations

import sys
from enum import Enum
from typing import Optional

import loguru
from pydantic_settings import BaseSettings


class LogLevelEnum(str, Enum):
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"


class LoggerSettings(BaseSettings):
    log_json: bool = True
    log_level: LogLevelEnum = LogLevelEnum.DEBUG


def build_root_logger(log_settings: Optional[LoggerSettings] = None) -> loguru.Logger:
    log_settings_ = log_settings or LoggerSettings()
    loguru.logger.remove()
    if log_settings_.log_json:
        loguru.logger.add(
            sys.stdout,
            level=log_settings_.log_level.value,
            backtrace=False,
            diagnose=False,
            serialize=False,
        )
    else:
        loguru.logger.add(
            sys.stdout,
            level=log_settings_.log_level.value,
        )
    return loguru.logger


LOGGER = build_root_logger()


def get_logger(name: str) -> loguru.Logger:
    return loguru.logger.bind(logger_name=name)
