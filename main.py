import logging
from argparse import ArgumentParser, Namespace

import yaml

from core.base import get_exception_error
from core.config_loader import ConfigFileLoader
from core.logging.config import AppLoggers, AppLoggerConfig, UvicornLogConfigAdapter, LogLevel, LoggerConfig
from core.logging.requests import RequestLogger
from core.process_middleware import get_server_processes
from core.server_processing import ProcessesController
from model.config_file import parse_config


logger = logging.getLogger(str(AppLoggers.APP_LOGGER.value))


def init_arguments() -> Namespace:
    arg_parser = ArgumentParser(
        prog="cap",
        description="HTTP server tool")
    arg_parser.add_argument(
        "-c",
        default="cap.yml",
        metavar="config",
        type=str,
        help="configuration yml file path")
    arg_parser.add_argument(
        "-l",
        default=LogLevel.DEBUG,
        metavar="level",
        type=LogLevel,
        help="logging level")
    arg_parser.add_argument(
        "-f",
        default="[%(asctime)s: %(levelname)s] %(message)s",
        metavar="format",
        type=str,
        help="logging format")
    arg_parser.add_argument(
        "-o",
        default=list(),
        metavar="output",
        type=str,
        action="append",
        help="logging output file")
    return arg_parser.parse_args()


def set_logger_config(arguments: Namespace, logger_config: LoggerConfig):
    logger_config.logging_level = arguments.l
    logger_config.log_format = arguments.f
    logger_config.log_files = arguments.o


def parse_from_yaml(value: bytes) -> dict:
    try:
        return yaml.safe_load(value)
    except Exception as e:
        raise IOError(
            "YAML parsing error: " + get_exception_error(e)
        )


def main():
    controller = None
    try:
        request_logger = RequestLogger()
        log_config = AppLoggerConfig(AppLoggers.APP_LOGGER)
        log_config.init_logging()
        uvicorn_log_adapter = UvicornLogConfigAdapter()

        args = init_arguments()
        set_logger_config(args, log_config)
        set_logger_config(args, uvicorn_log_adapter)

        config_loader = ConfigFileLoader(args.c)
        config = parse_config(
            parse_from_yaml(config_loader.get_file_value())
        )

        request_logger.log_config = config.request_log_config
        processes = get_server_processes(
            config, [request_logger], uvicorn_log_adapter
        )
        controller = ProcessesController(processes)

        controller.start_all()
        while controller.is_running:
            config_loader.do_load()
            if config_loader.is_changed:
                config_loader.reset_changed()

                logger.info(
                    "Config file changes detected. Applying..."
                )

                config = None
                try:
                    config = parse_config(
                        parse_from_yaml(config_loader.get_file_value())
                    )
                except IOError as e:
                    logger.warning(get_exception_error(e))
                if config_loader is not None:
                    controller.terminate_all()
                    while controller.is_running:
                        pass
                    request_logger.log_config = config.request_log_config
                    processes = get_server_processes(
                        config, [request_logger], uvicorn_log_adapter
                    )
                    controller.processes = processes

                    controller.start_all()
    except SystemExit:
        pass
    except KeyboardInterrupt:
        logger.critical("Interrupted")
    except Exception as e:
        logger.critical(get_exception_error(e))
    finally:
        if controller is not None:
            controller.terminate_all()


if __name__ == "__main__":
    main()
