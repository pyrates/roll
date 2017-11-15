from http import HTTPStatus

import pytest
from roll import Protocol, HttpError, Request
from roll.testing import Transport

pytestmark = pytest.mark.asyncio


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
    assert protocol.request.method == 'GET'
    assert protocol.request.path == '/feeds'
    assert protocol.request.headers['ACCEPT'] == '*/*'


async def test_request_headers_are_uppercased(protocol):
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
    assert protocol.request.headers['ACCEPT-LANGUAGE'] == 'en-US,en;q=0.5'
    assert protocol.request.headers['ACCEPT'] == '*/*'
    assert protocol.request.headers.get('HOST') == 'localhost:1707'
    assert 'DNT' in protocol.request.headers
    assert protocol.request.headers.get('accept') is None


async def test_request_path_is_unquoted(protocol):
    protocol.data_received(
        b'GET /foo%2Bbar HTTP/1.1\r\n'
        b'Host: localhost:1707\r\n'
        b'User-Agent: HTTPie/0.9.8\r\n'
        b'Accept-Encoding: gzip, deflate\r\n'
        b'Accept: */*\r\n'
        b'Connection: keep-alive\r\n'
        b'\r\n')
    assert protocol.request.path == '/foo+bar'


async def test_request_parse_query_string(protocol):
    protocol.data_received(
        b'GET /feeds?foo=bar&bar=baz HTTP/1.1\r\n'
        b'Host: localhost:1707\r\n'
        b'User-Agent: HTTPie/0.9.8\r\n'
        b'Accept-Encoding: gzip, deflate\r\n'
        b'Accept: */*\r\n'
        b'Connection: keep-alive\r\n'
        b'\r\n')
    assert protocol.request.path == '/feeds'
    assert protocol.request.query['foo'][0] == 'bar'
    assert protocol.request.query['bar'][0] == 'baz'


async def test_request_parse_multivalue_query_string(protocol):
    protocol.data_received(
        b'GET /feeds?foo=bar&foo=baz HTTP/1.1\r\n'
        b'Host: localhost:1707\r\n'
        b'User-Agent: HTTPie/0.9.8\r\n'
        b'Accept-Encoding: gzip, deflate\r\n'
        b'Accept: */*\r\n'
        b'Connection: keep-alive\r\n'
        b'\r\n')
    assert protocol.request.path == '/feeds'
    assert protocol.request.query['foo'] == ['bar', 'baz']


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
    assert protocol.request.method == 'POST'
    assert protocol.request.body == b'{"link": "https://example.org"}'


async def test_invalid_request(protocol):
    protocol.data_received(
        b'INVALID HTTP/1.22\r\n')
    assert protocol.response.status == HTTPStatus.BAD_REQUEST


async def test_query_get_should_return_value(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=value')
    assert protocol.request.query.get('key') == 'value'


async def test_query_get_should_return_first_value_if_multiple(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=value&key=value2')
    assert protocol.request.query.get('key') == 'value'


async def test_query_get_should_raise_if_no_key_and_no_default(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=value')
    with pytest.raises(HttpError):
        protocol.request.query.get('other')


async def test_query_getlist_should_return_list_of_values(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=value&key=value2')
    assert protocol.request.query.list('key') == ['value', 'value2']


async def test_query_get_should_return_default_if_key_is_missing(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=value')
    assert protocol.request.query.get('other', None) is None
    assert protocol.request.query.get('other', 'default') == 'default'


@pytest.mark.parametrize('input,expected', [
    (b't', True),
    (b'true', True),
    (b'True', True),
    (b'1', True),
    (b'on', True),
    (b'f', False),
    (b'false', False),
    (b'False', False),
    (b'0', False),
    (b'off', False),
    (b'n', None),
    (b'none', None),
    (b'null', None),
    (b'NULL', None),
])
async def test_query_bool_should_cast_to_boolean(input, expected, protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=' + input)
    assert protocol.request.query.bool('key') == expected


async def test_query_bool_should_return_default(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=1')
    assert protocol.request.query.bool('other', default=False) is False


async def test_query_bool_should_raise_if_not_castable(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=one')
    with pytest.raises(HttpError):
        assert protocol.request.query.bool('key')


async def test_query_bool_should_raise_if_not_key_and_no_default(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=one')
    with pytest.raises(HttpError):
        assert protocol.request.query.bool('other')


async def test_query_bool_should_return_default_if_key_not_present(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=one')
    assert protocol.request.query.bool('other', default=False) is False


async def test_query_int_should_cast_to_int(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=22')
    assert protocol.request.query.int('key') == 22


async def test_query_int_should_return_default(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=1')
    assert protocol.request.query.int('other', default=22) == 22


async def test_query_int_should_raise_if_not_castable(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=one')
    with pytest.raises(HttpError):
        assert protocol.request.query.int('key')


async def test_query_int_should_raise_if_not_key_and_no_default(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=one')
    with pytest.raises(HttpError):
        assert protocol.request.query.int('other')


async def test_query_int_should_return_default_if_key_not_present(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=one')
    assert protocol.request.query.int('other', default=22) == 22


async def test_query_float_should_cast_to_float(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=2.234')
    assert protocol.request.query.float('key') == 2.234


async def test_query_float_should_return_default(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=1')
    assert protocol.request.query.float('other', default=2.234) == 2.234


async def test_query_float_should_raise_if_not_castable(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=one')
    with pytest.raises(HttpError):
        assert protocol.request.query.float('key')


async def test_query_float_should_raise_if_not_key_and_no_default(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=one')
    with pytest.raises(HttpError):
        assert protocol.request.query.float('other')


async def test_query_float_should_return_default_if_key_not_present(protocol):
    protocol.on_message_begin()
    protocol.on_url(b'/?key=one')
    assert protocol.request.query.float('other', default=2.234) == 2.234


async def test_request_parse_cookies(protocol):
    protocol.data_received(
        b'GET /feeds HTTP/1.1\r\n'
        b'Host: localhost:1707\r\n'
        b'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:54.0) '
        b'Gecko/20100101 Firefox/54.0\r\n'
        b'Origin: http://localhost:7777\r\n'
        b'Cookie: key=value\r\n'
        b'\r\n')
    assert protocol.request.cookies['key'] == 'value'


async def test_request_parse_multiple_cookies(protocol):
    protocol.data_received(
        b'GET /feeds HTTP/1.1\r\n'
        b'Host: localhost:1707\r\n'
        b'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:54.0) '
        b'Gecko/20100101 Firefox/54.0\r\n'
        b'Origin: http://localhost:7777\r\n'
        b'Cookie: key=value; other=new_value\r\n'
        b'\r\n')
    assert protocol.request.cookies['key'] == 'value'
    assert protocol.request.cookies['other'] == 'new_value'


async def test_request_cookies_get(protocol):
    protocol.data_received(
        b'GET /feeds HTTP/1.1\r\n'
        b'Host: localhost:1707\r\n'
        b'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:54.0) '
        b'Gecko/20100101 Firefox/54.0\r\n'
        b'Origin: http://localhost:7777\r\n'
        b'Cookie: key=value\r\n'
        b'\r\n')
    cookie = protocol.request.cookies.get('key')
    cookie == 'value'


async def test_request_cookies_get_unknown_key(protocol):
    protocol.data_received(
        b'GET /feeds HTTP/1.1\r\n'
        b'Host: localhost:1707\r\n'
        b'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:54.0) '
        b'Gecko/20100101 Firefox/54.0\r\n'
        b'Origin: http://localhost:7777\r\n'
        b'Cookie: key=value\r\n'
        b'\r\n')
    cookie = protocol.request.cookies.get('foo')
    assert cookie is None


async def test_request_get_unknown_cookie_key_raises_keyerror(protocol):
    protocol.data_received(
        b'GET /feeds HTTP/1.1\r\n'
        b'Host: localhost:1707\r\n'
        b'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:54.0) '
        b'Gecko/20100101 Firefox/54.0\r\n'
        b'Origin: http://localhost:7777\r\n'
        b'Cookie: key=value\r\n'
        b'\r\n')
    with pytest.raises(KeyError):
        protocol.request.cookies['foo']


async def test_can_store_arbitrary_keys_on_request():
    request = Request()
    request['custom'] = 'value'
    assert 'custom' in request
    assert request['custom'] == 'value'
