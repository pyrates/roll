import pytest
from roll import Protocol, HttpError

pytestmark = pytest.mark.asyncio


class Transport:

    def write(self, data):
        ...

    def close(self):
        ...


@pytest.fixture
def protocol(app):
    protocol = Protocol(app)
    protocol.connection_made(Transport())
    return protocol


async def test_request_parse_simple_get_response(protocol):
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


async def test_request_parse_query_string(protocol):
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


async def test_request_parse_multivalue_query_string(protocol):
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


async def test_request_parse_POST_body(protocol):
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


async def test_invalid_request(protocol):
    protocol.data_received(
        b'INVALID HTTP/1.22\r\n')
    assert protocol.resp.status == b'400 Bad Request'


async def test_query_get_should_return_value(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=value')
    assert protocol.req.query.get('key') == 'value'


async def test_query_get_should_return_first_value_if_multiple(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=value&key=value2')
    assert protocol.req.query.get('key') == 'value'


async def test_query_getlist_should_return_list_of_values(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=value&key=value2')
    assert protocol.req.query.get_list('key') == ['value', 'value2']


async def test_query_get_should_return_default_if_key_is_missing(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=value')
    assert protocol.req.query.get('other') is None
    assert protocol.req.query.get('other', 'default') == 'default'


@pytest.mark.parametrize('input,expected', [
    (b'true', True),
    (b'1', True),
    (b'on', True),
    (b'false', False),
    (b'0', False),
    (b'off', False),
])
async def test_query_bool_should_cast_to_boolean(input, expected, protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=' + input)
    assert protocol.req.query.bool('key') == expected


async def test_query_bool_should_return_default(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=1')
    assert protocol.req.query.bool('other', default=False) is False


async def test_query_bool_should_raise_if_not_castable(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=one')
    with pytest.raises(HttpError):
        assert protocol.req.query.bool('key')


async def test_query_bool_should_raise_if_not_key_and_no_default(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=one')
    with pytest.raises(HttpError):
        assert protocol.req.query.bool('other')


async def test_query_bool_should_return_default_if_key_not_present(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=one')
    assert protocol.req.query.bool('other', default=False) is False


async def test_query_int_should_cast_to_int(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=22')
    assert protocol.req.query.int('key') == 22


async def test_query_int_should_return_default(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=1')
    assert protocol.req.query.int('other', default=22) == 22


async def test_query_int_should_raise_if_not_castable(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=one')
    with pytest.raises(HttpError):
        assert protocol.req.query.int('key')


async def test_query_int_should_raise_if_not_key_and_no_default(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=one')
    with pytest.raises(HttpError):
        assert protocol.req.query.int('other')


async def test_query_int_should_return_default_if_key_not_present(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=one')
    assert protocol.req.query.int('other', default=22) == 22


async def test_query_float_should_cast_to_float(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=2.234')
    assert protocol.req.query.float('key') == 2.234


async def test_query_float_should_return_default(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=1')
    assert protocol.req.query.float('other', default=2.234) == 2.234


async def test_query_float_should_raise_if_not_castable(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=one')
    with pytest.raises(HttpError):
        assert protocol.req.query.float('key')


async def test_query_float_should_raise_if_not_key_and_no_default(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=one')
    with pytest.raises(HttpError):
        assert protocol.req.query.float('other')


async def test_query_float_should_return_default_if_key_not_present(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=one')
    assert protocol.req.query.float('other', default=2.234) == 2.234
