import asyncio
import os

import uvloop
from aiofile import AIOFile, Reader
from roll import Roll
from roll.extensions import cors, igniter, logger, simple_server, traceback

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

app = Roll()
cors(app)
logger(app)
traceback(app)


@app.route("/fullasync", methods=["POST"], lazy_body=True)
async def fullasync(request, response):
    response.body = (chunk async for chunk in request)


if __name__ == "__main__":
    simple_server(app)
