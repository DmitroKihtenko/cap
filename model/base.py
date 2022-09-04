from pydantic import ValidationError
from pydantic.error_wrappers import ErrorWrapper
from pydantic.errors import PydanticErrorMixin

from core.base import get_exception_error


def get_validation_error_message(error: ValidationError) -> str:
    if len(error.raw_errors) == 0:
        return "Unknown validation error"
    else:
        wrappers_list = error.raw_errors[0]
        if isinstance(wrappers_list, list):
            if len(wrappers_list) == 0:
                return "Unknown validation error"
            else:
                wrapper: ErrorWrapper = wrappers_list[0]
        elif isinstance(wrappers_list, str):
            return "Validation error: " + wrappers_list
        else:
            wrapper = wrappers_list
        raw_error = wrapper.exc
        if isinstance(raw_error, ValidationError):
            return get_validation_error_message(raw_error)
        elif isinstance(raw_error, str):
            return raw_error
        elif isinstance(raw_error, PydanticErrorMixin):
            fields = wrapper.loc_tuple()
            return "Validation error at fields: " +\
                   ", ".join(fields) +\
                   ". Message: " + str(raw_error)
        else:
            return "Validation error: " +\
                   get_exception_error(raw_error)
