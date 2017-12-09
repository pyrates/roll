# cython: language_level=3

"""Howdy fellow developer!

We are glad you are taking a look at our code :-)
Make sure to check out our documentation too:
http://roll.readthedocs.io/en/latest/

If you do not understand why something is not working as expected,
please submit an issue (or even better a pull-request with at least
a test failing): https://github.com/pyrates/roll/issues/new
"""
from . cimport cparser
import asyncio
from collections import namedtuple
from http import HTTPStatus
from typing import TypeVar
from urllib.parse import parse_qs, unquote

from autoroutes._autoroutes cimport Routes as BaseRoutes
from biscuits import Cookie, parse
from httptools import parse_url

try:
    # In case you use json heavily, we recommend installing
    # https://pypi.python.org/pypi/ujson for better performances.
    import ujson as json
except ImportError:
    import json as json


HttpCode = TypeVar('HttpCode', HTTPStatus, int)


# Prevent creating new HTTPStatus instances when
# dealing with integer statuses.
STATUSES = {}

for status in HTTPStatus:
    STATUSES[status.value] = status
    STATUSES[status] = status

class HttpError(Exception):
    """Exception meant to be raised when an error is occurring.

    E.g.:
        Within your view `raise HttpError(HTTPStatus.BAD_REQUEST)` will
        direcly return a 400 HTTP status code with descriptive content.
    """

    __slots__ = ('status', 'message')

    def __init__(self, http_code: HttpCode, message: str=None):
        # Idempotent if `http_code` is already an `HTTPStatus` instance.
        self.status = HTTPStatus(http_code)
        self.message = message or self.status.phrase


cdef class Query(dict):
    """Allow to access casted GET parameters from `request.query`.

    E.g.:
        `request.query.int('weight', 0)` will return an integer or zero.
    """

    TRUE_STRINGS = ('t', 'true', 'yes', '1', 'on')
    FALSE_STRINGS = ('f', 'false', 'no', '0', 'off')
    NONE_STRINGS = ('n', 'none', 'null')

    def get(self, key: str, default=...):
        return self.list(key, [default])[0]

    def list(self, key: str, default=...):
        try:
            return self[key]
        except KeyError:
            if default is ... or default == [...]:
                raise HttpError(HTTPStatus.BAD_REQUEST,
                                "Missing '{}' key".format(key))
            return default

    def bool(self, key: str, default=...):
        value = self.get(key, default)
        if value in (True, False, None):
            return value
        value = value.lower()
        if value in self.TRUE_STRINGS:
            return True
        elif value in self.FALSE_STRINGS:
            return False
        elif value in self.NONE_STRINGS:
            return None
        raise HttpError(
            HTTPStatus.BAD_REQUEST,
            "Wrong boolean value for '{}={}'".format(key, self.get(key)))

    def int(self, key: str, default=...):
        try:
            return int(self.get(key, default))
        except ValueError:
            raise HttpError(HTTPStatus.BAD_REQUEST,
                            "Key '{}' must be castable to int".format(key))

    def float(self, key: str, default=...):
        try:
            return float(self.get(key, default))
        except ValueError:
            raise HttpError(HTTPStatus.BAD_REQUEST,
                            "Key '{}' must be castable to float".format(key))


class Cookies(dict):

    def set(self, name, *args, **kwargs):
        self[name] = Cookie(name, *args, **kwargs)


cdef class Request(dict):
    """A container for the result of the parsing on each request.

    The default parsing is made by `httptools.HttpRequestParser`.
    """
    __slots__ = ('app', 'url', 'path', 'query_string', '_query', 'method',
                 'body', 'headers', 'route', '_cookies')

    cdef:
        size_t length
        const char *_method
        size_t method_len
        const char *_path
        size_t path_len
        int minor_version
        cparser.phr_header _headers[10]
        size_t num_headers
        public int status
        public object app
        public bytes url
        public str path
        public str query_string
        public object _query
        public str method
        public bytes body
        public dict headers
        public object route
        public object _cookies

    def __cinit__(self, app):
        self.num_headers = <size_t>10

    def __init__(self, app):
        self.app = app
        self.headers = {}
        self.reset()

    def reset(self):
        self.headers.clear()
        self.body = b''
        self._cookies = None
        self._query = None
        self.clear()

    @property
    def cookies(self):
        if self._cookies is None:
            self._cookies = parse(self.headers.get('COOKIE', ''))
        return self._cookies

    @property
    def query(self):
        if self._query is None:
            parsed_qs = parse_qs(self.query_string, keep_blank_values=True)
            self._query = self.app.Query(parsed_qs)
        return self._query

    cdef read_headers(self):
        for header in self._headers:
            if header.name_len:
                self.headers[header.name[:header.name_len].decode().upper()] = \
                    header.value[:header.value_len].decode()

    cdef get_method(self):
        return self._method[:self.method_len].decode().upper()

    cdef get_path(self):
        return self._path[:self.path_len]

    cdef feed_data(self, bytes data):
        self.status = cparser.phr_parse_request(
            data, len(data), &self._method, &self.method_len, &self._path,
            &self.path_len, &self.minor_version, self._headers,
            <size_t*>&self.num_headers, 0)
        return self.status


cdef class Response:
    """A container for `status`, `headers` and `body`."""
    __slots__ = ('app', '_status', 'headers', 'body', '_cookies')

    cdef:
        public object app
        public object _status
        public dict headers
        public object body
        public object _cookies

    def __init__(self, app):
        self.app = app
        self.headers = {}
        self.reset()

    def reset(self):
        self._status = None
        self.body = b''
        self.status = HTTPStatus.OK
        self.headers.clear()
        self._cookies = None

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, http_code: HttpCode):
        # Idempotent if `http_code` is already an `HTTPStatus` instance.
        self._status = STATUSES[http_code]

    def json(self, value: dict):
        # Shortcut from a dict to JSON with proper content type.
        self.headers['Content-Type'] = 'application/json; charset=utf-8'
        self.body = json.dumps(value)

    json = property(None, json)

    @property
    def cookies(self):
        if self._cookies is None:
            self._cookies = Cookies()
        return self._cookies


cdef class Protocol:
    """Responsible of parsing the request and writing the response."""

    __slots__ = ('app', 'req', 'parser', 'resp', 'writer')
    _BODYLESS_METHODS = ('HEAD', 'CONNECT')
    _BODYLESS_STATUSES = (HTTPStatus.CONTINUE, HTTPStatus.SWITCHING_PROTOCOLS,
                          HTTPStatus.PROCESSING, HTTPStatus.NO_CONTENT,
                          HTTPStatus.NOT_MODIFIED)

    cdef:
        object app
        object writer
        Request request
        Response response

    def __init__(self, app):
        self.app = app
        self.request = self.app.Request(self.app)
        self.response = self.app.Response(self.app)

    def data_received(self, data: bytes):
        self.request.reset()
        self.response.reset()
        status = self.request.feed_data(data)
        if status == -1:
            self.response.status = HTTPStatus.BAD_REQUEST
            self.response.body = b'Unparsable request'
            self.write()
        else:
            self.request.method = self.request.get_method()
            self.request.read_headers()
            self.request.body += data[self.request.status:]
            self.on_url(self.request.get_path())
            # self.writer.write(b'HTTP/1.1 200 OK\r\n'
            #                   b'Content-Length: 27\r\n'
            #                   b'Content-Type: application/json\r\n'
            #                   b'\r\n'
            #                   b'{"message":"Hello, World!"}')
            # return
            self.on_message_complete()

    def on_url(self, url: bytes):
        self.request.url = url
        parsed = parse_url(self.request.url)
        self.request.path = unquote(parsed.path.decode())
        self.request.query_string = (parsed.query or b'').decode()

    def on_message_complete(self):
        task = self.app.loop.create_task(self.app(self.request, self.response))
        task.add_done_callback(self.write)

    def connection_made(self, transport):
        self.writer = transport

    def connection_lost(self, exc):
        pass

    def data_received(self, data):
        pass

    def eof_received(self):
        pass

    # May or may not have "future" as arg.
    def write(self, *args):
        # Appends bytes for performances.
        payload = b'HTTP/1.1 %a %b\r\n' % (
            self.response.status.value, self.response.status.phrase.encode())
        if not isinstance(self.response.body, bytes):
            self.response.body = str(self.response.body).encode()
        # https://tools.ietf.org/html/rfc7230#section-3.3.2 :scream:
        bodyless = (self.response.status in self._BODYLESS_STATUSES or
                    (hasattr(self, 'request') and
                     self.request.method in self._BODYLESS_METHODS))
        if 'Content-Length' not in self.response.headers and not bodyless:
            length = len(self.response.body)
            self.response.headers['Content-Length'] = length
        if self.response._cookies:
            # https://tools.ietf.org/html/rfc7230#page-23
            for cookie in self.response.cookies.values():
                payload += b'Set-Cookie: %b\r\n' % str(cookie).encode()
        for key, value in self.response.headers.items():
            payload += b'%b: %b\r\n' % (key.encode(), str(value).encode())
        payload += b'\r\n'
        if self.response.body and not bodyless:
            payload += self.response.body
        self.writer.write(payload)
        # if not self.parser.should_keep_alive():
        #     self.writer.close()


cdef class Routes(BaseRoutes):
    """Customized to raise our own `HttpError` in case of 404."""

    def match(self, url: str):
        payload, params = super().match(url)
        if not payload:
            raise HttpError(HTTPStatus.NOT_FOUND, url)
        return payload, params


Route = namedtuple('Route', ['payload', 'vars'])


class Roll:
    """Deal with routes dispatching and events listening.

    You can subclass it to set your own `Protocol`, `Routes`, `Query`,
    `Request` and/or `Response` class(es).
    """
    Protocol = Protocol
    Routes = Routes
    Query = Query
    Request = Request
    Response = Response

    def __init__(self):
        self.routes = self.Routes()
        self.hooks = {}

    async def startup(self):
        await self.hook('startup')

    async def shutdown(self):
        await self.hook('shutdown')

    async def __call__(self, request: Request, response: Response):
        try:
            request.route = Route(*self.routes.match(request.path))
            if not await self.hook('request', request, response):
                # Uppercased in order to only consider HTTP verbs.
                if request.method.upper() not in request.route.payload:
                    raise HttpError(HTTPStatus.METHOD_NOT_ALLOWED)
                handler = request.route.payload[request.method]
                await handler(request, response, **request.route.vars)
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
        return self.Protocol(self)

    def route(self, path: str, methods: list=None, **extras: dict):
        if methods is None:
            methods = ['GET']

        def wrapper(func):
            payload = {method: func for method in methods}
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
