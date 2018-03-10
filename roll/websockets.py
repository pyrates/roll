# -*- coding: utf-8 -*-

import asyncio
import types
from functools import wraps
from urllib.parse import unquote
from httptools import HttpParserUpgrade
from websockets import handshake, WebSocketCommonProtocol, InvalidHandshake
from websockets import ConnectionClosed  # exposed for convenience


class IncomingWebsocket:

    __slots__ = ('websocket', 'app')

    def __init__(self, app, websocket):
        self.app = app
        self.websocket = websocket

    def connection_lost(self, exc):
        self.websocket.connection_lost(exc)

    def data_received(self, data):
        # Received data. We refuse the data if the websocket is
        # already closed. If the websocket is closing, this data
        # might be part of the closing handshake (closing frame)
        if self.websocket.state != 3:  # not closed
            self.websocket.data_received(data)
        else:
            # The websocket is closed and we still get data for it
            # This is an unexpected problem. Let's do nothing
            # about it
            pass


class OutgoingWebsocket:

    websocket_timeout = 5
    websocket_max_size = 2 ** 20  # 1 megabytes
    websocket_max_queue = 16
    websocket_read_limit = 2 ** 16
    websocket_write_limit = 2 ** 16

    __slots__ = ('websocket', 'app', 'writer')
    
    def __init__(self, writer, app):
        self.app = app
        self.writer = writer

    def write(self, data):
        self.writer.write(data)
    
    def create_websocket(self, subprotocol):
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
    
    def write(self, *args):
        self.writer.close()

    def writer_response(self, response):
        raise NotImplementedError


def websocket_handshake(request, subprotocols: set=None):
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
    request.protocol.write(rv)

    # hook up the websocket protocol and new context
    protocol = request.protocol
    protocol.outgoing = OutgoingWebsocket(protocol.writer, request.app)
    websocket = protocol.outgoing.create_websocket(subprotocol)
    protocol.incoming = IncomingWebsocket(request.app, websocket)
    return websocket


def websocket(app, path, subprotocols: list=None, **extras: dict):

    if subprotocols is not None:
        subprotocols = frozenset(subprotocols)

    def websocket_wrapper(handler):

        async def websocket_handler(request, _, **params):
            ws = websocket_handshake(request, subprotocols)
            fut = asyncio.ensure_future(
                handler(request, ws, **params), loop=app.loop)
            app.storage['websockets'].add((fut, ws))
            try:
                await fut
            except ConnectionClosed:
                # The client closed the connection.
                # We cancel the future to be sure it's in order.
                fut.cancel()
                await ws.close(1002, 'Connection closed untimely.')
            except asyncio.CancelledError:
                # The websocket task was cancelled
                # We need to warn the client.
                await ws.close(1001, 'Handler cancelled.')
            except Exception as exc:
                # A more serious error happened.
                # The websocket handler was untimely terminated
                # by an unwarranted exception. Warn the client.
                await ws.close(1011, 'Handler died prematurely.')
                raise
            else:
                # The handler finished gracefully.
                # We can close the socket in peace.
                await ws.close()
            finally:
                # Whatever happened, the websocket fate has been
                # sealed. We remove it from our watch.
                app.storage['websockets'].discard((fut, ws))

        payload = {'GET': websocket_handler}
        payload.update(extras)
        app.routes.add(path, **payload)
        return handler

    return websocket_wrapper


def websockets(app):
    app.storage['websockets'] = set()
    app.websocket = types.MethodType(websocket, app)
