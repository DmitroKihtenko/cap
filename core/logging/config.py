import logging
import sys
from enum import Enum
from typing import List

from uvicorn.config import LOGGING_CONFIG


class LogLevel(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"


class AppLoggers(str, Enum):
    APP_LOGGER = "application"
    UVICORN = "uvicorn"
    UVICORN_ERROR = "uvicorn.error"
    UVICORN_ACCESS = "uvicorn.access"


class LoggerConfig:
    @property
    def logging_level(self) -> LogLevel:
        raise NotImplemented

    @logging_level.setter
    def logging_level(self, level: LogLevel):
        raise NotImplemented

    @property
    def log_format(self) -> str:
        raise NotImplemented

    @log_format.setter
    def log_format(self, log_format: str):
        raise NotImplemented

    @property
    def log_files(self) -> List[str]:
        raise NotImplemented

    @log_files.setter
    def log_files(self, files: List[str]):
        raise NotImplemented


class UvicornLogConfigAdapter(LoggerConfig):
    __default_handlers_keys = {"default", "access"}

    def _modify_uvicorn_config(self, config: dict):
        handlers = config.get("handlers")
        if handlers is not None:
            for handler in handlers.keys():
                handlers[handler]["stream"] = "ext://sys.stdout"

    def __init__(self, uvicorn_log_config: dict = LOGGING_CONFIG):
        self.__uvicorn_config = dict(uvicorn_log_config)
        self._modify_uvicorn_config(self.__uvicorn_config)

        self.logging_level = LogLevel.DEBUG
        self.log_format = "[%(asctime)s: %(levelname)s] %(message)s"
        self.log_files = list()

    @property
    def uvicorn_config(self) -> dict:
        return self.__uvicorn_config

    @property
    def logging_level(self) -> LogLevel:
        return self.__logging_level

    @logging_level.setter
    def logging_level(self, level: LogLevel):
        self.__logging_level = level

        if self.uvicorn_config.get("loggers") is not None:
            loggers = self.uvicorn_config["loggers"]
            for logger in loggers.keys():
                loggers[logger]["level"] = self.logging_level.value

    @property
    def log_format(self) -> str:
        return self.__log_format

    @log_format.setter
    def log_format(self, log_format: str):
        self.__log_format = log_format

        if self.uvicorn_config.get("formatters") is not None:
            formatters = self.uvicorn_config["formatters"]
            for formatter in formatters.keys():
                formatters[formatter]["fmt"] = self.log_format

    @property
    def log_files(self) -> List[str]:
        return self.__log_files

    @log_files.setter
    def log_files(self, files: List[str]):
        self.__log_files = files

        if self.uvicorn_config.get("handlers") is not None:
            handlers = self.uvicorn_config["handlers"]
            for handler in handlers.keys():
                if handler not in self.__default_handlers_keys:
                    handlers.pop(handler)
        if self.uvicorn_config.get("loggers") is not None:
            loggers = self.uvicorn_config["loggers"]
            for logger in loggers.keys():
                handlers = loggers[logger].get("handlers")
                if handlers is not None:
                    for handler in handlers:
                        if handler not in self.__default_handlers_keys:
                            handlers.pop(handler)

        if self.uvicorn_config.get("handlers") is not None:
            for file in self.log_files:
                self.uvicorn_config["handlers"][file] = {
                    "formatter": "default",
                    "class": "logging.FileHandler",
                    "filename": file,
                }
        if self.uvicorn_config.get("loggers") is not None:
            loggers = self.uvicorn_config["loggers"]
            for logger in loggers.keys():
                for file in self.log_files:
                    if loggers[logger].get("handlers") is not None:
                        loggers[logger]["handlers"].append(file)


class AppLoggerConfig(LoggerConfig):
    def __init__(self, logger_name: str):
        self.__logger_name = logger_name

        self.__log_handlers = dict()
        self.__log_formatter = None
        self.__stdout_handler = logging.StreamHandler(
            stream=sys.stdout
        )

        self.logging_level = LogLevel.DEBUG
        self.log_format = "[%(asctime)s: %(levelname)s] %(message)s"
        self.log_files = list()

    def init_logging(self):
        self.de_init_logging()
        self.app_logger.addHandler(self.__stdout_handler)
        for file in self.__log_handlers.keys():
            self.app_logger.addHandler(self.__log_handlers[file])
        self.app_logger.setLevel(self.__logging_level.value)

    def de_init_logging(self):
        self.app_logger.removeHandler(self.__stdout_handler)
        for file in self.__log_handlers.keys():
            self.app_logger.removeHandler(self.__log_handlers[file])

    @property
    def logger_name(self) -> str:
        return self.__logger_name

    @property
    def logging_level(self) -> LogLevel:
        return self.__logging_level

    @logging_level.setter
    def logging_level(self, level: LogLevel):
        self.__logging_level = level
        self.app_logger.setLevel(str(level.value))

    @property
    def log_format(self) -> str:
        return self.__log_format

    @log_format.setter
    def log_format(self, log_format: str):
        self.__log_format = log_format
        formatter = self._log_formatter
        self.__stdout_handler.setFormatter(formatter)
        for handler in self.app_logger.handlers:
            handler.setFormatter(formatter)

    @property
    def log_files(self) -> List[str]:
        return list(self.__log_handlers.keys())

    @log_files.setter
    def log_files(self, files: List[str]):
        for file in self.__log_handlers.keys():
            self.app_logger.removeHandler(self.__log_handlers[file])
        self.__log_handlers.clear()
        for file in files:
            handler = logging.FileHandler(file)
            handler.setFormatter(self._log_formatter)
            self.__log_handlers[file] = handler
        for handler in self.__log_handlers.values():
            self.app_logger.addHandler(handler)

    @property
    def _log_formatter(self) -> logging.Formatter:
        if self.__log_formatter is None:
            self.__log_formatter = logging.Formatter(self.__log_format)
        return self.__log_formatter

    @property
    def app_logger(self) -> logging.Logger:
        return logging.getLogger(self.logger_name)
