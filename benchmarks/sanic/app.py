import asyncio
import logging
import os

import uvloop

from sanic import Sanic
from sanic.response import json

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
logging.getLogger('asyncio').setLevel(logging.CRITICAL)

app = Sanic(log_config=None)


@app.route('/hello/<parameter>')
async def hello(request, parameter):
    response = json({'message': f'Hello {parameter}'})
    # response.cookies['bench'] = request.cookies.get('test')
    return response


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000,
            workers=int(os.environ.get('WORKERS')))
