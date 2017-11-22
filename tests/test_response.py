from datetime import datetime
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
        b'HTTP/1.1 202 Accepted\r\nContent-Length: 0\r\n\r\n'


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
    assert client.protocol.writer.data == b'HTTP/1.1 204 No Content\r\n\r\n'


async def test_write_get_304_no_content_type(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.NOT_MODIFIED

    await client.get('/test')
    assert client.protocol.writer.data == b'HTTP/1.1 304 Not Modified\r\n\r\n'


async def test_write_get_1XX_no_content_type(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.CONTINUE

    await client.get('/test')
    assert client.protocol.writer.data == b'HTTP/1.1 100 Continue\r\n\r\n'


async def test_write_head_no_content_type(client, app):

    @app.route('/test', methods=['HEAD'])
    async def head(req, resp):
        resp.status = HTTPStatus.OK

    await client.head('/test')
    assert client.protocol.writer.data == b'HTTP/1.1 200 OK\r\n\r\n'


async def test_write_connect_no_content_type(client, app):

    @app.route('/test', methods=['CONNECT'])
    async def connect(req, resp):
        resp.status = HTTPStatus.OK

    await client.connect('/test')
    assert client.protocol.writer.data == b'HTTP/1.1 200 OK\r\n\r\n'


async def test_write_cookies(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.OK
        resp.body = 'body'
        resp.cookies.set(name='name', value='value')

    await client.get('/test')
    data = client.protocol.writer.data
    assert b'\r\nSet-Cookie: name=value\r\n' in data


async def test_write_multiple_cookies(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.OK
        resp.body = 'body'
        resp.cookies.set('name', 'value')
        resp.cookies.set('other', 'value2')

    await client.get('/test')
    data = client.protocol.writer.data
    assert b'\r\nSet-Cookie: name=value\r\n' in data
    assert b'\r\nSet-Cookie: other=value2\r\n' in data


async def test_write_cookies_with_path(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.OK
        resp.body = 'body'
        resp.cookies.set('name', 'value', path='/foo')

    await client.get('/test')
    data = client.protocol.writer.data
    assert b'\r\nSet-Cookie: name=value; Path=/foo\r\n' in data


async def test_write_cookies_with_expires(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.OK
        resp.body = 'body'
        resp.cookies.set('name', 'value',
                         expires=datetime(2027, 9, 21, 11, 22))

    await client.get('/test')
    data = client.protocol.writer.data
    assert (b'\r\nSet-Cookie: name=value; '
            b'Expires=Tue, 21 Sep 2027 11:22:00 GMT\r\n') in data


async def test_write_cookies_with_max_age(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.OK
        resp.body = 'body'
        resp.cookies.set('name', 'value', max_age=600)

    await client.get('/test')
    data = client.protocol.writer.data
    assert (b'\r\nSet-Cookie: name=value; Max-Age=600\r\n') in data


async def test_write_cookies_with_domain(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.OK
        resp.body = 'body'
        resp.cookies.set('name', 'value', domain='www.example.com')

    await client.get('/test')
    data = client.protocol.writer.data
    assert (b'\r\nSet-Cookie: name=value; Domain=www.example.com\r\n') in data


async def test_write_cookies_with_http_only(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.OK
        resp.body = 'body'
        resp.cookies.set('name', 'value', httponly=True)

    await client.get('/test')
    data = client.protocol.writer.data
    assert (b'\r\nSet-Cookie: name=value; HttpOnly\r\n') in data


async def test_write_cookies_with_secure(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.OK
        resp.body = 'body'
        resp.cookies.set('name', 'value', secure=True)

    await client.get('/test')
    data = client.protocol.writer.data
    assert (b'\r\nSet-Cookie: name=value; Secure\r\n') in data


async def test_write_cookies_with_multiple_attributes(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.OK
        resp.body = 'body'
        resp.cookies.set('name', 'value', secure=True, max_age=300)

    await client.get('/test')
    data = client.protocol.writer.data
    assert (b'\r\nSet-Cookie: name=value; Max-Age=300; Secure\r\n') in data


async def test_delete_cookies(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.OK
        resp.body = 'body'
        resp.cookies.set(name='name', value='value')
        del resp.cookies['name']

    await client.get('/test')
    data = client.protocol.writer.data
    assert b'\r\nSet-Cookie: name=value\r\n' not in data
