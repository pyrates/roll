import json
from urllib.parse import urlencode

import pytest

from . import Protocol


class Client:

    # Default content type for request body encoding, change it to your own
    # taste if needed.
    content_type = 'application/json'

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
        protocol = self.app.factory()
        protocol.on_message_begin()
        protocol.on_url(path.encode())
        protocol.req.body = body
        protocol.req.method = method
        protocol.req.headers = headers
        return await self.app(protocol.req, protocol.resp)

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


@pytest.fixture
def client(app, event_loop):
    app.loop = event_loop
    app.loop.run_until_complete(app.startup())
    yield Client(app)
    app.loop.run_until_complete(app.shutdown())


# Retrocompat, remove me.
@pytest.fixture
def req(client):
    return client.request
