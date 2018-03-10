# -*- coding: utf-8 -*-

import asyncio
from collections import deque
from http import HTTPStatus
from urllib.parse import unquote
from httptools import (
    HttpParserUpgrade, HttpParserError, HttpRequestParser, parse_url)
from websockets import handshake, WebSocketCommonProtocol, InvalidHandshake
from websockets import ConnectionClosed  # exposed for convenience


class IncomingHTTP:

    __slots__ = ('app', 'parser', 'request')

    RequestParser = HttpRequestParser

    def __init__(self, app, request):
        self.app = app
        self.parser = self.RequestParser(self)
        self.request = request
        
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

    def should_keep_alive(self):
        self.parser.should_keep_alive()

    def connection_lost(self, exc):
        pass

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


class OutgoingHTTP:

    __slots__ = ('app', 'writer')

    _BODYLESS_METHODS = ('HEAD', 'CONNECT')
    _BODYLESS_STATUSES = (
        HTTPStatus.CONTINUE, HTTPStatus.SWITCHING_PROTOCOLS,
        HTTPStatus.PROCESSING, HTTPStatus.NO_CONTENT,
        HTTPStatus.NOT_MODIFIED,
    )

    def __init__(self, writer, app):
        self.app = app
        self.writer = writer

    def report_error(self, exc):
        response = self.app.Response(self.app)
        response.status = HTTPStatus.BAD_REQUEST
        response.body = b'Unparsable request'
        self.write_response(response)
        self.writer.close()

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


class Protocol(asyncio.Protocol):

    __slots__ = ('app', 'incoming', 'outgoing')

    def __init__(self, app):
        self.app = app

    def connection_made(self, transport):
        self.writer = transport
        self.request = self.app.Request(self.app, self)
        self.incoming = IncomingHTTP(self.app, self.request)
        self.outgoing = OutgoingHTTP(transport, self.app)

    def connection_lost(self, exc):
        self.incoming.connection_lost(exc)
        super().connection_lost(exc)

    def data_received(self, data: bytes):
        try:
            self.incoming.data_received(data)
        except Exception as exc:
            self.outgoing.report_error(exc)

    def write(self, data):
        self.outgoing.write(data)

    def reply(self, response):
        self.outgoing.write_response(response)
        if not self.incoming.should_keep_alive():
            self.writer.close()
