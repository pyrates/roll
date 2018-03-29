
import http
import json
import mimetypes
import pytest
import socket

from functools import partial
from io import BytesIO
from urllib.parse import urlencode
from uuid import uuid4


def encode_multipart(data, charset='utf-8'):
    # Ported from Werkzeug testing.
    boundary = '---------------Boundary%s' % uuid4().hex
    body = BytesIO()

    def write(string):
        body.write(string.encode(charset))

    if isinstance(data, dict):
        data = data.items()

    for key, values in data:
        if not isinstance(values, (list, tuple)):
            values = [values]
        for value in values:
            write('--%s\r\nContent-Disposition: form-data; name="%s"' %
                  (boundary, key))
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
                    write('; filename="%s"\r\n' % filename)
                else:
                    write('\r\n')
                write('Content-Type: %s\r\n\r\n' % content_type)
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
    write('--%s--\r\n' % boundary)

    body.seek(0)
    content_type = 'multipart/form-data; boundary=%s' % boundary
    return body.read(), content_type


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


class Client:

    # Default content type for request body encoding, change it to your own
    # taste if needed.
    content_type = 'application/json; charset=utf-8'

    def __init__(self, app, event_loop):
        self.app = app
        self.loop = event_loop

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
        if content_type:
            headers['Content-Type'] = content_type
        body, headers = self.encode_body(body, headers)
        if isinstance(body, str):
            body = body.encode()
        self.protocol = self.app.factory()
        self.protocol.connection_made(Transport())
        self.protocol.on_message_begin()
        self.protocol.on_url(path.encode())
        self.protocol.request.body = body
        self.protocol.request.method = method
        for key, value in headers.items():
            self.protocol.on_header(key.encode(), value.encode())
        self.protocol.on_headers_complete()
        await self.protocol.run()
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
    yield Client(app, event_loop)
    app.loop.run_until_complete(app.shutdown())


def unused_port():
    """Return a port that is unused on the current host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class LiveClient:

    def __init__(self, app, loop):
        self.app = app
        self.loop = loop
        self.url = None
        self.wsl = None

    def start(self):
        self.port = unused_port()
        self.app.loop.run_until_complete(self.app.startup())
        self.server = self.app.loop.run_until_complete(
            self.loop.create_server(self.app.factory, '127.0.0.1', self.port))
        self.url = 'http://127.0.0.1:{port}'.format(port=self.port)
        self.wsl = 'ws://127.0.0.1:{port}'.format(port=self.port)

    def stop(self):
        self.server.close()
        self.port = self.url = self.wsl = None
        self.app.loop.run_until_complete(self.server.wait_closed())
        self.app.loop.run_until_complete(self.app.shutdown())

    def execute_query(self, method, uri, headers):
        self.conn.request(method, uri, headers=headers)
        response = self.conn.getresponse()
        return response

    async def query(self, method, uri, headers: dict=None):
        if headers is None:
            headers = {}

        requester = partial(self.execute_query, method.upper(), uri, headers)
        response = await self.loop.run_in_executor(None, requester)
        return response

    def __enter__(self):
        assert self.url is not None
        self.conn = http.client.HTTPConnection('127.0.0.1', self.port)
        return self.query

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()


@pytest.fixture()
def liveclient(app, event_loop):
    app.loop = event_loop
    client = LiveClient(app, loop=event_loop)
    client.start()
    yield client
    client.stop()
