import asyncio

import uvloop

from roll import Roll

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

app = Roll()


@app.route('/hello/:parameter')
async def hello(request, response, parameter):
    response.json = {'message': f'Hello {parameter}'}
