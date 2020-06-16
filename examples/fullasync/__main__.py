import asyncio
import os

import uvloop
from aiofile import AIOFile, Reader
from roll import Roll
from roll.ondemand import ondemand
from roll.io import Response, Request
from roll.http import Cookies
from roll.extensions import cors, igniter, logger, simple_server, traceback

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

app = Roll()
cors(app)
logger(app)
traceback(app)


@app.route("/fullasync", methods=["POST"], lazy_body=True)
@ondemand
async def fullasync(request: Request, response: Response):
    response.body = (chunk async for chunk in request)


@app.route("/", methods=["GET"], lazy_body=True)
@ondemand
async def someget(request: Request, response: Response, cookies: Cookies, test: str='toto'):
    response.body = f'{request} {response} {cookies}'


if __name__ == "__main__":
    simple_server(app)
