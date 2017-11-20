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


async def test_write(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.OK
        resp.body = 'body'

    await client.get('/test')
    assert client.protocol.writer.data == \
        b'HTTP/1.1 200 OK\r\nContent-Length: 4\r\n\r\nbody'


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
