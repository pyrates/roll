# -*- coding: utf-8 -*-

import asyncio
from http import HTTPStatus
from urllib.parse import unquote
from httptools import (
    HttpParserUpgrade, HttpParserError, HttpRequestParser, parse_url)
from websockets import handshake, WebSocketCommonProtocol, InvalidHandshake
from websockets import ConnectionClosed  # exposed for convenience


class Protocol(asyncio.Protocol):
    """Responsible of parsing the request and writing the response."""

    __slots__ = ('app', 'request', 'parser', 'response', 'writer')
    _BODYLESS_METHODS = ('HEAD', 'CONNECT')
    _BODYLESS_STATUSES = (HTTPStatus.CONTINUE, HTTPStatus.SWITCHING_PROTOCOLS,
                          HTTPStatus.PROCESSING, HTTPStatus.NO_CONTENT,
                          HTTPStatus.NOT_MODIFIED)
    RequestParser = HttpRequestParser

    def __init__(self, app):
        self.app = app
        self.parser = self.RequestParser(self)

    def connection_made(self, transport):
        self.writer = transport
        
    def data_received(self, data: bytes):
        try:
            self.parser.feed_data(data)
        except HttpParserError:
            # If the parsing failed before on_message_begin, we don't have a
            # response.
            self.response = self.app.Response(self.app, self.writer)
            self.response.status = HTTPStatus.BAD_REQUEST
            self.response.body = b'Unparsable request'
            self.write()

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

    def on_headers_complete(self):
        self.request.transport = self.writer

    def on_message_begin(self):
        self.request = self.app.Request(self.app, self.writer)
        self.response = self.app.Response(self.app)

    def on_message_complete(self):
        self.request.method = self.parser.get_method().decode().upper()
        task = self.app.loop.create_task(self.app(self.request, self.response))
        task.add_done_callback(self.write)

    # May or may not have "future" as arg.
    def write(self, *args):
        # Appends bytes for performances.
        payload = b'HTTP/1.1 %a %b\r\n' % (
            self.response.status.value, self.response.status.phrase.encode())
        if not isinstance(self.response.body, bytes):
            self.response.body = str(self.response.body).encode()
        # https://tools.ietf.org/html/rfc7230#section-3.3.2 :scream:
        bodyless = (self.response.status in self._BODYLESS_STATUSES or
                    (hasattr(self, 'request') and
                     self.request.method in self._BODYLESS_METHODS))
        if 'Content-Length' not in self.response.headers and not bodyless:
            length = len(self.response.body)
            self.response.headers['Content-Length'] = length
        if self.response._cookies:
            # https://tools.ietf.org/html/rfc7230#page-23
            for cookie in self.response.cookies.values():
                payload += b'Set-Cookie: %b\r\n' % str(cookie).encode()
        for key, value in self.response.headers.items():
            payload += b'%b: %b\r\n' % (key.encode(), str(value).encode())
        payload += b'\r\n'
        if self.response.body and not bodyless:
            payload += self.response.body
        self.writer.write(payload)
        if not self.parser.should_keep_alive():
            self.writer.close()


class WSProtocol(Protocol):
    """Websocket protocol.
    """

    def __init__(self, *args, websocket_timeout=10,
                 websocket_max_size=2 ** 20,  # 1 megabytes
                 websocket_max_queue=64,
                 websocket_read_limit=2 ** 16,
                 websocket_write_limit=2 ** 16, **kwargs):
        super().__init__(*args, **kwargs)
        self.websocket = None
        self.websocket_timeout = websocket_timeout
        self.websocket_max_size = websocket_max_size
        self.websocket_max_queue = websocket_max_queue
        self.websocket_read_limit = websocket_read_limit
        self.websocket_write_limit = websocket_write_limit

    def connection_lost(self, exc):
        if self.websocket is not None:
            self.websocket.connection_lost(exc)
        super().connection_lost(exc)

    def data_received(self, data):
        if self.websocket is not None:
            # pass the data to the websocket protocol
            self.websocket.data_received(data)
        else:
            try:
                super().data_received(data)
            except HttpParserUpgrade:
                # Upgrade request
                pass

    def write(self, *args):
        if self.websocket is not None:
            # websocket requests do not write a response
            self.writer.close()
        else:
            super().write(*args)

    async def websocket_handshake(self, request, subprotocols: set=None):
        """Websocket handshake, handled by `websockets`
        """
        headers = []

        def get_header(k):
            return request.headers.get(k.upper(), '')

        def set_header(k, v):
            headers.append((k, v))

        try:
            key = handshake.check_request(get_header)
            handshake.build_response(set_header, key)
        except InvalidHandshake:
            raise RuntimeError('Invalid websocket request')

        subprotocol = None
        ws_protocol = get_header('Sec-Websocket-Protocol')
        if subprotocols and ws_protocol:
            # select a subprotocol
            client_subprotocols = tuple(
                (p.strip() for p in ws_protocol.split(',')))
            for p in client_subprotocols:
                if p in subprotocols:
                    subprotocol = p
                    set_header('Sec-Websocket-Protocol', subprotocol)
                    break

        # write the 101 response back to the client
        rv = b'HTTP/1.1 101 Switching Protocols\r\n'
        for k, v in headers:
            rv += k.encode('utf-8') + b': ' + v.encode('utf-8') + b'\r\n'
        rv += b'\r\n'
        self.writer.write(rv)

        # hook up the websocket protocol
        self.websocket = WebSocketCommonProtocol(
            timeout=self.websocket_timeout,
            max_size=self.websocket_max_size,
            max_queue=self.websocket_max_queue,
            read_limit=self.websocket_read_limit,
            write_limit=self.websocket_write_limit
        )
        self.websocket.subprotocol = subprotocol
        self.websocket.connection_made(self.writer)
        self.websocket.connection_open()
        return self.websocket
