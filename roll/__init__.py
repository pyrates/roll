"""Howdy fellow developer!

We are glad you are taking a look at our code :-)
Make sure to check out our documentation too:
http://roll.readthedocs.io/en/latest/

If you do not understand why something is not working as expected,
please submit an issue (or even better a pull-request with at least
a test failing): https://github.com/pyrates/roll/issues/new
"""

from collections import namedtuple, defaultdict
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
        self.hooks = defaultdict(list)

    async def startup(self):
        await self.hook('startup')

    async def shutdown(self):
        await self.hook('shutdown')

    async def __call__(self, request: Request, response: Response):
        payload = request.route.payload
        handler = None
        if payload:
            try:
                # Uppercased in order to only consider HTTP verbs.
                handler = request.route.payload[request.method.upper()]
            except KeyError:
                pass
        try:
            if not await self.request_hook(handler, 'headers', request, response):
                if payload and not payload.get('lazy'):
                    await request.read()
                if not await self.request_hook(handler, 'request', request, response):
                    if not payload:
                        raise HttpError(HTTPStatus.NOT_FOUND, request.path)
                    if not handler:
                        raise HttpError(HTTPStatus.METHOD_NOT_ALLOWED)
                    await handler(request, response, **request.route.vars)
        except Exception as error:
            await self.on_error(request, response, error)
        try:
            # Views exceptions should still pass by the response hooks.
            await self.request_hook(handler, 'response', request, response)
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
              protocol: str='http', **extras: dict):
        if methods is None:
            methods = ['GET']
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
            if not hasattr(func, '__hooks__'):
                func.__hooks__ = defaultdict(list)
            payload = {method: func for method in methods}
            payload.update(extras)
            self.routes.add(path, **payload)
            return func

        return wrapper

    def listen(self, name: str, *handlers):
        def add_middleware(func):
            self.hooks[name].append(func)
            return func

        def add_decorator(func):
            if not hasattr(func, '__hooks__'):
                func.__hooks__ = defaultdict(list)
            func.__hooks__[name].extend(handlers)
            return func
        return add_decorator if handlers else add_middleware

    async def hook(self, name: str, *args, **kwargs):
        hooks = self.hooks[name]
        for func in hooks:
            responded = await func(*args, **kwargs)
            if responded:  # Allows to shortcut the chain.
                return responded

    async def request_hook(self, handler, name, request, response):
        responded = await self.hook(name, request, response)
        if responded:
            return responded
        if handler:  # None when 404.
            hooks = handler.__hooks__[name]
            for func in hooks:
                responded = await func(request, response)
                if responded:  # Allows to shortcut the chain.
                    return responded
