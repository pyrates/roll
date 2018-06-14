# -*- coding: utf-8 -*-

import uuid
import uvloop
import asyncio
from roll import Roll, Response
from roll.socket import socket_server
from roll.extensions import logger, traceback


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


class HTMLResponse(Response):

    def html(self, body):
        self.headers['Content-Type'] = 'text/html'
        self.body = body

        
class Application(Roll):
    Response = HTMLResponse

        
app = Application()
logger(app)
traceback(app)


@app.route('/')
async def hello(request, response):
    response.html('Hello World !')


if __name__ == '__main__':
    socket_server(app)
