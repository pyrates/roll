import asyncio
import logging

import uvloop

from roll import Roll

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
logging.getLogger('asyncio').setLevel(logging.CRITICAL)

app = Roll()


@app.route('/hello/minimal')
async def minimal(request, response):
    response.json = {'message': 'Hello, World!'}


@app.route('/hello/with/{parameter}')
async def parameter(request, response, parameter):
    response.json = {'parameter': parameter}


@app.route('/hello/cookie')
async def cookie(request, response):
    response.json = {'cookie': request.cookies['test']}
    response.cookies.set(name='bench', value='value')


@app.route('/hello/query')
async def query(request, response):
    response.json = {'query': request.query.get('query')}


@app.route('/hello/full/with/{one}/and/{two}')
async def full(request, response, one, two):
    response.json = {
        'parameters': f'{one} and {two}',
        'query': request.query.get('query'),
        'cookie': request.cookies['test'],
    }
    response.cookies.set(name='bench', value='value')
