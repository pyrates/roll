
import asyncio
from http import HTTPStatus
from websockets import handshake, WebSocketCommonProtocol, InvalidHandshake
from websockets import ConnectionClosed  # exposed for convenience


class WebsocketHandler:

    timeout = 5
    max_size = 2 ** 20  # 1 megabytes
    max_queue = 64
    read_limit = 2 ** 16
    write_limit = 2 ** 16

    def __init__(self, handler, subprotocols: list=None, **kwargs):
        self.handler = handler
        if subprotocols:
            subprotocols = frozenset(subprotocols)
        self.subprotocols = subprotocols

    def handshake(self, request):
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
        if self.subprotocols and ws_protocol:
            # select a subprotocol
            client_subprotocols = tuple(
                (p.strip() for p in ws_protocol.split(',')))
            for p in client_subprotocols:
                if p in self.subprotocols:
                    subprotocol = p
                    set_header('Sec-Websocket-Protocol', subprotocol)
                    break

        # write the 101 response back to the client
        # We will use a real Response in the future.
        rv = b'HTTP/1.1 101 Switching Protocols\r\n'
        for k, v in headers:
            rv += k.encode('utf-8') + b': ' + v.encode('utf-8') + b'\r\n'
        rv += b'\r\n'
        request.transport.write(rv)

        # Return the subprotocol agreed upon, if any
        return subprotocol

    def switch_protocol(self, request):
        # The websocket handshake agrees on the subprotocol to use.
        # It then writes a response to the client, before we go any further.
        subprotocol = self.handshake(request)

        # Creation of the new protocol, with the agreed upon subprotocol
        websocket = WebSocketCommonProtocol(
            timeout=self.timeout,
            max_size=self.max_size,
            max_queue=self.max_queue,
            read_limit=self.read_limit,
            write_limit=self.write_limit
        )
        websocket.subprotocol = subprotocol

        # The protocol now opens the connection and gets pushed into place.
        websocket.connection_made(request.transport)
        websocket.connection_open()
        request.transport.set_protocol(websocket)
        return websocket

    async def __call__(self, request, response, **params):
        if request.upgrade != 'websocket':
            # https://tools.ietf.org/html/rfc7231.html#page-62
            # Upgrade needed but none was request or of the wrong type
            response.status = HTTPStatus.UPGRADE_REQUIRED
            response.body = b"This service requires the websocket protocol"
            return

        ws = self.switch_protocol(request)
        if 'websockets' not in request.app:
            request.app['websockets'] = set()
        try:
            fut = request.app.loop.create_task(
                self.handler(request, ws, **params))
            request.app['websockets'].add((fut, ws))
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
            request.app['websockets'].discard((fut, ws))
