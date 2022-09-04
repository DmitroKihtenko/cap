import typing

from starlette.responses import Response


class RawResponse(Response):
    def init_headers(
        self, headers: typing.Optional[typing.Mapping[str, str]] = None
    ) -> None:
        content_length = len(self.body)
        if headers is None:
            headers = dict()
        headers["content-length"] = str(content_length)
        raw_headers = [
            (k.lower().encode("latin-1"), v.encode("latin-1"))
            for k, v in headers.items()
        ]
        self.raw_headers = raw_headers
