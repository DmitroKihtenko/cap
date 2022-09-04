import logging
from multiprocessing import Process

import uvicorn
from starlette.applications import Starlette

from typing import List

from constants import Schema
from core.base import get_exception_error
from core.logging.config import UvicornLogConfigAdapter, AppLoggers
from model.config_file import ServerConfig, SslConfig

logger = logging.getLogger(str(AppLoggers.APP_LOGGER.value))


class ServerProcess(Process):
    def __init__(
            self, application: Starlette,
            server_config: ServerConfig,
            logger_adapter: UvicornLogConfigAdapter,
            **kwargs
    ):
        self.application = application
        self.server = server_config
        self.logger_adapter = logger_adapter
        super().__init__(**kwargs, target=self._process_function)

    def _ssl_config_to_uvicorn_config(self, config: SslConfig) -> dict:
        return {
            "ssl_keyfile": config.keyfile,
            "ssl_certfile": config.certfile,
            "ssl_keyfile_password": config.keyfile_password,
            "ssl_ca_certs": config.ca_certs,
        }

    @property
    def _process_function(self) -> callable:
        def run():
            application = self.application
            server_config = self.server
            ssl_config = dict()
            if server_config.schema == Schema.HTTPS:
                ssl_config = self._ssl_config_to_uvicorn_config(
                    server_config.ssl_config
                )
            try:
                uvicorn.run(
                    application,
                    host=server_config.host,
                    port=server_config.port,
                    date_header=False,
                    proxy_headers=False,
                    server_header=False,
                    log_config=self.logger_adapter.uvicorn_config,
                    **ssl_config
                )
            except IOError as e:
                logger.error(
                    f"Server '{self.server.base_url}' "
                    "starting error: File reading error"
                )
            except Exception as e:
                logger.error(
                    f"Server '{self.server.base_url}' "
                    "starting error: " + get_exception_error(e)
                )
        return run

    @property
    def application(self) -> Starlette:
        return self.__application

    @application.setter
    def application(self, application: Starlette):
        self.__application = application

    @property
    def server(self) -> ServerConfig:
        return self.__server_config

    @server.setter
    def server(self, server: ServerConfig):
        self.__server_config = server

    @property
    def logger_adapter(self) -> UvicornLogConfigAdapter:
        return self.__logger_adapter

    @logger_adapter.setter
    def logger_adapter(self, logger_adapter: UvicornLogConfigAdapter):
        self.__logger_adapter = logger_adapter


class ProcessesController:
    def __init__(self, processes: List[ServerProcess]):
        self.__is_running = False
        self.__processes = list()

        self.processes = processes

    @property
    def is_running(self) -> bool:
        value = any(process.is_alive() for process in self.processes)
        return value

    @property
    def processes(self):
        return self.__processes

    @processes.setter
    def processes(self, processes: List[ServerProcess]):
        if self.is_running:
            self.terminate_all()
        self.__processes = processes

    def start_all(self):
        for process in self.processes:
            process.start()

    def terminate_all(self):
        if self.is_running:

            logger.info("Stopping server processes...")

            for process in self.processes:
                if process.is_alive():
                    process.terminate()
