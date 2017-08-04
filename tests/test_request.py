import pytest
from roll import Request

pytestmark = pytest.mark.asyncio


async def test_request_parse_simple_get_response(app):
    req = Request(app)
    req.connection_made(app)
    req.data_received(b'GET /feeds HTTP/1.1\r\nHost: localhost:1707\r\nUser-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:54.0) Gecko/20100101 Firefox/54.0\r\nAccept: */*\r\nAccept-Language: en-US,en;q=0.5\r\nAccept-Encoding: gzip, deflate\r\nOrigin: http://localhost:7777\r\nReferer: http://localhost:7777/\r\nDNT: 1\r\nConnection: keep-alive\r\n\r\n')  # noqa
    assert req.method == 'GET'
    assert req.path == '/feeds'
    assert req.headers['Accept'] == '*/*'


async def test_request_parse_query_string(app):
    req = Request(app)
    req.connection_made(app)
    req.data_received(b'GET /feeds?foo=bar&bar=baz HTTP/1.1\r\nHost: localhost:1707\r\nUser-Agent: HTTPie/0.9.8\r\nAccept-Encoding: gzip, deflate\r\nAccept: */*\r\nConnection: keep-alive\r\n\r\n')  # noqa
    assert req.path == '/feeds'
    assert req.query['foo'][0] == 'bar'
    assert req.query['bar'][0] == 'baz'


async def test_request_parse_multivalue_query_string(app):
    req = Request(app)
    req.connection_made(app)
    req.data_received(b'GET /feeds?foo=bar&foo=baz HTTP/1.1\r\nHost: localhost:1707\r\nUser-Agent: HTTPie/0.9.8\r\nAccept-Encoding: gzip, deflate\r\nAccept: */*\r\nConnection: keep-alive\r\n\r\n')  # noqa
    assert req.path == '/feeds'
    assert req.query['foo'] == ['bar', 'baz']


async def test_request_parse_POST_body(app):
    req = Request(app)
    req.connection_made(app)
    req.data_received(b'POST /feed HTTP/1.1\r\nHost: localhost:1707\r\nUser-Agent: HTTPie/0.9.8\r\nAccept-Encoding: gzip, deflate\r\nAccept: application/json, */*\r\nConnection: keep-alive\r\nContent-Type: application/json\r\nContent-Length: 58\r\n\r\n{"link": "https://www.bastamag.net/spip.php?page=backend"}')  # noqa
    assert req.method == 'POST'
    assert req.body == b'{"link": "https://www.bastamag.net/spip.php?page=backend"}'  # noqa
