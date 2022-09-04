from starlette.requests import Request


def get_exception_error(exception: Exception) -> str:
    filtered_args = list()

    for argument in exception.args:
        if argument is not None:
            filtered_args.append(str(argument))
    return ". ".join(filtered_args)


def request_params_to_dict(request: Request) -> dict:
    request_params = dict()
    for k, v in request.query_params.items():
        request_params[k] = v
    return request_params


def request_headers_to_dict(request: Request) -> dict:
    request_headers = dict()
    for k, v in request.headers.items():
        request_headers[k] = v
    return request_headers
