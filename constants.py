from enum import Enum
from typing import List


class Schema(str, Enum):
    HTTP = "http"
    HTTPS = "https"

    @classmethod
    def get_key_by_value(cls, value: str):
        for element in cls:
            if element == value:
                return element


class BodyType(str, Enum):
    TEXT = "text"
    BYTES = "bytes"
    AUTO = "auto"

    @classmethod
    def get_key_by_value(cls, value: str):
        for element in cls:
            if element == value:
                return element


class RequestMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    OPTIONS = "OPTIONS"
    HEAD = "HEAD"
    TRACE = "TRACE"
    CONNECT = "CONNECT"

    @classmethod
    def get_all_values(cls) -> List[str]:
        value = list()
        for method in cls:
            value.append(method)
        return value
