from typing import List

from core.logging.requests import RequestLogger


def request_logging(loggers: List[RequestLogger]):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            for logger in loggers:
                await logger.log_request(*args, **kwargs)
            return await func(*args, **kwargs)
        return wrapper
    return decorator
