import json
from urllib.parse import urlencode

import pytest


class Transport:

    def __init__(self):
        self.data = b''

    def write(self, data):
        self.data += data

    def close(self):
        ...


class Client:

    # Default content type for request body encoding, change it to your own
    # taste if needed.
    content_type = 'application/json; charset=utf-8'

    def __init__(self, app):
        self.app = app

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
            elif 'application/json' in headers['Content-Type']:
                body = json.dumps(body)
            else:
                raise NotImplementedError('Content-Type not supported')
        return body, headers

    async def request(self, path, method='GET', body=b'', headers=None,
                      content_type=None):
        headers = headers or {}
        if content_type:
            headers['Content-Type'] = content_type
        body, headers = self.encode_body(body, headers)
        self.protocol = self.app.factory()
        self.protocol.connection_made(Transport())
        self.protocol.on_message_begin()
        self.protocol.on_url(path.encode())
        self.protocol.request.body = body
        self.protocol.request.method = method
        for key, value in headers.items():
            self.protocol.on_header(key.encode(), value.encode())
        await self.app(self.protocol.request, self.protocol.response)
        self.protocol.write()
        return self.protocol.response

    async def get(self, path, **kwargs):
        return await self.request(path, method='GET', **kwargs)

    async def head(self, path, **kwargs):
        return await self.request(path, method='HEAD', **kwargs)

    async def post(self, path, body, **kwargs):
        return await self.request(path, method='POST', body=body, **kwargs)

    async def put(self, path, body, **kwargs):
        return await self.request(path, method='PUT', body=body, **kwargs)

    async def patch(self, path, body, **kwargs):
        return await self.request(path, method='PATCH', body=body, **kwargs)

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
