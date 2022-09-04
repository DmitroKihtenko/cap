import asyncio
import logging
from typing import Dict, List, Optional

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

from constants import RequestMethod
from core.base import request_params_to_dict
from core.logging.config import AppLoggers
from core.logging.requests import RequestLogger
from core.logging.config import UvicornLogConfigAdapter
from core.server_processing import ServerProcess
from hooks.routes import AllMappingRoute
from core.decorators import request_logging
from hooks.responses import RawResponse
from model.config_file import (
    RequestConfig,
    ServerConfig,
    ResponseConfig,
    Config
)


logger = logging.getLogger(str(AppLoggers.APP_LOGGER.value))


def is_request_fit(
        request: Request,
        request_config: RequestConfig,
        server_config: ServerConfig
) -> bool:
    if request.method != request_config.method.value:
        return False
    if request.scope.get("path") != server_config.base_mapping\
            + request_config.mapping:
        return False
    if request_config.parameters is not None:
        if request_config.parameters != request_params_to_dict(request):
            return False
    if request_config.body is not None and request.body() !=\
            request_config.body.bytes:
        return False
    return True


def get_request_allocation_function(
        server_requests: List[RequestConfig],
        server_config: ServerConfig,
        responses: Dict[str, ResponseConfig],
        loggers: List[RequestLogger]
) -> callable:

    async def request_processor(request: Request):
        for request_config in server_requests:
            if is_request_fit(request, request_config, server_config):
                return await get_request_function(loggers)(
                    request,
                    request_config,
                    responses[request_config.response_id],
                    server_config
                )
        raise HTTPException(
            400,
            "Unknown request. Will be"
            " allocated to default response"
        )
    return request_processor


def get_request_function(
        loggers: List[RequestLogger]
) -> callable:

    @request_logging(loggers)
    async def request_response_function(
            request: Request,
            request_config: Optional[RequestConfig],
            response_config: ResponseConfig,
            server_config: ServerConfig
    ) -> Response:
        if response_config.seconds_delay is not None:
            await asyncio.sleep(response_config.seconds_delay)
        return RawResponse(
            response_config.body.bytes,
            status_code=response_config.status,
            headers=response_config.headers
        )

    return request_response_function


def get_exception_handler_function(
        loggers: List[RequestLogger],
        response_config: ResponseConfig,
        server_config: ServerConfig
) -> callable:

    async def exception_handler(request: Request, exc: HTTPException):
        logger.warning(
            f"Request '{request.scope.get('path')}' error. "
            + str(exc.detail)
        )
        return await get_request_function(loggers)(
            request, None, response_config, server_config
        )

    return exception_handler


def create_server_routes(
        config: Config,
        loggers: List[RequestLogger]
) -> Dict[str, Route]:
    server_routes = dict()

    servers_requests = dict()
    for server_config in config.servers:
        identity = server_config.identity
        servers_requests[identity] = list()
        for request_id in server_config.requests_ids:
            servers_requests[identity].append(
                config.requests[request_id]
            )

    for server_config in config.servers:
        identity = server_config.identity
        server_requests = servers_requests[identity]

        server_routes[identity] = AllMappingRoute(
            "/",
            endpoint=get_request_allocation_function(
                server_requests,
                server_config,
                config.responses,
                loggers
            ),
            methods=RequestMethod.get_all_values()
        )

    return server_routes


def create_routes(
        config: Config,
        endpoints: Dict[str, callable]
) -> Dict[str, Route]:
    routes = dict()
    for request_id in config.requests.keys():
        request = config.requests[request_id]
        routes[request_id] = Route(
            request.mapping,
            endpoint=endpoints[request.response_id],
            methods=[request.method.value]
        )
    return routes


def create_processes(
        config: Config,
        endpoints: Dict[str, Route],
        log_adapter: UvicornLogConfigAdapter,
        loggers: List[RequestLogger]
) -> List[ServerProcess]:
    processes = list()

    for server in config.servers:
        identity = server.identity
        default_response = config.responses[server.default_response_id]

        app = Starlette(
            routes=[endpoints[identity]],
            exception_handlers={
                HTTPException: get_exception_handler_function(
                    loggers, default_response, server
                )
            }
        )
        processes.append(ServerProcess(app, server, log_adapter))
    return processes


def get_server_processes(
        config: Config,
        loggers: List[RequestLogger],
        log_adapter: UvicornLogConfigAdapter
) -> List[ServerProcess]:
    return create_processes(
        config,
        create_server_routes(config, loggers),
        log_adapter,
        loggers
    )
