"""Howdy fellow developer!

We are glad you are taking a look at our code :-)
Make sure to check out our documentation too:
http://roll.readthedocs.io/en/latest/

If you do not understand why something is not working as expected,
please submit an issue (or even better a pull-request with at least
a test failing): https://github.com/pyrates/roll/issues/new
"""
import asyncio
from cgi import parse_header
from collections import namedtuple
from http import HTTPStatus
from typing import TypeVar
from urllib.parse import parse_qs

from autoroutes import Routes as BaseRoutes
from httptools import HttpParserError, HttpRequestParser, parse_url

from .extensions import options

try:
    # In case you use json heavily, we recommend installing
    # https://pypi.python.org/pypi/ujson for better performances.
    import ujson as json
except ImportError:
    import json as json


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


class ListDict(dict):
    """Deal with dicts containing either lists or a single element."""

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


class Query(ListDict):
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


def parse_multipart_form(body: bytes, boundary: bytes):
    """Parse a request body and returns fields and files ListDicts."""
    File = namedtuple('File', ['type', 'body', 'name'])
    files = ListDict()
    fields = ListDict()
    form_parts = body.split(boundary)
    for form_part in form_parts[1:-1]:
        file_name = None
        file_type = None
        field_name = None
        line_index = 2
        line_end_index = 0
        while not line_end_index == -1:
            line_end_index = form_part.find(b'\r\n', line_index)
            form_line = form_part[line_index:line_end_index].decode('utf-8')
            line_index = line_end_index + 2

            if not form_line:
                break

            colon_index = form_line.index(':')
            form_header_field = form_line[0:colon_index].lower()
            form_header_value, form_parameters = parse_header(
                form_line[colon_index + 2:])

            if form_header_field == 'content-disposition':
                if 'filename' in form_parameters:
                    file_name = form_parameters['filename']
                field_name = form_parameters.get('name')
            elif form_header_field == 'content-type':
                file_type = form_header_value

        post_data = form_part[line_index:-4]
        if file_name or file_type:
            file_ = File(type=file_type, name=file_name, body=post_data)
            if field_name in files:
                files[field_name].append(file_)
            else:
                files[field_name] = [file_]
        else:
            value = post_data.decode('utf-8')
            if field_name in fields:
                fields[field_name].append(value)
            else:
                fields[field_name] = [value]

    return fields, files


class Request:
    """A container for the result of the parsing on each request.

    The parsing is made by `httptools.HttpRequestParser`.
    """
    __slots__ = ('url', 'path', 'query_string', 'query', 'method', 'kwargs',
                 'body', 'headers', 'fields', 'files')

    def __init__(self):
        self.kwargs = {}
        self.headers = {}
        self.body = b''


class Response:
    """A container for `status`, `headers` and `body`."""
    __slots__ = ('_status', 'headers', 'body')

    def __init__(self):
        self._status = None
        self.body = b''
        self.status = HTTPStatus.OK
        self.headers = {}

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, http_code: HttpCode):
        # Idempotent if `http_code` is already an `HTTPStatus` instance.
        self._status = HTTPStatus(http_code)

    def json(self, value: dict):
        # Shortcut from a dict to a JSON with proper content type.
        self.headers['Content-Type'] = 'application/json'
        self.body = json.dumps(value)

    json = property(None, json)


class Protocol(asyncio.Protocol):
    """Responsible of parsing the request and writing the response.

    You can subclass it to set your own `Query`, `Request` or `Response`
    classes.
    """

    __slots__ = ('app', 'req', 'parser', 'resp', 'writer')
    Query = Query
    Request = Request
    RequestParser = HttpRequestParser
    Response = Response

    def __init__(self, app):
        self.app = app

    def data_received(self, data: bytes):
        self.parser = self.RequestParser(self)
        try:
            self.parser.feed_data(data)
        except HttpParserError:
            # If the parsing failed before on_message_begin, we don't have a
            # response.
            self.response = Response()
            self.response.status = HTTPStatus.BAD_REQUEST
            self.response.body = b'Unparsable request'
            self.write()

    def connection_made(self, transport):
        self.writer = transport

    # All on_xxx methods are in use by httptools parser.
    # See https://github.com/MagicStack/httptools#apis
    def on_header(self, name: bytes, value: bytes):
        self.request.headers[name.decode()] = value.decode()

    def on_body(self, body: bytes):
        content_type = self.request.headers['Content-Type']
        if 'multipart/form-data' in content_type:
            content_type, parameters = parse_header(content_type)
            self.request.fields, self.request.files = parse_multipart_form(
                body, parameters['boundary'].encode())
        else:
            self.request.body += body

    def on_url(self, url: bytes):
        self.request.url = url
        parsed = parse_url(url)
        self.request.path = parsed.path.decode()
        self.request.query_string = (parsed.query or b'').decode()
        parsed_qs = parse_qs(self.request.query_string, keep_blank_values=True)
        self.request.query = self.Query(parsed_qs)

    def on_message_begin(self):
        self.request = self.Request()
        self.response = self.Response()

    def on_message_complete(self):
        self.request.method = self.parser.get_method().decode().upper()
        task = self.app.loop.create_task(self.app(self.request, self.response))
        task.add_done_callback(self.write)

    # May or may not have "future" as arg.
    def write(self, *args):
        # Appends bytes for performances.
        payload = b'HTTP/1.1 %a %b\r\n' % (
            self.response.status.value, self.response.status.phrase.encode())
        if not isinstance(self.response.body, bytes):
            self.response.body = self.response.body.encode()
        if 'Content-Length' not in self.response.headers:
            length = len(self.response.body)
            self.response.headers['Content-Length'] = length
        for key, value in self.response.headers.items():
            payload += b'%b: %b\r\n' % (key.encode(), str(value).encode())
        payload += b'\r\n%b' % self.response.body
        self.writer.write(payload)
        if not self.parser.should_keep_alive():
            self.writer.close()


class Routes(BaseRoutes):
    """Customized to raise our own `HttpError` in case of 404."""

    def match(self, url: str):
        payload, params = super().match(url)
        if not payload:
            raise HttpError(HTTPStatus.NOT_FOUND, url)
        return payload, params


class Roll:
    """Deal with routes dispatching and events listening.

    You can subclass it to set your own `Protocol` or `Routes` class.
    """
    Protocol = Protocol
    Routes = Routes

    def __init__(self):
        self.routes = self.Routes()
        self.hooks = {}
        options(self)

    async def startup(self):
        await self.hook('startup')

    async def shutdown(self):
        await self.hook('shutdown')

    async def __call__(self, request: Request, response: Response):
        try:
            if not await self.hook('request', request, response):
                params, handler = self.dispatch(request)
                await handler(request, response, **params)
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

    def route(self, path: str, methods: list=None):
        if methods is None:
            methods = ['GET']

        def wrapper(func):
            self.routes.add(path, **{m: func for m in methods})
            return func

        return wrapper

    def dispatch(self, request: Request):
        handlers, params = self.routes.match(request.path)
        if request.method not in handlers:
            raise HttpError(HTTPStatus.METHOD_NOT_ALLOWED)
        request.kwargs.update(params)
        return params, handlers[request.method]

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
