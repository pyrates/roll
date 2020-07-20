import http.client
import json
import mimetypes
from functools import partial
from http import HTTPStatus
from io import BytesIO
from urllib.parse import urlencode, quote, urlparse, parse_qsl
from uuid import uuid4

import pytest


def encode_multipart(data, charset='utf-8'):
    # Ported from Werkzeug testing.
    boundary = f'---------------Boundary{uuid4().hex}'
    body = BytesIO()

    def write(string):
        body.write(string.encode(charset))

    if isinstance(data, dict):
        data = data.items()

    for key, values in data:
        if not isinstance(values, (list, tuple)):
            values = [values]
        for value in values:
            write(f'--{boundary}\r\n'
                  f'Content-Disposition: form-data; name="{key}"')
            reader = getattr(value, 'read', None)
            if reader is not None:
                filename = getattr(value, 'filename',
                                   getattr(value, 'name', None))
                content_type = getattr(value, 'content_type', None)
                if content_type is None:
                    content_type = filename and \
                        mimetypes.guess_type(filename)[0] or \
                        'application/octet-stream'
                if filename is not None:
                    write(f'; filename="{filename}"\r\n')
                else:
                    write('\r\n')
                write(f'Content-Type: {content_type}\r\n\r\n')
                while 1:
                    chunk = reader(16384)
                    if not chunk:
                        break
                    body.write(chunk)
            else:
                if not isinstance(value, str):
                    value = str(value)
                else:
                    value = value.encode(charset)
                write('\r\n\r\n')
                body.write(value)
            write('\r\n')
    write(f'--{boundary}--\r\n')

    body.seek(0)
    content_type = f'multipart/form-data; boundary={boundary}'
    return body.read(), content_type


def encode_path(path):
    parsed = urlparse(path)
    out = quote(parsed.path)
    if parsed.query:
        query = parse_qsl(parsed.query, keep_blank_values=True)
        out += "?" + "&".join(f"{k}={quote(v)}" for k, v in query)
    return out.encode()


class Transport:

    def __init__(self):
        self.data = b''
        self._closing = False

    def is_closing(self):
        return self._closing

    def write(self, data):
        self.data += data

    def close(self):
        self._closing = True

    def pause_reading(self):
        pass

    def resume_reading(self):
        pass


class Client:

    # Default content type for request body encoding, change it to your own
    # taste if needed.
    content_type = 'application/json; charset=utf-8'
    # Default headers to use eg. for patching Auth in tests.
    default_headers = {}

    def __init__(self, app):
        self.app = app

    def handle_files(self, kwargs):
        kwargs.setdefault('headers', {})
        files = kwargs.pop('files', None)
        if files:
            kwargs['headers']['Content-Type'] = 'multipart/form-data'
            if isinstance(files, dict):
                files = files.items()
            for key, els in files:
                if not els:
                    continue
                if not isinstance(els, (list, tuple)):
                    # Allow passing a file instance.
                    els = [els]
                file_ = els[0]
                if isinstance(file_, str):
                    file_ = file_.encode()
                if isinstance(file_, bytes):
                    file_ = BytesIO(file_)
                if len(els) > 1:
                    file_.name = els[1]
                if len(els) > 2:
                    file_.charset = els[2]
                kwargs['body'][key] = file_

    def encode_body(self, body, headers):
        content_type = headers.get('Content-Type')
        if not body or isinstance(body, (str, bytes)):
            return body, headers
        if not content_type:
            if self.content_type:
                headers['Content-Type'] = content_type = self.content_type
        if content_type:
            if 'application/x-www-form-urlencoded' in content_type:
                body = urlencode(body)
            elif 'application/json' in content_type:
                body = json.dumps(body)
            elif 'multipart/form-data' in content_type:
                body, headers['Content-Type'] = encode_multipart(body)
            else:
                raise NotImplementedError('Content-Type not supported')
        return body, headers

    async def request(self, path, method='GET', body=b'', headers=None,
                      content_type=None):
        headers = headers or {}
        for key, value in self.default_headers.items():
            headers.setdefault(key, value)
        if content_type:
            headers['Content-Type'] = content_type
        body, headers = self.encode_body(body, headers)
        if isinstance(body, str):
            body = body.encode()
        if body and 'Content-Length' not in headers:
            headers['Content-Length'] = len(body)
        self.protocol = self.app.factory()
        self.protocol.connection_made(Transport())
        headers = '\r\n'.join(f'{k}: {v}' for k, v in headers.items())
        data = b'%b %b HTTP/1.1\r\n%b\r\n\r\n%b' % (
            method.encode(), encode_path(path), headers.encode(), body or b'')

        self.protocol.data_received(data)
        if self.protocol.task:
            await self.protocol.task
        return self.protocol.response

    async def get(self, path, **kwargs):
        return await self.request(path, method='GET', **kwargs)

    async def head(self, path, **kwargs):
        return await self.request(path, method='HEAD', **kwargs)

    async def post(self, path, data=None, **kwargs):
        kwargs.setdefault('body', data or {})
        self.handle_files(kwargs)
        return await self.request(path, method='POST', **kwargs)

    async def put(self, path, data=None, **kwargs):
        kwargs.setdefault('body', data or {})
        self.handle_files(kwargs)
        return await self.request(path, method='PUT', **kwargs)

    async def patch(self, path, data=None, **kwargs):
        kwargs.setdefault('body', data or {})
        self.handle_files(kwargs)
        return await self.request(path, method='PATCH', **kwargs)

    async def delete(self, path, **kwargs):
        return await self.request(path, method='DELETE', **kwargs)

    async def options(self, path, **kwargs):
        return await self.request(path, method='OPTIONS', **kwargs)

    async def connect(self, path, **kwargs):
        return await self.request(path, method='CONNECT', **kwargs)


@pytest.fixture
def client(app, event_loop):
    app.loop = event_loop
    app.loop.run_until_complete(app.startup())
    yield Client(app)
    app.loop.run_until_complete(app.shutdown())


def read_chunked_body(response):

    def chunk_size():
        size_str = response.read(2)
        while size_str[-2:] != b"\r\n":
            size_str += response.read(1)
        return int(size_str[:-2], 16)

    def chunk_data(chunk_size):
        data = response.read(chunk_size)
        response.read(2)
        return data

    while True:
        size = chunk_size()
        if (size == 0):
            break
        else:
            yield chunk_data(size)


class LiveResponse:

    def __init__(self, status: int, reason: str):
        self.status = HTTPStatus(status)
        self.reason = reason
        self.body = b''
        self.chunks = None

    def write(self, data):
        self.body += data

    def write_chunk(self, data):
        self.body += data
        if self.chunks is None:
            self.chunks = []
        self.chunks.append(data)

    @classmethod
    def from_query(cls, result):
        response = cls(result.status, result.reason)
        if result.chunked:
            result.chunked = False
            for data in read_chunked_body(result):
                response.write_chunk(data)
        else:
            response.write(result.read())
        return response


class LiveClient:

    def __init__(self, app):
        self.app = app
        self.url = None
        self.wsl = None

    def start(self):
        self.app.loop.run_until_complete(self.app.startup())
        self.server = self.app.loop.run_until_complete(
            self.app.loop.create_server(self.app.factory, '127.0.0.1', 0))
        self.port = self.server.sockets[0].getsockname()[1]
        self.url = f'http://127.0.0.1:{self.port}'
        self.wsl = f'ws://127.0.0.1:{self.port}'

    def stop(self):
        self.server.close()
        self.port = self.url = self.wsl = None
        self.app.loop.run_until_complete(self.server.wait_closed())
        self.app.loop.run_until_complete(self.app.shutdown())

    def execute_query(self, method, uri, headers, body=None):
        self.conn.request(method, uri, headers=headers, body=body)
        result = self.conn.getresponse()
        return LiveResponse.from_query(result)

    async def query(self, method, uri, headers: dict=None, body=None):
        if headers is None:
            headers = {}

        self.conn = http.client.HTTPConnection('127.0.0.1', self.port)
        requester = partial(
            self.execute_query, method.upper(), uri, headers, body)
        response = await self.app.loop.run_in_executor(None, requester)
        self.conn.close()
        return response


@pytest.fixture
def liveclient(app, event_loop):
    app.loop = event_loop
    client = LiveClient(app)
    client.start()
    yield client
    client.stop()
