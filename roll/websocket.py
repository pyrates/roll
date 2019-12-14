import asyncio

import websockets
from websockets import ConnectionClosed  # exposed for convenience


class WSProtocol(websockets.WebSocketCommonProtocol):

    NEEDS_UPGRADE = True
    ALLOWED_METHODS = {'GET'}
    TIMEOUT = 5
    MAX_SIZE = 2 ** 20  # 1 megabytes
    MAX_QUEUE = 64
    READ_LIMIT = 2 ** 16
    WRITE_LIMIT = 2 ** 16

    is_client = False
    side = "server"  # Useful for websockets logging.

    def __init__(self, request):
        self.request = request
        super().__init__(
            timeout=self.TIMEOUT,
            max_size=self.MAX_SIZE,
            max_queue=self.MAX_QUEUE,
            read_limit=self.READ_LIMIT,
            write_limit=self.WRITE_LIMIT)

    def handshake(self, response):
        """Websocket handshake, handled by `websockets`
        """
        try:
            headers = websockets.http.Headers(**self.request.headers)
            key = websockets.handshake.check_request(headers)
            websockets.handshake.build_response(response.headers, key)
        except websockets.InvalidHandshake:
            raise RuntimeError('Invalid websocket request')

        subprotocol = None
        ws_protocol = ','.join(headers.get_all('Sec-Websocket-Protocol'))
        subprotocols = self.request.route.payload.get('subprotocols')
        if subprotocols and ws_protocol:
            # select a subprotocol
            client_subprotocols = tuple(
                (p.strip() for p in ws_protocol.split(',')))
            for p in client_subprotocols:
                if p in subprotocols:
                    subprotocol = p
                    response.headers['Sec-Websocket-Protocol'] = subprotocol
                    break

        # Return the subprotocol agreed upon, if any
        self.subprotocol = subprotocol

    async def run(self):
        # See https://tools.ietf.org/html/rfc6455#page-45
        try:
            await self.request.app.hook(
                'websocket_connect', self.request, self)
            await self.request.route.payload['GET'](self.request, self)
        except ConnectionClosed:
            # The client closed the connection.
            # We cancel the future to be sure it's in order.
            await self.close(1002, 'Connection closed untimely.')
        except asyncio.CancelledError:
            # The websocket task was cancelled
            # We need to warn the client.
            await self.close(1001, 'Handler cancelled.')
        except Exception:
            # A more serious error happened.
            # The websocket handler was untimely terminated
            # by an unwarranted exception. Warn the client.
            await self.close(1011, 'Handler died prematurely.')
            raise
        else:
            # The handler finished gracefully.
            # We can close the socket in peace.
            await self.close()
        finally:
            await self.request.app.hook(
                'websocket_disconnect', self.request, self)
