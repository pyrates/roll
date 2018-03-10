# -*- coding: utf-8 -*-

import asyncio
from collections import deque
from http import HTTPStatus
from urllib.parse import unquote
from httptools import (
    HttpParserUpgrade, HttpParserError, HttpRequestParser, parse_url)
from websockets import handshake, WebSocketCommonProtocol, InvalidHandshake
from websockets import ConnectionClosed  # exposed for convenience


class Context:

    __slots__ = ('app', 'writer', 'parser')

    _BODYLESS_METHODS = ('HEAD', 'CONNECT')
    _BODYLESS_STATUSES = (
        HTTPStatus.CONTINUE, HTTPStatus.SWITCHING_PROTOCOLS,
        HTTPStatus.PROCESSING, HTTPStatus.NO_CONTENT,
        HTTPStatus.NOT_MODIFIED,
    )
    
    def __init__(self, app, writer, parser):
        self.app = app
        self.writer = writer
        self.parser = parser

    def connection_lost(self, exc):
        pass

    def write(self, data):
        self.writer.write(data)

    def write_response(self, response):
        # Appends bytes for performances.
        payload = b'HTTP/1.1 %a %b\r\n' % (
            response.status.value, response.status.phrase.encode())
        if not isinstance(response.body, bytes):
            response.body = str(response.body).encode()
        # https://tools.ietf.org/html/rfc7230#section-3.3.2 :scream:
        bodyless = (response.status in self._BODYLESS_STATUSES or
                    (hasattr(self, 'request') and
                     self.request.method in self._BODYLESS_METHODS))
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
        self.writer.write(payload)
        if not self.parser.should_keep_alive():
            self.writer.close()

    def data_received(self, data: bytes):
        try:
            self.parser.feed_data(data)
        except HttpParserUpgrade:
            # Upgrade request
            pass
        except HttpParserError:
            # If the parsing failed before on_message_begin, we don't have a
            # response.
            raise
            response = self.app.Response(self.app)
            response.status = HTTPStatus.BAD_REQUEST
            response.body = b'Unparsable request'
            self.write_html(response)
            


class Protocol(asyncio.Protocol):
    """Responsible of parsing the request and writing the response."""

    __slots__ = ('app', 'request', 'parser', 'writer')
    RequestParser = HttpRequestParser

    def __init__(self, app):
        self.app = app
        self.parser = self.RequestParser(self)

    def connection_made(self, transport):
        self.writer = transport
        self.request = self.app.Request(self.app)
        self.request.set_context(Context(self.app, self.writer, self.parser))

    def connection_lost(self, exc):
        self.request.context.connection_lost(exc)
        super().connection_lost(exc)

    def data_received(self, data: bytes):
        self.request.context.data_received(data)

    def write(self, data):
        self.request.context.write(data)

    # All on_xxx methods are in use by httptools parser.
    # See https://github.com/MagicStack/httptools#apis
    def on_header(self, name: bytes, value: bytes):
        self.request.headers[name.decode().upper()] = value.decode()

    def on_body(self, body: bytes):
        # FIXME do not put all body in RAM blindly.
        self.request.body += body

    def on_url(self, url: bytes):
        parsed = parse_url(url)
        self.request.url = url
        self.request.path = unquote(parsed.path.decode())
        self.request.query_string = (parsed.query or b'').decode()
        self.request.method = self.parser.get_method().decode().upper()

    def on_message_begin(self):
        pass

    def on_message_complete(self):
        handler, params = self.app.lookup(self.request)
        task = self.app.loop.create_task(
            self.app.__call__(self.request, handler, params))
