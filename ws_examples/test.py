# -*- coding: utf-8 -*-

import uuid
import uvloop
import asyncio
from roll import Roll, Response
from roll.websockets import websockets, websocket
from roll.extensions import logger, simple_server, traceback


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


class HTMLResponse(Response):

    def html(self, body):
        self.headers['Content-Type'] = 'plain/text'
        self.body = body

        
class Application(Roll):
    Response = HTMLResponse

        
app = Application()
logger(app)
traceback(app)
websockets(app)


@app.route('/')
async def hello(request, response_class):
    response = response_class()
    response.html('Hello World !')
    return response


@app.websocket('/chat', websocket=True)
async def broadcast(request, ws, **params):
    wsid = str(uuid.uuid4())
    await ws.send(f'Welcome {wsid} !')
    async for message in ws:
        for (task, socket) in app.storage['websockets']:
            if socket != ws:
                await socket.send('{}: {}'.format(wsid, message))


@app.websocket('/fail')
async def failer(request, ws, **params):
    raise RuntimeError('TEST')


if __name__ == '__main__':
    simple_server(app)
