import asyncio
from http import HTTPStatus
from urllib.parse import parse_qs

from httptools import HttpRequestParser, parse_url, HttpParserError
from kua.routes import RouteError, Routes

from .extensions import options

try:
    import ujson as json
except ImportError:
    import json as json


class HttpError(Exception):

    __slots__ = ('status', 'message')

    def __init__(self, code, message=None):
        self.status = HTTPStatus(code)
        self.message = message or self.status.phrase


class Protocol(asyncio.Protocol):

    __slots__ = ('app', 'req', 'parser', 'resp', 'writer')

    def __init__(self, app):
        self.app = app
        self.parser = HttpRequestParser(self)

    def data_received(self, data: bytes):
        try:
            self.parser.feed_data(data)
        except HttpParserError:
            # If the parsing failed before on_message_begin, we don't have a
            # response.
            self.resp = Response()
            self.resp.status = HTTPStatus.BAD_REQUEST
            self.resp.body = b'Unparsable request'
            self.write()

    def connection_made(self, transport):
        self.writer = transport

    # All on_xxx methods are in use by httptools parser.
    # See https://github.com/MagicStack/httptools#apis
    def on_header(self, name: bytes, value: bytes):
        self.req.headers[name.decode()] = value.decode()

    def on_body(self, body: bytes):
        self.req.body += body

    def on_url(self, url: bytes):
        parsed = parse_url(url)
        self.req.path = parsed.path.decode()
        self.req.query_string = (parsed.query or b'').decode()
        self.req.query = Query(
            parse_qs(self.req.query_string, keep_blank_values=True))

    def on_message_begin(self):
        self.req = Request()
        self.resp = Response()

    def on_message_complete(self):
        self.req.method = self.parser.get_method().decode().upper()
        task = self.app.loop.create_task(self.app(self.req, self.resp))
        task.add_done_callback(self.write)

    def write(self, *args):
        # May or may not have "future" as arg.
        self.writer.write(b'HTTP/1.1 %b\r\n' % self.resp.status)
        if not isinstance(self.resp.body, bytes):
            self.resp.body = self.resp.body.encode()
        if 'Content-Length' not in self.resp.headers:
            length = len(self.resp.body)
            self.resp.headers['Content-Length'] = str(length)
        for key, value in self.resp.headers.items():
            self.writer.write(b'%b: %b\r\n' % (key.encode(),
                                               str(value).encode()))
        self.writer.write(b'\r\n')
        self.writer.write(self.resp.body)
        if not self.parser.should_keep_alive():
            self.writer.close()


class Query(dict):

    TRUE_STRINGS = ('true', 'True', 'yes', '1', 'on')
    FALSE_STRINGS = ('false', 'False', 'no', '0', 'off')
    NONE_STRINGS = ('none', 'None', 'null', 'NULL', '')

    def get(self, key, default=None):
        return super().get(key, [default])[0]

    def get_list(self, key, default=None):
        return super().get(key, default)

    def bool(self, key, default=...):
        if key in self:
            value = self.get(key)
            if value in self.TRUE_STRINGS:
                return True
            elif value in self.FALSE_STRINGS:
                return False
            elif value in self.NONE_STRINGS:
                return None
            raise HttpError(
                HTTPStatus.BAD_REQUEST,
                'Wrong boolean value for {}={}'.format(key, self.get(key)))
        if default is ...:
            raise HttpError(HTTPStatus.BAD_REQUEST,
                            'Missing {} key'.format(key))
        return default

    def int(self, key, default=...):
        try:
            value = int(self.get(key))
        except TypeError:
            if default is ...:
                raise HttpError(
                    HTTPStatus.BAD_REQUEST,
                    'Key {} must be present and castable to int'.format(key))
            return default
        except ValueError:
            if default is ...:
                raise HttpError(HTTPStatus.BAD_REQUEST,
                                'Key {} must be castable to int'.format(key))
            return default
        return value

    def float(self, key, default=...):
        try:
            value = float(self.get(key))
        except TypeError:
            if default is ...:
                raise HttpError(
                    HTTPStatus.BAD_REQUEST,
                    'Key {} must be present and castable to float'.format(key))
            return default
        except ValueError:
            if default is ...:
                raise HttpError(HTTPStatus.BAD_REQUEST,
                                'Key {} must be castable to float'.format(key))
            return default
        return value


class Request:

    __slots__ = ('path', 'query_string', 'query', 'method', 'kwargs',
                 'body', 'headers')

    def __init__(self):
        self.kwargs = {}
        self.headers = {}
        self.body = b''


class Response:

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
    def status(self, code):
        status_ = HTTPStatus(code)
        self._status = '{} {}'.format(status_.value, status_.phrase).encode()

    def json(self, value):
        self.headers['Content-Type'] = 'application/json'
        self.body = json.dumps(value)

    json = property(None, json)


class Roll:

    def __init__(self):
        self.routes = Routes()
        self.hooks = {}
        options(self)

    async def startup(self):
        await self.hook('startup')

    async def shutdown(self):
        await self.hook('shutdown')

    async def __call__(self, req, resp):
        try:
            if not await self.hook('request', request=req, response=resp):
                params, handler = self.dispatch(req)
                await handler(req, resp, **params)
        except Exception as error:
            await self.on_error(error, resp)
        try:
            # Views exceptions should still pass by the response hooks.
            await self.hook('response', response=resp, request=req)
        except Exception as error:
            await self.on_error(error, resp)
        return resp

    async def on_error(self, error, response):
        if not isinstance(error, HttpError):
            error = HttpError(HTTPStatus.INTERNAL_SERVER_ERROR,
                              str(error).encode())
        response.status = error.status
        response.body = error.message
        try:
            await self.hook('error', error=error, response=response)
        except Exception as error:
            response.status = HTTPStatus.INTERNAL_SERVER_ERROR
            response.body = str(error)

    def factory(self):
        return Protocol(self)

    def route(self, path, methods=None):
        if methods is None:
            methods = ['GET']

        def wrapper(func):
            self.routes.add(path, {m: func for m in methods})
            return func

        return wrapper

    def dispatch(self, req):
        try:
            params, handlers = self.routes.match(req.path)
        except RouteError:
            raise HttpError(HTTPStatus.NOT_FOUND, req.path)
        if req.method not in handlers:
            raise HttpError(HTTPStatus.METHOD_NOT_ALLOWED)
        req.kwargs.update(params)
        return params, handlers[req.method]

    def listen(self, name):
        def wrapper(func):
            self.hooks.setdefault(name, [])
            self.hooks[name].append(func)
        return wrapper

    async def hook(self, name, **kwargs):
        try:
            for func in self.hooks[name]:
                result = await func(**kwargs)
                if result:
                    return result
        except KeyError:
            # Nobody registered to this event, let's roll anyway.
            pass
