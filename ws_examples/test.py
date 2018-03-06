# -*- coding: utf-8 -*-

import uvloop
import asyncio
from roll import WSRoll
from roll import Response
from roll.extensions import logger, simple_server, traceback


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


class HTMLResponse(Response):

    def html(self, body):
        self.headers['Content-Type'] = 'plain/text'
        self.body = body


class Application(WSRoll):
    Response = HTMLResponse


app = Application()
logger(app)
traceback(app)


@app.route('/')
async def hello(request, response):
    response.html('Hello World !')


@app.route('/feed', websocket=True)
async def feed(request, ws, **params):
    while True:
        data = 'hello!'
        print('Sending: ' + data)
        await ws.send(data)
        data = await ws.recv()
        print('Received: ' + data)


if __name__ == '__main__':
    simple_server(app)
