"""Howdy fellow developer!

We are glad you are taking a look at our code :-)
Make sure to check out our documentation too:
http://roll.readthedocs.io/en/latest/

If you do not understand why something is not working as expected,
please submit an issue (or even better a pull-request with at least
a test failing): https://github.com/pyrates/roll/issues/new
"""
import asyncio
import operator
import enum

from abc import ABC, abstractmethod
from collections import namedtuple, defaultdict
from functools import wraps, reduce
from http import HTTPStatus
from io import BytesIO
from typing import TypeVar
from urllib.parse import parse_qs, unquote

from autoroutes import Routes
from biscuits import Cookie, parse
from httptools import (
    HttpParserUpgrade, HttpParserError, HttpRequestParser, parse_url)
from multifruits import Parser, extract_filename, parse_content_disposition

try:
    # In case you use json heavily, we recommend installing
    # https://pypi.python.org/pypi/ujson for better performances.
    import ujson as json
    JSONDecodeError = ValueError
except ImportError:
    import json as json
    from json.decoder import JSONDecodeError


HttpCode = TypeVar('HttpCode', HTTPStatus, int)


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
        'app', '_url', 'path', 'query_string', '_query', 'upgrade_protocol',
        'method', 'body', 'headers', 'route', '_cookies', '_form', '_files',
    )

    def __init__(self, app, method='GET', url=b'/', body=b'', headers=None):
        self.app = app
        self.method = method
        if headers is None:
            self.headers = {}
        self.body = body
        self._cookies = None
        self._query = None
        self._form = None
        self._files = None
        self.url = url
        self.upgrade_protocol = None

    def upgrade(self, *args, **kwargs):
        if self.upgrade_protocol is None:
            raise NotImplementedError('This request is not upgradeable.')
        return self.upgrade_protocol(*args, **kwargs)

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, url):
        self._url = url
        parsed = parse_url(url)
        self.path = unquote(parsed.path.decode())
        self.query_string = (parsed.query or b'').decode()
        
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
    __slots__ = (
        'app', 'request', 'headers', 'body', 'bodyless',
        '_cookies','_status',
    )

    BODYLESS_METHODS = frozenset(('HEAD', 'CONNECT'))
    BODYLESS_STATUSES = frozenset((
        HTTPStatus.CONTINUE, HTTPStatus.SWITCHING_PROTOCOLS,
        HTTPStatus.PROCESSING, HTTPStatus.NO_CONTENT,
        HTTPStatus.NOT_MODIFIED))
    
    def __init__(self, app, request=None, status=HTTPStatus.OK, body=b''):
        self.app = app
        self.request = request
        self._cookies = None
        self._status = None
        self.body = body
        self.headers = {}
        self.status = status

    @classmethod
    def from_http_error(cls, app, error):
        return cls(app, status=error.status, body=error.message)

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, http_code: HttpCode):
        # Idempotent if `http_code` is already an `HTTPStatus` instance.
        self._status = HTTPStatus(http_code)
        self.bodyless = (
            self._status in self.BODYLESS_STATUSES or
            (self.request is not None and
             self.request.method in self.BODYLESS_METHODS))

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

    def __bytes__(self):
        response = b'HTTP/1.1 %a %b\r\n' % (
            self.status.value, self.status.phrase.encode())

        if self._cookies:
            # https://tools.ietf.org/html/rfc7230#page-23
            for cookie in self.cookies.values():
                response += b'Set-Cookie: %b\r\n' % str(cookie).encode()

        # https://tools.ietf.org/html/rfc7230#section-3.3.2 :scream:
        for key, value in self.headers.items():
            response += b'%b: %b\r\n' % (key.encode(), str(value).encode())

        if not self.bodyless:
            if not isinstance(self.body, bytes):
                body = str(self.body).encode()
            else:
                body = self.body

            if 'Content-Length' not in self.headers:
                response += b'Content-Length: %i\r\n' % len(body)

            response += b'\r\n'
            if body:
                response += body
        else:
            response += b'\r\n'
        return response


# PROTOCOL STATUS FLAGS
class ProtocolStatus(enum.IntEnum):
    """The ProtocolStatus flags act like workflow states.

    On normal HTTP Request, the protocol is marked as NO_UPDATE.

    When an HTTP request demands an upgrade, we mark the
    protocol as UPGRADE_EXPECTED.

    No protocol methods marked as upgrade-delegated can be called
    until the upgrade is made. If a call is made despite this flag,
    a code 501 response (Not Implemented) is issued to the client.

    Once the protocol has received its upgrade, it's marked as 
    UPGRADED and can now delegate the marked methods to the 
    newly set "ProtocolUpgrade" object.
    """
    NO_UPGRADE, UPGRADE_EXPECTED, UPGRADED = range(1, 4)


class ProtocolUpgrade(ABC):

    @abstractmethod
    def connection_lost(self, protocol, exc) -> None:
        """Connection with the client was lost.
        """

    @abstractmethod
    def data_received(self, protocol, data: bytes) -> None:
        """Data was received from the client: dispatch to the upgrade.
        """

    @abstractmethod
    def write(self, protocol, *args) -> None:
        """Write to the client, on the upgrade channel.
        """

    @abstractmethod
    def __call__(self, protocol) -> bytes:
        """Returns an upgrade response for the client.
        """


def upgrade_delegator(method):
    bubble_up = getattr(method, 'bubble_up', False)
    @wraps(method)
    def delegate_to(protocol, *args, **kwargs):
        if protocol.status == ProtocolStatus.NO_UPGRADE:
            return method(protocol, *args, **kwargs)
        elif protocol.status == ProtocolStatus.UPGRADE_EXPECTED:
            error = HttpError(
                HTTPStatus.NOT_IMPLEMENTED,
                message='Expected upgrade to {} protocol failed.'.format(
                    protocol.upgrade_type))
            protocol.report_http_error(error)
        else:
            surrogate = getattr(protocol.upgrade, method.__name__)
            surrogate(protocol, *args, **kwargs)
            if bubble_up:
                method(protocol, *args, **kwargs)
    return delegate_to


class Protocol(asyncio.Protocol):
    """Responsible of parsing the request and writing the response."""

    __slots__ = ('app', 'request', 'task', 'status', 'error', 
                 'parser', 'writer', 'upgrade', 'upgrade_type')
    RequestParser = HttpRequestParser

    def __init__(self, app):
        self.app = app
        self.parser = self.RequestParser(self)
        self.keep_alive = False
        self.upgrade = None
        self.status = ProtocolStatus.NO_UPGRADE
        self.prime_for_request()

    def prime_for_request(self):
        # This method is called when we are expecting requests.
        # In case of a new protocol or a protocol kept alive.
        self.request = None
        self.task = None
        self.error = None

    def upgrade_protocol(self, upgrade):
        if self.status != ProtocolStatus.UPGRADE_EXPECTED:
            # We are trying to upgrade request that did not ask for it
            # Do we really want to allow that ? If not raise. If so, log ?
            ...
        assert isinstance(upgrade, ProtocolUpgrade)
        response = upgrade(self)
        self.writer.write(response)  # writing the upgrade response
        self.status = ProtocolStatus.UPGRADED
        self.upgrade = upgrade  # We are ready to deputize.

    def connection_made(self, transport):
        # This is done only once for possibly several requests, depending
        # on the keep alive marker.
        self.writer = transport

    @upgrade_delegator
    def connection_lost(self, exc):
        super().connection_lost(exc)

    @upgrade_delegator
    def data_received(self, data: bytes):
        try:
            self.parser.feed_data(data)
        except HttpParserUpgrade:
            # This request needs an upgrade.
            # We mark ourselves as needing an upgrade and provide
            # the request with the means to do so.
            self.status = ProtocolStatus.UPGRADE_EXPECTED
            self.request.upgrade_protocol = self.upgrade_protocol
            self.upgrade_type = self.request.headers['UPGRADE']
        except HttpParserError:
            self.report_http_error(HttpError(
                HTTPStatus.BAD_REQUEST,
                message=b'Unparsable request'))

    @upgrade_delegator
    def write(self, data: bytes, close: bool=False):
        self.writer.write(data)
        if close:
            self.writer.close()

    def reply(self, task):
        # `reply` is used as the main task callback.
        response = task.result()
        self.write(bytes(response))
        if not self.keep_alive:
            self.writer.close()
        else:
            self.prime_for_request()

    def report_http_error(self, error):
        # Direct output through the original transport.
        # This is a HTTP error, no upgrade would change that.
        response = self.app.Response.from_http_error(self.app, error)
        self.error = response
        self.writer.write(bytes(response))
        self.writer.close()

    # All on_xxx methods are in use by httptools parser.
    # See https://github.com/MagicStack/httptools#apis
    def on_message_begin(self):
        if self.request is None:
            self.request = self.app.Request(self.app)

    def on_header(self, name: bytes, value: bytes):
        value = value.decode()
        if value:
            name = name.decode().upper()
            if name in self.request.headers:
                self.request.headers[name] += ', {}'.format(value)
            else:
                self.request.headers[name] = value

    def on_headers_complete(self):
        self.keep_alive = self.parser.should_keep_alive()
        self.request.method = self.parser.get_method().decode().upper()

    def on_body(self, body: bytes):
        # FIXME do not put all body in RAM blindly.
        self.request.body += body

    def on_url(self, url: bytes):
        self.request.url = url

    def on_message_complete(self):
        self.task = self.app.loop.create_task(self.app(self.request))
        self.task.add_done_callback(self.reply)
            

Route = namedtuple('Route', ['payload', 'vars'])


class Roll(dict):
    """Deal with routes dispatching and events listening.

    You can subclass it to set your own `Protocol`, `Routes`, `Query`, `Form`,
    `Files`, `Request`, `Response` and/or `Cookies` class(es).
    """
    Protocol = Protocol
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

    async def lookup(self, request: Request, response: Response):
        route = Route(*self.routes.match(request.path))
        request.route = route
        if not await self.hook('request', request, response):
            if not request.route.payload:
                raise HttpError(HTTPStatus.NOT_FOUND, request.path)
            # Uppercased in order to only consider HTTP verbs.
            if request.method.upper() not in request.route.payload:
                raise HttpError(HTTPStatus.METHOD_NOT_ALLOWED)
            return route, route.vars

    async def __call__(self, request: Request) -> Response:
        response = self.Response(self, request)
        try:
            found = await self.lookup(request, response)
            if found is not None:
                handler, params = found
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
