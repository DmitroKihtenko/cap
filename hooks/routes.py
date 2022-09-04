import typing

from starlette.routing import Route, Match
from starlette.types import Scope


class AllMappingRoute(Route):
    def matches(self, scope: Scope) -> typing.Tuple[Match, Scope]:
        return Match.FULL, {"endpoint": scope["path"], "path_params": {}}
