from http import HTTPStatus

import pytest

pytestmark = pytest.mark.asyncio


async def test_can_set_status_from_numeric_value(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = 202

    resp = await client.get('/test')
    assert resp.status == HTTPStatus.ACCEPTED


async def test_can_set_status_from_httpstatus(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.ACCEPTED

    resp = await client.get('/test')
    assert resp.status == HTTPStatus.ACCEPTED
    assert client.protocol.writer.data == \
        b'HTTP/1.1 202 Accepted\r\nContent-Length: 0\r\n'


async def test_write(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.OK
        resp.body = 'body'

    await client.get('/test')
    assert client.protocol.writer.data == \
        b'HTTP/1.1 200 OK\r\nContent-Length: 4\r\n\r\nbody'


async def test_write_get_204_no_content_type(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.NO_CONTENT

    await client.get('/test')
    assert client.protocol.writer.data == b'HTTP/1.1 204 No Content\r\n'


async def test_write_get_304_no_content_type(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.NOT_MODIFIED

    await client.get('/test')
    assert client.protocol.writer.data == b'HTTP/1.1 304 Not Modified\r\n'


async def test_write_get_1XX_no_content_type(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.CONTINUE

    await client.get('/test')
    assert client.protocol.writer.data == b'HTTP/1.1 100 Continue\r\n'


async def test_write_head_no_content_type(client, app):

    @app.route('/test', methods=['HEAD'])
    async def head(req, resp):
        resp.status = HTTPStatus.OK

    await client.head('/test')
    assert client.protocol.writer.data == b'HTTP/1.1 200 OK\r\n'


async def test_write_connect_no_content_type(client, app):

    @app.route('/test', methods=['CONNECT'])
    async def connect(req, resp):
        resp.status = HTTPStatus.OK

    await client.connect('/test')
    assert client.protocol.writer.data == b'HTTP/1.1 200 OK\r\n'


async def test_write_set_cookie(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.OK
        resp.body = 'body'
        resp.headers['Set-Cookie'] = 'name=value'

    await client.get('/test')
    data = client.protocol.writer.data
    assert b'\r\nSet-Cookie: name=value\r\n' in data
    assert b'\r\nContent-Length: 4\r\n' in data
    assert b'\r\n\r\nbody' in data


async def test_write_multiple_set_cookie(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.OK
        resp.body = 'body'
        resp.headers['Set-Cookie'] = ['name=value', 'other=value2']

    await client.get('/test')
    data = client.protocol.writer.data
    assert b'\r\nSet-Cookie: name=value\r\n' in data
    assert b'\r\nSet-Cookie: other=value2\r\n' in data
    assert b'\r\nContent-Length: 4\r\n' in data
    assert b'\r\n\r\nbody' in data
