import pytest
from roll import Protocol

pytestmark = pytest.mark.asyncio


class Transport:

    def write(self, data):
        ...

    def close(self):
        ...


async def test_request_parse_simple_get_response(app):
    protocol = Protocol(app)
    protocol.connection_made(Transport())
    protocol.data_received(
        b'GET /feeds HTTP/1.1\r\n'
        b'Host: localhost:1707\r\n'
        b'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:54.0) '
        b'Gecko/20100101 Firefox/54.0\r\n'
        b'Accept: */*\r\n'
        b'Accept-Language: en-US,en;q=0.5\r\n'
        b'Accept-Encoding: gzip, deflate\r\n'
        b'Origin: http://localhost:7777\r\n'
        b'Referer: http://localhost:7777/\r\n'
        b'DNT: 1\r\n'
        b'Connection: keep-alive\r\n'
        b'\r\n')
    assert protocol.req.method == 'GET'
    assert protocol.req.path == '/feeds'
    assert protocol.req.headers['Accept'] == '*/*'


async def test_request_parse_query_string(app):
    protocol = Protocol(app)
    protocol.connection_made(Transport())
    protocol.data_received(
        b'GET /feeds?foo=bar&bar=baz HTTP/1.1\r\n'
        b'Host: localhost:1707\r\n'
        b'User-Agent: HTTPie/0.9.8\r\n'
        b'Accept-Encoding: gzip, deflate\r\n'
        b'Accept: */*\r\n'
        b'Connection: keep-alive\r\n'
        b'\r\n')
    assert protocol.req.path == '/feeds'
    assert protocol.req.query['foo'][0] == 'bar'
    assert protocol.req.query['bar'][0] == 'baz'


async def test_request_parse_multivalue_query_string(app):
    protocol = Protocol(app)
    protocol.connection_made(Transport())
    protocol.data_received(
        b'GET /feeds?foo=bar&foo=baz HTTP/1.1\r\n'
        b'Host: localhost:1707\r\n'
        b'User-Agent: HTTPie/0.9.8\r\n'
        b'Accept-Encoding: gzip, deflate\r\n'
        b'Accept: */*\r\n'
        b'Connection: keep-alive\r\n'
        b'\r\n')
    assert protocol.req.path == '/feeds'
    assert protocol.req.query['foo'] == ['bar', 'baz']


async def test_request_parse_POST_body(app):
    protocol = Protocol(app)
    protocol.connection_made(Transport())
    protocol.data_received(
        b'POST /feed HTTP/1.1\r\n'
        b'Host: localhost:1707\r\n'
        b'User-Agent: HTTPie/0.9.8\r\n'
        b'Accept-Encoding: gzip, deflate\r\n'
        b'Accept: application/json, */*\r\n'
        b'Connection: keep-alive\r\n'
        b'Content-Type: application/json\r\n'
        b'Content-Length: 31\r\n'
        b'\r\n'
        b'{"link": "https://example.org"}')
    assert protocol.req.method == 'POST'
    assert protocol.req.body == b'{"link": "https://example.org"}'


async def test_invalid_request(app):
    protocol = Protocol(app)
    protocol.connection_made(Transport())
    protocol.data_received(
        b'INVALID HTTP/1.22\r\n')
    assert protocol.resp.status == b'400 Bad Request'
