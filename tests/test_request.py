import pytest
from roll import Request

pytestmark = pytest.mark.asyncio


async def test_request_parse_simple_get_response(app):
    req = Request(app)
    req.connection_made(app)
    req.data_received(
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
    assert req.method == 'GET'
    assert req.path == '/feeds'
    assert req.headers['Accept'] == '*/*'


async def test_request_parse_query_string(app):
    req = Request(app)
    req.connection_made(app)
    req.data_received(
        b'GET /feeds?foo=bar&bar=baz HTTP/1.1\r\n'
        b'Host: localhost:1707\r\n'
        b'User-Agent: HTTPie/0.9.8\r\n'
        b'Accept-Encoding: gzip, deflate\r\n'
        b'Accept: */*\r\n'
        b'Connection: keep-alive\r\n'
        b'\r\n')
    assert req.path == '/feeds'
    assert req.query['foo'][0] == 'bar'
    assert req.query['bar'][0] == 'baz'


async def test_request_parse_multivalue_query_string(app):
    req = Request(app)
    req.connection_made(app)
    req.data_received(
        b'GET /feeds?foo=bar&foo=baz HTTP/1.1\r\n'
        b'Host: localhost:1707\r\n'
        b'User-Agent: HTTPie/0.9.8\r\n'
        b'Accept-Encoding: gzip, deflate\r\n'
        b'Accept: */*\r\n'
        b'Connection: keep-alive\r\n'
        b'\r\n')
    assert req.path == '/feeds'
    assert req.query['foo'] == ['bar', 'baz']


async def test_request_parse_POST_body(app):
    req = Request(app)
    req.connection_made(app)
    req.data_received(
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
    assert req.method == 'POST'
    assert req.body == b'{"link": "https://example.org"}'
