import asyncio
from urllib.parse import parse_qs, unquote
from functools import partial
from httptools import (HttpParserError, HttpParserUpgrade, HttpRequestParser,
                       parse_url)

from . import Roll
from .http import HttpError, HTTPStatus, HTTPProtocol


class HTTPParser:

    __slots__ = ('app', 'parser', 'request', 'complete')
    
    def __init__(self, app):
        self.app = app
        self.parser = HttpRequestParser(self)

    def data_received(self, data):
        try:
            self.parser.feed_data(data)
        except HttpParserUpgrade as upgrade:
            self.request.upgrade = self.request.headers['UPGRADE']

    def on_header(self, name, value):
        value = value.decode()
        if value:
            name = name.decode().upper()
            if name in self.request.headers:
                self.request.headers[name] += ', {}'.format(value)
            else:
                self.request.headers[name] = value

    def on_message_begin(self):
        self.complete = False
        self.request = self.app.Request(self.app)

    def on_url(self, url):
        self.request.url = url
        parsed = parse_url(url)
        self.request.path = unquote(parsed.path.decode())
        self.request.query_string = (parsed.query or b'').decode()

    def on_headers_complete(self):
        self.request.method = self.parser.get_method().decode().upper()
        self.complete = True


class ConnectionClosed(Exception):
    pass


def write(response):
    # Appends bytes for performances.
    payload = b'HTTP/1.1 %a %b\r\n' % (
        response.status.value, response.status.phrase.encode())
    if not isinstance(response.body, bytes):
        response.body = str(response.body).encode()
        # https://tools.ietf.org/html/rfc7230#section-3.3.2 :scream:
    bodyless = response.status in HTTPProtocol._BODYLESS_STATUSES
    if 'Content-Length' not in response.headers and not bodyless:
        length = len(response.body)
        response.headers['Content-Length'] = length
    if response._cookies:
        # https://tools.ietf.org/html/rfc7230#page-23
        for cookie in response.cookies.values():
            payload += b'Set-Cookie: %b\r\n' % str(cookie).encode()
    for key, value in response.headers.items():
        payload += b'%b: %b\r\n' % (key.encode(), str(value).encode())
    payload += b'\r\n'
    if response.body and not bodyless:
        payload += response.body
    return payload


class readlines:

    def __init__(self, reader):
        self.reader = reader

    def __aiter__(self):
        return self

    def __anext__(self):
        return self.reader.readline()


async def read_headers(httpparser, reader, max_field_size=2**16):
    async for line in readlines(reader):
        if not line and reader.at_eof():
            raise ConnectionClosed()
        if len(line) > max_field_size:
            raise HttpError(
                HTTPStatus.BAD_REQUEST, 'Request headers too large.')
        try:
            httpparser.data_received(line)
        except HttpParserError as exc:
            raise HttpError(
                HTTPStatus.BAD_REQUEST, 'Unparsable request.')
        if not line.strip():
            # End of the headers section.
            break

    # Readlines was finished by lack of data or by reaching the end
    # of the headers section. We need to test if the parser is done
    # with the headers
    if httpparser.complete:
        return httpparser.request

    # The request is complete.
    return None


async def request_handler(app, reader, writer):
    """Handles a TCP connection
    It can be one or several requests, according to the Keep-Alive
    """
    try:
        httpparser = HTTPParser(app)
        keep_alive = True
        while keep_alive:
            try:
                request = await read_headers(httpparser, reader)
            except HttpError:
                # we should write an error.
                raise
            else:
                if request is not None:
                    route = await app.lookup(request)
                    request.route = route
                    keep_alive = httpparser.parser.should_keep_alive()
                    response = app.Response(app)
                    response = await app(request, response)
                    writer.write(write(response))
                    await writer.drain()
                    del request
                    del response
                    
    except (ConnectionClosed, ConnectionResetError, BrokenPipeError):
        pass
    except Exception as e:
        raise
    finally:
        writer.close()


def socket_server(roll):
    loop = asyncio.get_event_loop()
    app = partial(request_handler, roll)
    runner = asyncio.start_server(app, '127.0.0.1', 8888, loop=loop)

    loop.create_task(runner)
    loop.run_forever()
