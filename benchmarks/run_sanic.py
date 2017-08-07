import asyncio
import logging

import uvloop

from sanic import Sanic
from sanic.response import json

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
logging.getLogger('asyncio').setLevel(logging.CRITICAL)

app = Sanic(log_config=None)


@app.route('/hello/<parameter>')
async def hello(request, parameter):
    return json({'message': f'Hello {parameter}'})
