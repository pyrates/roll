# -*- coding: utf-8 -*-

import asyncio
from http import HTTPStatus
from functools import partial
from collections import deque
from urllib.parse import unquote
from httptools import (
    HttpParserUpgrade, HttpParserError, HttpRequestParser, parse_url)
from websockets import handshake, WebSocketCommonProtocol, InvalidHandshake
from websockets import ConnectionClosed  # exposed for convenience


def default_receiver(protocol, data: bytes):
    try:
        protocol.parser.feed_data(data)
    except HttpParserError:
        # If the parsing failed before on_message_begin, we don't have a
        # response.
        protocol.response = protocol.app.Response(protocol.app)
        protocol.response.status = HTTPStatus.BAD_REQUEST
        protocol.response.body = b'Unparsable request'
        protocol.write()
    except HttpParserUpgrade:
        pass
    return True


def default_writer(protocol, *args):
    # Appends bytes for performances.
    payload = b'HTTP/1.1 %a %b\r\n' % (
        protocol.response.status.value,
        protocol.response.status.phrase.encode())
    if not isinstance(protocol.response.body, bytes):
        protocol.response.body = str(protocol.response.body).encode()
        # https://tools.ietf.org/html/rfc7230#section-3.3.2 :scream:
    bodyless = (protocol.response.status in protocol._BODYLESS_STATUSES or
                (hasattr(protocol, 'request') and
                 protocol.request.method in protocol._BODYLESS_METHODS))
    if 'Content-Length' not in protocol.response.headers and not bodyless:
        length = len(protocol.response.body)
        protocol.response.headers['Content-Length'] = length
    if protocol.response._cookies:
        # https://tools.ietf.org/html/rfc7230#page-23
        for cookie in protocol.response.cookies.values():
            payload += b'Set-Cookie: %b\r\n' % str(cookie).encode()
    for key, value in protocol.response.headers.items():
        payload += b'%b: %b\r\n' % (key.encode(), str(value).encode())
    payload += b'\r\n'
    if protocol.response.body and not bodyless:
        payload += protocol.response.body
    protocol.writer.write(payload)
    if not protocol.parser.should_keep_alive():
        protocol.writer.close()
    return True
    

class Protocol(asyncio.Protocol):
    """Responsible of parsing the request and writing the response."""

    __slots__ = ('app', 'request', 'parser', 'response',
                 'writer', 'read_pipe', 'write_pipe', 'bound_protocols')

    _BODYLESS_METHODS = ('HEAD', 'CONNECT')
    _BODYLESS_STATUSES = (HTTPStatus.CONTINUE, HTTPStatus.SWITCHING_PROTOCOLS,
                          HTTPStatus.PROCESSING, HTTPStatus.NO_CONTENT,
                          HTTPStatus.NOT_MODIFIED)
    RequestParser = HttpRequestParser


    def __init__(self, app):
        self.app = app
        self.parser = self.RequestParser(self)
        self.write_pipe = deque([default_writer])
        self.read_pipe = deque([default_receiver])
        self.bound_protocols = deque()

    def connection_made(self, transport):
        self.writer = transport

    def connection_lost(self, exc):
        if self.bound_protocols:
            while self.bound_protocols:
                protocol = self.bound_protocols.popleft()
                protocol.connection_lost(exc)
        super().connection_lost(exc)

    def data_received(self, data: bytes):
        if self.read_pipe:
            for reader in self.read_pipe:
                if reader(self, data) is True:
                    return
        else:
            # if we have no reader, we might need to drain the receiving
            # pool somehow
            pass

    def write(self, *args):
        if self.write_pipe:
            for writer in self.write_pipe:
                if writer(self, *args) is True:
                    return
        else:
            self.writer.close()

    # All on_xxx methods are in use by httptools parser.
    # See https://github.com/MagicStack/httptools#apis
    def on_header(self, name: bytes, value: bytes):
        self.request.headers[name.decode().upper()] = value.decode()

    def on_body(self, body: bytes):
        # FIXME do not put all body in RAM blindly.
        self.request.body += body

    def on_url(self, url: bytes):
        self.request.url = url
        parsed = parse_url(url)
        self.request.path = unquote(parsed.path.decode())
        self.request.query_string = (parsed.query or b'').decode()

    def on_message_begin(self):
        self.request = self.app.Request(self.app, self)
        self.response = self.app.Response(self.app)

    def on_message_complete(self):
        self.request.method = self.parser.get_method().decode().upper()
        task = self.app.loop.create_task(self.app(self.request, self.response))
        task.add_done_callback(self.write)
