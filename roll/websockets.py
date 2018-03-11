# -*- coding: utf-8 -*-

import asyncio
import types
from websockets import handshake, WebSocketCommonProtocol, InvalidHandshake
from websockets import ConnectionClosed  # exposed for convenience


def create_websocket(
        transport, subprotocol,
        websocket_timeout = 5,
        websocket_max_size = 2 ** 20,  # 1 megabytes
        websocket_max_queue = 16,
        websocket_read_limit = 2 ** 16,
        websocket_write_limit = 2 ** 16):
    """Instanciate a new websocket with the given subprotocol.
    """
    websocket = WebSocketCommonProtocol(
        timeout=websocket_timeout,
        max_size=websocket_max_size,
        max_queue=websocket_max_queue,
        read_limit=websocket_read_limit,
        write_limit=websocket_write_limit
    )
    websocket.subprotocol = subprotocol
    websocket.connection_made(transport)
    websocket.connection_open()
    return websocket


class WebsocketIO:

    __slots__ = ('websocket')

    def __init__(self, websocket):
        self.websocket = websocket

    @classmethod
    def create_and_bind(cls, protocol, subprotocol):
        websocket = create_websocket(protocol.writer, subprotocol)
        wsio = cls(websocket)
        protocol.read_pipe.appendleft(wsio.data_received)
        protocol.write_pipe.appendleft(wsio.write)
        protocol.bound_protocols.appendleft(websocket)
        return wsio.websocket

    def data_received(self, protocol, data):
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
        return True

    def write(self, protocol, *args):
        # We don't need a response.
        protocol.writer.close()
        return True


def websocket_handshake(app, request, subprotocols: set=None):
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
    request.protocol.writer.write(rv)

    # hook up the websocket protocol and new context
    websocket = WebsocketIO.create_and_bind(request.protocol, subprotocol)
    return websocket


def websocket(app, path, subprotocols: list=None, **extras: dict):

    if subprotocols is not None:
        subprotocols = frozenset(subprotocols)

    def websocket_wrapper(handler):

        async def websocket_handler(request, _, **params):
            ws = websocket_handshake(app, request, subprotocols)
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
