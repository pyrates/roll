"""Howdy fellow developer!

We are glad you are taking a look at our code :-)
Make sure to check out our documentation too:
http://roll.readthedocs.io/en/latest/

If you do not understand why something is not working as expected,
please submit an issue (or even better a pull-request with at least
a test failing): https://github.com/pyrates/roll/issues/new
"""

import asyncio
from collections import namedtuple
from http import HTTPStatus
from io import BytesIO
from typing import TypeVar
from urllib.parse import parse_qs, unquote

from autoroutes import Routes
from biscuits import Cookie, parse
from httptools import (HttpParserError, HttpParserUpgrade, HttpRequestParser,
                       parse_url)
from multifruits import Parser, extract_filename, parse_content_disposition
from websockets import ConnectionClosed  # exposed for convenience
from websockets import InvalidHandshake, WebSocketCommonProtocol, handshake

try:
    # In case you use json heavily, we recommend installing
    # https://pypi.python.org/pypi/ujson for better performances.
    import ujson as json
    JSONDecodeError = ValueError
except ImportError:
    import json as json
    from json.decoder import JSONDecodeError


HttpCode = TypeVar('HttpCode', HTTPStatus, int)


# Prevent creating new HTTPStatus instances when
# dealing with integer statuses.
STATUSES = {}

for status in HTTPStatus:
    STATUSES[status.value] = status


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


class Multidict(dict):
    """Data structure to deal with several values for the same key.

    Useful for query string parameters or form-like POSTed ones.
    """

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


class Query(Multidict):
    """Allow to access casted GET parameters from `request.query`.

    E.g.:
        `request.query.int('weight', 0)` will return an integer or zero.
    """

    TRUE_STRINGS = ('t', 'true', 'yes', '1', 'on')
    FALSE_STRINGS = ('f', 'false', 'no', '0', 'off')
    NONE_STRINGS = ('n', 'none', 'null')

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


class Form(Query):
    """Allow to access casted POST parameters from `request.body`."""


class Files(Multidict):
    """Allow to access POSTed files from `request.body`."""


class Multipart:
    """Responsible of the parsing of multipart encoded `request.body`."""

    __slots__ = ('app', 'form', 'files', '_parser', '_current',
                 '_current_headers', '_current_params')

    def __init__(self, app):
        self.app = app

    def initialize(self, content_type: str):
        self._parser = Parser(self, content_type.encode())
        self.form = self.app.Form()
        self.files = self.app.Files()
        return self.form, self.files

    def feed_data(self, data: bytes):
        self._parser.feed_data(data)

    def on_part_begin(self):
        self._current_headers = {}

    def on_header(self, field: bytes, value: bytes):
        self._current_headers[field] = value

    def on_headers_complete(self):
        disposition_type, params = parse_content_disposition(
            self._current_headers.get(b'Content-Disposition'))
        if not disposition_type:
            return
        self._current_params = params
        if b'Content-Type' in self._current_headers:
            self._current = BytesIO()
            self._current.filename = extract_filename(params)
            self._current.content_type = self._current_headers[b'Content-Type']
            self._current.params = params
        else:
            self._current = ''

    def on_data(self, data: bytes):
        if b'Content-Type' in self._current_headers:
            self._current.write(data)
        else:
            self._current += data.decode()

    def on_part_complete(self):
        name = self._current_params.get(b'name', b'').decode()
        if b'Content-Type' in self._current_headers:
            if name not in self.files:
                self.files[name] = []
            self._current.seek(0)
            self.files[name].append(self._current)
        else:
            if name not in self.form:
                self.form[name] = []
            self.form[name].append(self._current)
        self._current = None


class Cookies(dict):
    """A Cookies management class, built on top of biscuits."""

    def set(self, name, *args, **kwargs):
        self[name] = Cookie(name, *args, **kwargs)


class Request(dict):
    """A container for the result of the parsing on each request.

    The default parsing is made by `httptools.HttpRequestParser`.
    """
    __slots__ = (
        'app', 'url', 'path', 'query_string', '_query',
        'method', 'body', 'headers', 'route', '_cookies', '_form', '_files',
        'upgrade'
    )

    def __init__(self, app):
        self.app = app
        self.headers = {}
        self.body = b''
        self.upgrade = None
        self._cookies = None
        self._query = None
        self._form = None
        self._files = None

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

    def _parse_multipart(self):
        parser = Multipart(self.app)
        self._form, self._files = parser.initialize(self.content_type)
        try:
            parser.feed_data(self.body)
        except ValueError:
            raise HttpError(HTTPStatus.BAD_REQUEST,
                            'Unparsable multipart body')

    def _parse_urlencoded(self):
        try:
            parsed_qs = parse_qs(self.body.decode(), keep_blank_values=True,
                                 strict_parsing=True)
        except ValueError:
            raise HttpError(HTTPStatus.BAD_REQUEST,
                            'Unparsable urlencoded body')
        self._form = self.app.Form(parsed_qs)

    @property
    def form(self):
        if self._form is None:
            if 'multipart/form-data' in self.content_type:
                self._parse_multipart()
            elif 'application/x-www-form-urlencoded' in self.content_type:
                self._parse_urlencoded()
            else:
                self._form = self.app.Form()
        return self._form

    @property
    def files(self):
        if self._files is None:
            if 'multipart/form-data' in self.content_type:
                self._parse_multipart()
            else:
                self._files = self.app.Files()
        return self._files

    @property
    def json(self):
        try:
            return json.loads(self.body.decode())
        except (UnicodeDecodeError, JSONDecodeError):
            raise HttpError(HTTPStatus.BAD_REQUEST, 'Unparsable JSON body')

    @property
    def content_type(self):
        return self.headers.get('CONTENT-TYPE', '')

    @property
    def host(self):
        return self.headers.get('HOST', '')


class Response:
    """A container for `status`, `headers` and `body`."""
    __slots__ = ('app', '_status', 'headers', 'body', '_cookies')

    def __init__(self, app):
        self.app = app
        self.body = b''
        self.status = HTTPStatus.OK
        self.headers = {}
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
            self._cookies = self.app.Cookies()
        return self._cookies


class WSProtocol(WebSocketCommonProtocol):

    NEEDS_UPGRADE = True
    ALLOWED_METHODS = {'GET'}
    TIMEOUT = 5
    MAX_SIZE = 2 ** 20  # 1 megabytes
    MAX_QUEUE = 64
    READ_LIMIT = 2 ** 16
    WRITE_LIMIT = 2 ** 16

    def __init__(self, request):
        self.request = request
        super().__init__(
            timeout=self.TIMEOUT,
            max_size=self.MAX_SIZE,
            max_queue=self.MAX_QUEUE,
            read_limit=self.READ_LIMIT,
            write_limit=self.WRITE_LIMIT)

    def handshake(self, response):
        """Websocket handshake, handled by `websockets`
        """
        def get_header(k):
            return self.request.headers.get(k.upper(), '')

        def set_header(k, v):
            response.headers[k] = v

        try:
            key = handshake.check_request(get_header)
            handshake.build_response(set_header, key)
        except InvalidHandshake:
            raise RuntimeError('Invalid websocket request')

        subprotocol = None
        ws_protocol = get_header('Sec-Websocket-Protocol')
        subprotocols = self.request.route.payload.get('subprotocols')
        if subprotocols and ws_protocol:
            # select a subprotocol
            client_subprotocols = tuple(
                (p.strip() for p in ws_protocol.split(',')))
            for p in client_subprotocols:
                if p in subprotocols:
                    subprotocol = p
                    set_header('Sec-Websocket-Protocol', subprotocol)
                    break

        # Return the subprotocol agreed upon, if any
        self.subprotocol = subprotocol

    async def run(self):
        # See https://tools.ietf.org/html/rfc6455#page-45
        try:
            await self.request.app.hook(
                'websocket_connect', self.request, self)
            await self.request.route.payload['GET'](self.request, self)
        except ConnectionClosed:
            # The client closed the connection.
            # We cancel the future to be sure it's in order.
            await self.close(1002, 'Connection closed untimely.')
        except asyncio.CancelledError:
            # The websocket task was cancelled
            # We need to warn the client.
            await self.close(1001, 'Handler cancelled.')
        except Exception as exc:
            # A more serious error happened.
            # The websocket handler was untimely terminated
            # by an unwarranted exception. Warn the client.
            await self.close(1011, 'Handler died prematurely.')
            raise
        else:
            # The handler finished gracefully.
            # We can close the socket in peace.
            await self.close()
        finally:
            await self.request.app.hook(
                'websocket_disconnect', self.request, self)


class HTTPProtocol(asyncio.Protocol):
    """Responsible of parsing the request and writing the response."""

    __slots__ = ('app', 'request', 'parser', 'response', 'transport', 'task')
    _BODYLESS_METHODS = ('HEAD', 'CONNECT')
    _BODYLESS_STATUSES = (HTTPStatus.CONTINUE, HTTPStatus.SWITCHING_PROTOCOLS,
                          HTTPStatus.PROCESSING, HTTPStatus.NO_CONTENT,
                          HTTPStatus.NOT_MODIFIED)
    RequestParser = HttpRequestParser
    NEEDS_UPGRADE = False
    ALLOWED_METHODS = None  # Means all.

    def __init__(self, app):
        self.app = app
        self.parser = self.RequestParser(self)
        self.task = None

    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data: bytes):
        try:
            self.parser.feed_data(data)
        except HttpParserUpgrade:
            # The upgrade raise is done after all the on_x
            # We acted upon the upgrade earlier, so we just pass.
            pass
        except HttpParserError as error:
            # If the parsing failed before on_message_begin, we don't have a
            # response.
            self.response = self.app.Response(self.app)
            # Original error stored by httptools.
            if isinstance(error.__context__, HttpError):
                error = error.__context__
                self.response.status = error.status
                self.response.body = error.message
            else:
                self.response.status = HTTPStatus.BAD_REQUEST
                self.response.body = b'Unparsable request'
            self.write()

    def upgrade(self):
        handler_protocol = self.request.route.payload.get('protocol', 'http')

        if self.request.upgrade != handler_protocol:
            raise HttpError(HTTPStatus.NOT_IMPLEMENTED,
                            'Request cannot be upgraded.')

        protocol_class = self.request.route.payload['_protocol_class']
        new_protocol = protocol_class(self.request)
        new_protocol.handshake(self.response)
        self.response.status = HTTPStatus.SWITCHING_PROTOCOLS
        self.write()
        new_protocol.connection_made(self.transport)
        new_protocol.connection_open()
        self.transport.set_protocol(new_protocol)
        return new_protocol

    # All on_xxx methods are in use by httptools parser.
    # See https://github.com/MagicStack/httptools#apis
    def on_header(self, name: bytes, value: bytes):
        self.request.headers[name.decode().upper()] = value.decode()

    def on_body(self, body: bytes):
        # FIXME do not put all body in RAM blindly.
        self.request.body += body

    def on_url(self, url: bytes):
        self.request.method = self.parser.get_method().decode().upper()
        self.request.url = url
        parsed = parse_url(url)
        self.request.path = unquote(parsed.path.decode())
        self.request.query_string = (parsed.query or b'').decode()
        self.app.lookup(self.request)

    def on_message_begin(self):
        self.request = self.app.Request(self.app)
        self.response = self.app.Response(self.app)

    def on_message_complete(self):
        if self.parser.should_upgrade():
            # An upgrade has been requested
            self.request.upgrade = self.request.headers['UPGRADE'].lower()
            new_protocol = self.upgrade()
            if new_protocol is not None:
                # No error occured during the upgrade
                # The protocol was found and the handler willing to comply
                # We run the protocol task.
                self.task = self.app.loop.create_task(new_protocol.run())
        else:
            # No upgrade was requested
            payload = self.request.route.payload
            if payload and payload['_protocol_class'].NEEDS_UPGRADE:
                # The handler need and upgrade: we need to complain.
                raise HttpError(HTTPStatus.UPGRADE_REQUIRED)
            # No upgrade was required and the handler didn't need any.
            # We run the normal task.
            self.task = self.app.loop.create_task(
                self.app(self.request, self.response))
            self.task.add_done_callback(self.write)

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
        if self.transport.is_closing():
            # Request has been aborted, thus socket as been closed, thus
            # transport has been closed?
            return
        try:
            self.transport.write(payload)
        except RuntimeError:  # transport may still be closed during write.
            # TODO: Pass into error hook when write is async.
            pass
        else:
            if not self.parser.should_keep_alive():
                self.transport.close()


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

    async def __call__(self, request: Request, response: Response):
        try:
            if not await self.hook('request', request, response):
                if not request.route.payload:
                    raise HttpError(HTTPStatus.NOT_FOUND, request.path)
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
