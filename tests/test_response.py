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


async def test_raises_a_500_if_code_is_unknown(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = 999

    resp = await client.get('/test')
    assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR


async def test_can_set_status_from_httpstatus(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.ACCEPTED

    resp = await client.get('/test')
    assert resp.status == HTTPStatus.ACCEPTED
    assert client.protocol.transport.data == \
        b'HTTP/1.1 202 Accepted\r\nContent-Length: 0\r\n\r\n'


async def test_write(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.OK
        resp.body = 'body'

    await client.get('/test')
    assert client.protocol.transport.data == \
        b'HTTP/1.1 200 OK\r\nContent-Length: 4\r\n\r\nbody'


async def test_write_get_204_no_content_type(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.NO_CONTENT

    await client.get('/test')
    assert client.protocol.transport.data == b'HTTP/1.1 204 No Content\r\n\r\n'


async def test_write_get_304_no_content_type(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.NOT_MODIFIED

    await client.get('/test')
    assert client.protocol.transport.data == b'HTTP/1.1 304 Not Modified\r\n\r\n'


async def test_write_get_1XX_no_content_type(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.CONTINUE

    await client.get('/test')
    assert client.protocol.transport.data == b'HTTP/1.1 100 Continue\r\n\r\n'


async def test_write_head_no_content_type(client, app):

    @app.route('/test', methods=['HEAD'])
    async def head(req, resp):
        resp.status = HTTPStatus.OK

    await client.head('/test')
    assert client.protocol.transport.data == b'HTTP/1.1 200 OK\r\n\r\n'


async def test_write_cookies(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.OK
        resp.body = 'body'
        resp.cookies.set(name='name', value='value')

    await client.get('/test')
    data = client.protocol.transport.data
    assert b'\r\nSet-Cookie: name=value; Path=/\r\n' in data


async def test_write_multiple_cookies(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.OK
        resp.body = 'body'
        resp.cookies.set('name', 'value')
        resp.cookies.set('other', 'value2')

    await client.get('/test')
    data = client.protocol.transport.data
    assert b'\r\nSet-Cookie: name=value; Path=/\r\n' in data
    assert b'\r\nSet-Cookie: other=value2; Path=/\r\n' in data


async def test_write_cookies_with_path(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.OK
        resp.body = 'body'
        resp.cookies.set('name', 'value', path='/foo')

    await client.get('/test')
    data = client.protocol.transport.data
    assert b'\r\nSet-Cookie: name=value; Path=/foo\r\n' in data


async def test_write_cookies_with_expires(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.OK
        resp.body = 'body'
        resp.cookies.set('name', 'value',
                         expires=datetime(2027, 9, 21, 11, 22))

    await client.get('/test')
    data = client.protocol.transport.data
    assert (b'\r\nSet-Cookie: name=value; '
            b'Expires=Tue, 21 Sep 2027 11:22:00 GMT; Path=/\r\n') in data


async def test_write_cookies_with_max_age(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.OK
        resp.body = 'body'
        resp.cookies.set('name', 'value', max_age=600)

    await client.get('/test')
    data = client.protocol.transport.data
    assert (b'\r\nSet-Cookie: name=value; Max-Age=600; Path=/\r\n') in data


async def test_write_cookies_with_domain(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.OK
        resp.body = 'body'
        resp.cookies.set('name', 'value', domain='www.example.com')

    await client.get('/test')
    data = client.protocol.transport.data
    assert (b'\r\nSet-Cookie: name=value; Domain=www.example.com; '
            b'Path=/\r\n') in data


async def test_write_cookies_with_http_only(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.OK
        resp.body = 'body'
        resp.cookies.set('name', 'value', httponly=True)

    await client.get('/test')
    data = client.protocol.transport.data
    assert (b'\r\nSet-Cookie: name=value; Path=/; HttpOnly\r\n') in data


async def test_write_cookies_with_secure(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.OK
        resp.body = 'body'
        resp.cookies.set('name', 'value', secure=True)

    await client.get('/test')
    data = client.protocol.transport.data
    assert (b'\r\nSet-Cookie: name=value; Path=/; Secure\r\n') in data


async def test_write_cookies_with_multiple_attributes(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.OK
        resp.body = 'body'
        resp.cookies.set('name', 'value', secure=True, max_age=300)

    await client.get('/test')
    data = client.protocol.transport.data
    assert (b'\r\nSet-Cookie: name=value; Max-Age=300; Path=/; '
            b'Secure\r\n') in data


async def test_delete_cookies(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.status = HTTPStatus.OK
        resp.body = 'body'
        resp.cookies.set(name='name', value='value')
        del resp.cookies['name']

    resp = await client.get('/test')
    assert resp.status == HTTPStatus.OK
    data = client.protocol.transport.data
    assert b'\r\nSet-Cookie: name=value\r\n' not in data


async def test_write_chunks(client, app):

    async def mygen():
        for i in range(3):
            yield ("chunk" + str(i)).encode()

    @app.route('/test')
    async def head(req, resp):
        resp.body = mygen()

    await client.get('/test')
    assert client.protocol.transport.data == (
        b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n6\r\nchunk0"
        b"\r\n6\r\nchunk1\r\n6\r\nchunk2\r\n0\r\n\r\n")


async def test_write_non_bytes_chunks(client, app):

    async def mygen():
        for i in range(3):
            yield i

    @app.route('/test')
    async def head(req, resp):
        resp.body = mygen()

    await client.get('/test')
    assert client.protocol.transport.data == (
        b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n1\r\n0\r\n1'
        b'\r\n1\r\n1\r\n2\r\n0\r\n\r\n')


async def test_set_redirect(client, app):

    @app.route('/test')
    async def get(req, resp):
        resp.redirect = "https://example.org", 307

    resp = await client.get('/test')
    assert resp.status == 307
    assert resp.headers["Location"] == "https://example.org"
