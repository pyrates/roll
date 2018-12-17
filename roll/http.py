import asyncio
from http import HTTPStatus
from io import BytesIO
from typing import TypeVar
from urllib.parse import unquote

from biscuits import Cookie
from httptools import (HttpParserError, HttpParserUpgrade, HttpRequestParser,
                       parse_url)
from multifruits import Parser, extract_filename, parse_content_disposition


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
