"""Howdy fellow developer!

We are glad you are taking a look at our code :-)
Make sure to check out our documentation too:
http://roll.readthedocs.io/en/latest/

If you do not understand why something is not working as expected,
please submit an issue (or even better a pull-request with at least
a test failing): https://github.com/pyrates/roll/issues/new
"""

import inspect
import re
from collections import defaultdict, namedtuple
from http import HTTPStatus
from typing import Callable

from autoroutes import Routes

from .http import Cookies, Files, Form, HttpError, HTTPProtocol, Query
from .io import Request, Response
from .websocket import ConnectionClosed  # noqa. Exposed for convenience.
from .websocket import WSProtocol

Route = namedtuple("Route", ["payload", "vars"])
HTTP_METHODS = [
    "GET",
    "HEAD",
    "POST",
    "PUT",
    "DELETE",
    "TRACE",
    "OPTIONS",
    "CONNECT",
    "PATCH",
]
# Everything between the colon and the closing braket, including the colon but not the
# braket.
CLEAN_PATH_PATTERN = re.compile(r":[^}]+(?=})")


class Roll(dict):
    """Deal with routes dispatching and events listening.

    You can subclass it to set your own `Protocol`, `Routes`, `Query`, `Form`,
    `Files`, `Request`, `Response` and/or `Cookies` class(es).
    """

    HttpProtocol = HTTPProtocol
    WebsocketProtocol = WSProtocol
    Routes = Routes
    Query = Query
    Form = Form
    Files = Files
    Request = Request
    Response = Response
    Cookies = Cookies

    def __init__(self):
        self.routes = self.Routes()
        self.hooks = defaultdict(list)
        self._urls = {}

    async def startup(self):
        await self.hook("startup")

    async def shutdown(self):
        await self.hook("shutdown")

    async def __call__(self, request: Request, response: Response):
        payload = request.route.payload
        try:
            if not await self.hook("request", request, response):
                if not payload:
                    raise HttpError(HTTPStatus.NOT_FOUND, request.path)
                # Uppercased in order to only consider HTTP verbs.
                if request.method.upper() not in payload:
                    raise HttpError(HTTPStatus.METHOD_NOT_ALLOWED)
                if not payload.get("lazy_body"):
                    await request.load_body()
                handler = payload[request.method]
                await handler(request, response, **request.route.vars)
        except Exception as error:
            await self.on_error(request, response, error)
        try:
            # Views exceptions should still pass by the response hooks.
            await self.hook("response", request, response)
        except Exception as error:
            await self.on_error(request, response, error)
        return response

    async def on_error(self, request: Request, response: Response, error):
        if not isinstance(error, HttpError):
            error = HttpError(HTTPStatus.INTERNAL_SERVER_ERROR, str(error).encode())
        response.status = error.status
        response.body = error.message
        try:
            await self.hook("error", request, response, error)
        except Exception as e:
            response.status = HTTPStatus.INTERNAL_SERVER_ERROR
            response.body = str(e)

    def factory(self):
        return self.HttpProtocol(self)

    def lookup(self, request):
        request.route = Route(*self.routes.match(request.path))

    def _get_protocol_class(self, protocol):
        klass_attr = protocol.title() + "Protocol"
        klass = getattr(self, klass_attr, None)
        assert klass, (
            f"No class handler declared for {protocol} protocol. "
            f"Add a {klass_attr} key to your Roll app."
        )
        return klass

    def route(
        self, path: str, methods: list = None, protocol: str = "http", **extras: dict
    ):

        protocol_class = self._get_protocol_class(protocol)
        # Computed at load time for perf.
        extras["protocol"] = protocol
        extras["_protocol_class"] = protocol_class

        def add_route(view):
            nonlocal methods
            if inspect.isclass(view):
                inst = view()
                if methods is not None:
                    raise AttributeError("Can't use `methods` with class view")
                payload = {}
                for method in HTTP_METHODS:
                    key = f"on_{method.lower()}"
                    func = getattr(inst, key, None)
                    if func:
                        payload[method] = func
                if not payload:
                    raise ValueError(f"Empty view: {view}")
            else:
                if methods is None:
                    methods = ["GET"]
                payload = {method: view for method in methods}
            payload.update(extras)
            if protocol_class.ALLOWED_METHODS:
                assert set(methods) <= set(protocol_class.ALLOWED_METHODS)
            self.routes.add(path, **payload)
            self._register_route_name(path, view, extras.get("name"))
            return view

        return add_route

    def _register_route_name(self, path: str, view: Callable, name: str = None):
        cleaned = CLEAN_PATH_PATTERN.sub("", path)
        if not name:
            name = view.__name__.lower()
        if name in self._urls:
            _, view = self._urls[name]
            ref = f"{view.__module__}.{view.__name__}"
            raise ValueError(f"Route with name {name} already exists: {ref}")
        self._urls[name] = cleaned, view

    def url_for(self, name: str, **kwargs):
        try:
            path, _ = self._urls[name]
            return path.format(**kwargs)  # Raises a KeyError too if some param misses
        except KeyError:
            raise ValueError(f"No route found with name {name} and params {kwargs}")

    def listen(self, name: str):
        def wrapper(func):
            self.hooks[name].append(func)

        return wrapper

    async def hook(self, name: str, *args, **kwargs):
        for func in self.hooks[name]:
            result = await func(*args, **kwargs)
            if result:  # Allows to shortcut the chain.
                return result
