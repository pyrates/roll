import asyncio
import logging
import os

import uvloop

from sanic import Sanic
from sanic.response import json

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
logging.getLogger('asyncio').setLevel(logging.CRITICAL)

app = Sanic(log_config=None)


@app.route('/hello/minimal')
async def minimal(request):
    return json({'message': 'Hello, World!'})


@app.route('/hello/with/<parameter>')
async def parameter(request, parameter):
    return json({'parameter': parameter})


@app.route('/hello/cookie')
async def cookie(request):
    response = json({'cookie': request.cookies.get('test')})
    response.cookies['bench'] = 'value'
    return response


@app.route('/hello/query')
async def query(request):
    return json({'query': request.args.get('query')})


@app.route('/hello/full/with/<one>/and/<two>')
async def full(request, one, two):
    response = json({
        'parameters': f'{one} and {two}',
        'query': request.args.get('query'),
        'cookie': request.cookies['test'],
    })
    response.cookies['bench'] = 'value'
    return response


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, access_log=False,
            workers=int(os.environ.get('WORKERS')))
