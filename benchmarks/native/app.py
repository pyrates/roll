import asyncio
import logging
import signal
import sys

import uvloop

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
logging.getLogger('asyncio').setLevel(logging.CRITICAL)


class Protocol(asyncio.Protocol):

    def connection_made(self, transport):
        self.writer = transport

    def data_received(self, data: bytes):
        self.writer.write(b'HTTP/1.1 200 OK\r\n')
        self.writer.write(b'Content-Length: 27\r\n')
        self.writer.write(b'Content-Type: application/json\r\n')
        self.writer.write(b'\r\n')
        self.writer.write(b'{"message":"Hello, World!"}')


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    server = loop.create_server(Protocol, '127.0.0.1', 8000)
    loop.create_task(server)
    print('Serving on http://127.0.0.1:8000')

    def shutdown(*args):
        server.close()
        print('\nServer stopped.')
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()
        loop.close()
