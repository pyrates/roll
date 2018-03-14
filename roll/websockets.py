import asyncio
import types

from websockets import handshake, WebSocketCommonProtocol, InvalidHandshake
from websockets import ConnectionClosed  # exposed for convenience
from websockets.protocol import State

from roll import ProtocolUpgrade


def create_websocket(
        transport, subprotocol,
        websocket_timeout=5,
        websocket_max_size=2 ** 20,  # 1 megabytes
        websocket_max_queue=16,
        websocket_read_limit=2 ** 16,
        websocket_write_limit=2 ** 16):
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


class WebsocketProtocol(ProtocolUpgrade):

    __slots__ = ('websocket')

    def __init__(self, request, subprotocols, **params):
        self.subprotocol = None
        if subprotocols:
            ws_protocol = request.headers.get('SEC-WEBSOCKET-PROTOCOL')
            if ws_protocol:
                # select a subprotocol
                client_subprotocols = tuple(
                    (p.strip() for p in ws_protocol.split(',')))
                for p in client_subprotocols:
                    if p in subprotocols:
                        self.subprotocol = p
                        break

    def connection_lost(self, protocol, exc):
        self.websocket.connection_lost(exc)
    connection_lost.bubble_up = True

    def data_received(self, protocol, data):
        # Received data. We refuse the data if the websocket is
        # already closed. If the websocket is closing, this data
        # might be part of the closing handshake (closing frame)
        if self.websocket.state != State.CLOSED:
            self.websocket.data_received(data)
        else:
            # The websocket is closed and we still get data for it
            # This is an unexpected problem. Let's do nothing
            # about it
            pass

    def write(self, protocol, *args):
        # We don't need a response.
        protocol.writer.close()

    def __call__(self, protocol):
        self.websocket = create_websocket(protocol.writer, self.subprotocol)
        headers = []

        def get_header(k):
            return protocol.request.headers.get(k.upper(), '')

        def set_header(k, v):
            headers.append((k, v))

        try:
            key = handshake.check_request(get_header)
            handshake.build_response(set_header, key)
        except InvalidHandshake:
            raise RuntimeError('Invalid websocket request')

        if self.subprotocol:
            set_header('Sec-Websocket-Protocol', self.subprotocol)

        rv = b'HTTP/1.1 101 Switching Protocols\r\n'
        for k, v in headers:
            rv += (
                k.encode('utf-8') + b': ' + v.encode('utf-8') + b'\r\n')
        rv += b'\r\n'
        return rv

        
def websocket(app, path, subprotocols: list=None, **extras: dict):

    def websocket_wrapper(handler):

        async def websocket_handler(request, _, **params):
            # Handshake and protocol upgrade
            websocket_upgrade = WebsocketProtocol(
                request, subprotocols, **params)
            request.upgrade_protocol(websocket_upgrade)
            ws = websocket_upgrade.websocket

            fut = asyncio.ensure_future(
                handler(request, ws, **params), loop=app.loop)
            app['websockets'].add((fut, ws))
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
                app['websockets'].discard((fut, ws))

        payload = {'GET': websocket_handler}
        payload.update(extras)
        app.routes.add(path, **payload)
        return handler

    return websocket_wrapper


def websockets(app):
    app['websockets'] = set()
    app.websocket = types.MethodType(websocket, app)
    return app
