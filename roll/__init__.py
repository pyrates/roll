"""Howdy fellow developer!

We are glad you are taking a look at our code :-)
Make sure to check out our documentation too:
http://roll.readthedocs.io/en/latest/

If you do not understand why something is not working as expected,
please submit an issue (or even better a pull-request with at least
a test failing): https://github.com/pyrates/roll/issues/new
"""

import inspect
from collections import namedtuple
from http import HTTPStatus

from autoroutes import Routes

from .http import Cookies, Files, Form, HttpError, HTTPProtocol, Query
from .io import Request, Response
from .websocket import ConnectionClosed  # noqa. Exposed for convenience.
from .websocket import WSProtocol


Route = namedtuple('Route', ['payload', 'vars'])


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
        self.hooks = {}

    async def startup(self):
        await self.hook('startup')

    async def shutdown(self):
        await self.hook('shutdown')

    def inspect(self, func):
        func.__signature__ = inspect.signature(func, follow_wrapped=True)

    async def invoke(self, func, request, response):
        params = {}
        for name, param in func.__signature__.parameters.items():
            if param.kind != param.VAR_KEYWORD:
                if name == 'request':
                    value = request
                elif name == 'response':
                    value = response
                elif name in request.__namespace__:
                    member = getattr(request, name)
                    if inspect.iscoroutine(member):
                        value = await member
                    else:
                        value = member
                elif name in request.route.vars:
                    value = request.route.vars[name]
                else:
                    raise ValueError("Unknown param {name}".format(name=name))
                params[name] = value

        bound = func.__signature__.bind(**params)
        return await func(*bound.args, **bound.kwargs)

    async def __call__(self, request: Request, response: Response):
        try:
            if not await self.hook('request', request, response):
                if not request.route.payload:
                    raise HttpError(HTTPStatus.NOT_FOUND, request.path)
                # Uppercased in order to only consider HTTP verbs.
                if request.method.upper() not in request.route.payload:
                    raise HttpError(HTTPStatus.METHOD_NOT_ALLOWED)
                handler, before = request.route.payload[request.method]
                result = None
                for func in before:
                    result = await self.invoke(func, request, response)
                    if result:
                        break
                if not result:
                    await self.invoke(handler, request, response)
        except Exception as error:
            await self.on_error(request, response, error)
        try:
            # Views exceptions should still pass by the response hooks.
            await self.hook('response', request, response)
        except Exception as error:
            await self.on_error(request, response, error)
        return response

    async def on_error(self, request: Request, response: Response, error):
        if not isinstance(error, HttpError):
            error = HttpError(HTTPStatus.INTERNAL_SERVER_ERROR,
                              str(error).encode())
        response.status = error.status
        response.body = error.message
        try:
            await self.hook('error', request, response, error)
        except Exception as e:
            response.status = HTTPStatus.INTERNAL_SERVER_ERROR
            response.body = str(e)

    def factory(self):
        return self.HttpProtocol(self)

    def lookup(self, request):
        request.route = Route(*self.routes.match(request.path))

    def route(self, path: str, methods: list=None,
              protocol: str='http', before: list=None, **extras: dict):
        if methods is None:
            methods = ['GET']
        before = before or []
        if before and not isinstance(before, list):
            before = [before]
        for func in before:
            self.inspect(func)
        klass_attr = protocol.title() + 'Protocol'
        klass = getattr(self, klass_attr, None)
        assert klass, ('No class handler declared for {} protocol. Add a {} '
                       'key to your Roll app.'.format(protocol, klass_attr))
        if klass.ALLOWED_METHODS:
            assert set(methods) <= set(klass.ALLOWED_METHODS)
        # Computed at load time for perf.
        extras['protocol'] = protocol
        extras['_protocol_class'] = klass

        def wrapper(func):
            self.inspect(func)
            payload = {method: (func, before) for method in methods}
            payload.update(extras)
            self.routes.add(path, **payload)
            return func

        return wrapper

    def listen(self, name: str):
        def wrapper(func):
            self.hooks.setdefault(name, [])
            self.hooks[name].append(func)
        return wrapper

    async def hook(self, name: str, *args, **kwargs):
        try:
            for func in self.hooks[name]:
                result = await func(*args, **kwargs)
                if result:  # Allows to shortcut the chain.
                    return result
        except KeyError:
            # Nobody registered to this event, let's roll anyway.
            pass
