from functools import lru_cache
from logging import Logger
from re import Pattern
from typing import Dict, Optional, Union, List, Set

import re

from pydantic import BaseModel, Field, validator, ValidationError

from constants import RequestMethod, Schema, BodyType
from core.base import get_exception_error
from core.logging.config import AppLoggers
from model.base import get_validation_error_message


logger = Logger(str(AppLoggers.APP_LOGGER.value))


@lru_cache
def get_base_url_pattern() -> Pattern:
    return re.compile(
        "^((\\w+)://)?([\\w.]+)(:(\\d{1,5}))?((/\\w+)*)$"
    )


def check_base_url(url: str) -> str:
    match = get_base_url_pattern().match(url)
    if match is None:
        raise ValueError(f"Invalid server base url: '{url}'")
    raw_schema = get_base_url_pattern().match(url).group(2)
    if raw_schema is not None:
        schema = Schema.get_key_by_value(raw_schema.lower())
        if schema is None:
            raise ValueError(
                f"Invalid schema value '{raw_schema}'."
                f" Allowed values: '" + "', '".join(Schema) + "'"
            )
    raw_port = match.group(5)
    if raw_port is None:
        return url
    port = int(raw_port)
    if not 0 <= port <= 65535:
        raise ValueError(f"Port value '{raw_port}' is not from range 0-65535")
    return url


def check_encoding(encoding: str) -> str:
    try:
        "".encode(encoding)
        return encoding
    except:
        raise ValueError(f"Unknown encoding type '{encoding}'")


class HttpBody(BaseModel):
    file: Optional[str] = Field(
        None,
        description="HTTP body filename"
    )
    data: Union[str, bytes] = Field(
        b"",
        description="Http body data"
    )
    data_encoding: Optional[str] = Field(
        "utf-8",
        description="Http body data encoding"
    )

    @property
    def bytes(self):
        try:
            if self.file is not None:
                with open(self.file, "rb") as file:
                    return file.read()
            else:
                if isinstance(self.data, str):
                    return self.data.encode(self.data_encoding)
                else:
                    return self.data
        except:
            logger.error(f"Body file '{self.file}' reading error."
                         f"Empty body will be used")
            return b""


class HttpBase(BaseModel):
    headers: Dict[str, str] = Field(
        dict(),
        description="Headers map"
    )
    body: HttpBody = Field(
        HttpBody(),
        description="Http body data"
    )


class RequestLogConfig(BaseModel):
    headers_enabled: Optional[bool] = Field(
        None,
        description="Log request headers"
    )
    body_enabled: Optional[bool] = Field(
        None,
        description="Log request body"
    )
    body_as_file: Optional[bool] = Field(
        None,
        description="Log request body in a separate file"
    )
    body_files_folder: Optional[str] = Field(
        None,
        description="Requests content files base folder"
    )
    body_type: Optional[BodyType] = Field(
        None,
        description="Body representation type"
    )
    body_encoding: Optional[str] = Field(
        None,
        description="Encoding for text body representation"
    )
    log_file: Optional[str] = Field(
        None,
        description="Log request file"
    )
    log_console: Optional[bool] = Field(
        None,
        description="Log to console"
    )

    _body_encoding_validator = validator(
        "body_encoding",
        allow_reuse=True
    )(check_encoding)


class RequestConfig(BaseModel):
    mapping: str = Field(
        "/",
        description="Request mapping"
    )
    method: RequestMethod = Field(
        RequestMethod.GET,
        description="Request method"
    )
    parameters: Optional[Dict[str, str]] = Field(
        None,
        description="Request parameters"
    )
    body: Optional[HttpBody] = Field(
        None,
        description="Http body data"
    )
    response_id: str = Field(
        "default",
        description="Request response id"
    )


class ResponseConfig(BaseModel):
    headers: Dict[str, str] = Field(
        dict(),
        description="Headers map"
    )
    body: HttpBody = Field(
        HttpBody(),
        description="Http body data"
    )
    status: int = Field(
        200,
        description="Status",
        le=599,
        ge=100
    )
    seconds_delay: Optional[float] = Field(
        None,
        description="Request response id"
    )
    request_log_config: RequestLogConfig = Field(
        RequestLogConfig(),
        description="Request log config"
    )


class SslConfig(BaseModel):
    keyfile: Optional[str] = Field(
        None,
        description="SSL key file path"
    )
    certfile: Optional[str] = Field(
        None,
        description="SSL certificate file path"
    )
    keyfile_password: Optional[str] = Field(
        None,
        description="SSL key file password"
    )
    ca_certs: Optional[str] = Field(
        None,
        description="SSL ca certificate file"
    )

    def validate_config(self):
        if self.certfile is None and self.ca_certs is None:
            raise ValueError(
                "At least one certificate file must "
                "be specified in SSL configuration"
            )


class ServerConfig(BaseModel):
    alias: Optional[str] = Field(
        None,
        description="Server alias"
    )
    base_url: str = Field(
        "http://0.0.0.0:80/api",
        description="Base server URL"
    )
    requests_ids: Set[str] = Field(
        set(),
        description="Server requests ids"
    )
    default_response_id: str = Field(
        "default",
        description="Server default request id"
    )
    ssl_config: Optional[SslConfig] = Field(
        None,
        description="Server SSL configurations for HTTPS protocol"
    )

    @property
    def host(self) -> str:
        return get_base_url_pattern().match(self.base_url).group(3)

    @property
    def port(self) -> int:
        raw_port = get_base_url_pattern().match(self.base_url).group(5)
        if raw_port is None:
            return 80
        return int(raw_port)

    @property
    def schema(self) -> Schema:
        raw_schema = get_base_url_pattern().match(self.base_url).group(2)
        if raw_schema is None:
            return Schema.HTTP
        return Schema.get_key_by_value(raw_schema.lower())

    @property
    def base_mapping(self) -> str:
        mapping = get_base_url_pattern().match(self.base_url).group(6)
        if mapping is None:
            return ""
        return mapping

    @property
    def identity(self) -> str:
        match = get_base_url_pattern().match(self.base_url)
        return match.group(3) + match.group(4) + match.group(6)

    def validate_protocol_configured(self):
        if self.schema == Schema.HTTPS and self.ssl_config is None:
            raise ValueError(
                f"Required SSL configuration for schema "
                f"'{Schema.HTTPS.value}' for server '{self.base_url}'"
            )
        elif self.ssl_config is not None:
            self.ssl_config.validate_config()

    _base_url_validator = validator(
        "base_url",
        allow_reuse=True
    )(check_base_url)


class DefaultRequestLogConfig(RequestLogConfig):
    headers_enabled = True
    body_enabled = True
    body_as_file = False
    body_type = BodyType.AUTO
    body_encoding = "utf-8"
    log_console = True


class Config(BaseModel):
    servers: List[ServerConfig] = Field(
        [ServerConfig()],
        description="Servers list",
        min_items=1
    )
    requests: Dict[str, RequestConfig] = Field(
        dict(),
        description="Requests list"
    )
    responses: Dict[str, ResponseConfig] = Field(
        {"default": ResponseConfig()},
        description="Responses list",
    )
    request_log_config: RequestLogConfig = Field(
        DefaultRequestLogConfig(),
        description="Global request logging config"
    )

    def validate_request_response_ids(self):
        servers_configs = self.servers
        requests_configs = self.requests
        responses_configs = self.responses

        server_requests = set()
        responses = set()
        request_responses = set()
        requests = set()
        for server in servers_configs:
            for request_id in server.requests_ids:
                server_requests.add(request_id)
            request_responses.add(server.default_response_id)
        requests.update(set(requests_configs.keys()))
        for request in requests_configs.values():
            request_responses.add(request.response_id)
        responses.update(set(responses_configs.keys()))

        not_described_requests = server_requests.difference(requests)
        if len(not_described_requests) != 0:
            raise ValueError(
                "Not described requests: " +
                ", ".join(not_described_requests)
            )

        not_described_responses = request_responses.difference(responses)
        if len(not_described_responses) != 0:
            raise ValueError(
                "Not described responses: " +
                ", ".join(not_described_responses)
            )

    def validate(self):
        for server_config in self.servers:
            server_config.validate_protocol_configured()
        self.validate_request_response_ids()


def parse_config(raw_config: dict) -> Config:
    try:
        config = Config.parse_obj(raw_config)
        config.validate()
        return config
    except ValidationError as e:
        raise IOError(
            "Config file parsing error: " +
            get_validation_error_message(e)
        )
    except ValueError as e:
        raise IOError(
            "Config file parsing error: " +
            get_exception_error(e)
        )
