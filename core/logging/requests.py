import os
from datetime import datetime
import logging
import sys
from logging import Logger, FileHandler, Formatter, StreamHandler
from typing import Optional

import yaml
from magic import Magic
from starlette.requests import Request

from constants import BodyType
from core.base import request_params_to_dict, request_headers_to_dict, get_exception_error
from core.logging.config import LogLevel, AppLoggers
from model.config_file import (
    RequestLogConfig,
    RequestConfig,
    ResponseConfig,
    ServerConfig
)


logger = logging.getLogger(AppLoggers.APP_LOGGER)


class RequestDataFormatter:
    def do_format(self, message: dict) -> str:
        return yaml.safe_dump(message, sort_keys=False)


class RequestLogger:
    def __init__(self):
        self.__request_id = 0
        self.__console_logger = None
        self.__loggers = dict()

        self.log_config = RequestLogConfig()
        self.data_formatter = RequestDataFormatter()

    def _configure_file_logger(
        self,
        logger: Logger,
        file: str
    ) -> Logger:
        handler = FileHandler(file)
        handler.setFormatter(Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(str(LogLevel.DEBUG.value))
        return logger

    def _configure_console_logger(self, logger: Logger) -> Logger:
        handler = StreamHandler(sys.stdout)
        handler.setFormatter(Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(str(LogLevel.DEBUG.value))
        return logger

    def _create_body_file_name(self):
        identities = [
            datetime.now().isoformat(),
            str(self.__request_id)
        ]
        self.__request_id += 1
        return "_".join(identities)

    def _guess_mime_type(self, body: bytes) -> str:
        return Magic(mime=True).from_buffer(body)

    def _mime_type_to_body_type(self, media_type: str) -> BodyType:
        text_substrings = {
            "text/"
            "application/json",
            "application/x-empty",
            "application/x-www-form-urlencoded"
        }
        for substring in text_substrings:
            if substring in media_type:
                return BodyType.TEXT
        return BodyType.BYTES

    def _get_console_logger(self) -> Logger:
        if self.__console_logger is None:
            logger = logging.getLogger(
                type(self).__name__ + ".console." + str(hash(self))
            )
            self._configure_console_logger(logger)
            self.__console_logger = logger
        return self.__console_logger

    def _get_file_logger(self, file: str) -> Logger:
        if file in self.__loggers.keys():
            return self.__loggers[file]

        logger = logging.getLogger(
            type(self).__name__ + ".file." + file
        )
        logger = self._configure_file_logger(logger, file)
        self.__loggers[file] = logger
        return logger

    @property
    def log_config(self) -> RequestLogConfig:
        return self.__log_config

    @log_config.setter
    def log_config(self, log_config: RequestLogConfig):
        self.__log_config = log_config

    @property
    def data_formatter(self) -> RequestDataFormatter:
        return self.__data_formatter

    @data_formatter.setter
    def data_formatter(self, data_formatter: RequestDataFormatter):
        self.__data_formatter = data_formatter

    async def log_request(
            self,
            request: Request,
            request_config: Optional[RequestConfig],
            response_config: ResponseConfig,
            server_config: ServerConfig
    ):
        try:
            request_log_config = response_config.request_log_config
            log_file = self.log_config.log_file
            if request_log_config.log_file is not None:
                log_file = request_log_config.log_file
            log_console = self.log_config.log_console
            if request_log_config.log_console is not None:
                log_console = request_log_config.log_console
            if log_file or log_console:
                headers_enabled = self.log_config.headers_enabled
                if request_log_config.headers_enabled is not None:
                    headers_enabled = request_log_config.headers_enabled
                body_enabled = self.log_config.body_enabled
                if request_log_config.body_enabled is not None:
                    body_enabled = request_log_config.body_enabled
                message_value = dict()
                message_value["server"] = {
                    "url": server_config.schema.value + "://" +
                           server_config.host + ":" + str(server_config.port)
                }
                if server_config.alias is not None:
                    message_value["server"]["alias"] = server_config.alias
                message_value.update({
                    "method": request.method,
                    "mapping": request.scope.get("path"),
                    "parameters": request_params_to_dict(request)
                })
                if headers_enabled:
                    message_value["headers"] = request_headers_to_dict(
                        request
                    )
                if body_enabled:
                    body_bytes = await request.body()
                    body_as_file = self.log_config.body_as_file
                    if request_log_config.body_as_file is not None:
                        body_as_file = request_log_config.body_as_file
                    if body_as_file:
                        body_file_name = self._create_body_file_name()
                        base_folder = self.log_config.body_files_folder
                        if request_log_config.body_files_folder is not None:
                            base_folder = request_log_config.body_files_folder
                        if base_folder is None:
                            base_folder = os.getcwd()
                        message_value["body_file"] = \
                            base_folder + "/" + body_file_name
                        try:
                            with open(message_value["body_file"], "wb") as file:
                                file.write(body_bytes)
                        except IOError:
                            raise IOError(
                                f"Error writing request body to file"
                                f" '{message_value['body_file']}'"
                            )
                    else:
                        body_type = self.log_config.body_type
                        if request_log_config.body_type is not None:
                            body_type = request_log_config.body_type
                        if body_type is None or body_type == BodyType.AUTO:
                            headers = request_headers_to_dict(request)
                            media_type = headers.get("Content-Type") or \
                                headers.get("content-type") or \
                                self._guess_mime_type(body_bytes)
                            body_type = self._mime_type_to_body_type(
                                media_type
                            )
                        if body_type.TEXT:
                            encoding = self.log_config.body_encoding
                            if request_log_config.body_encoding is not None:
                                encoding = request_log_config.body_encoding
                            if encoding is None:
                                encoding = "utf-8"
                            message_value["body"] = body_bytes.decode(
                                encoding
                            )
                        else:
                            message_value["body"] = body_bytes.hex()
                message_str = self.data_formatter.do_format(
                    {datetime.now().isoformat(): message_value}
                )
                if log_file:
                    self._get_file_logger(log_file).info(message_str)
                if log_console:
                    self._get_console_logger().info(message_str)
        except Exception as e:
            logger.error(
                "Request logging error: " +
                get_exception_error(e)
            )
