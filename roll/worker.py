import asyncio
import os
import socket
import sys
import uvloop

from gunicorn.workers.base import Worker

from . import Request


class Worker(Worker):

    def init_process(self):
        self.server = None
        asyncio.get_event_loop().close()
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        super().init_process()

    def run(self):
        self.wsgi.loop = self.loop
        self.loop.run_until_complete(self.wsgi.startup())
        try:
            self.loop.run_until_complete(self._run())
        finally:
            self.loop.close()
        sys.exit()

    async def close(self):
        if self.server:
            server = self.server
            self.server = None
            self.log.info("Stopping server: %s", self.pid)
            await self.wsgi.shutdown()
            server.close()
            await server.wait_closed()

    async def _run(self):
        sock = self.sockets[0]
        # Pass loop to workaround python 3.5 issue.
        # See https://framagit.org/drone/roll/issues/1.
        kwargs = dict(sock=sock.sock)
        if hasattr(socket, 'AF_UNIX') and sock.family == socket.AF_UNIX:
            self.server = await asyncio.start_unix_server(self.wsgi, **kwargs)
        else:
            self.server = await self.loop.create_server(lambda: Request(self.wsgi), **kwargs)

        pid = os.getpid()
        try:
            while self.alive:
                self.notify()
                if pid == os.getpid() and self.ppid != os.getppid():
                    self.log.info("Parent changed, shutting down: %s", self)
                    break
                await asyncio.sleep(1.0, loop=self.loop)

        except Exception as e:
            print(e)

        await self.close()
