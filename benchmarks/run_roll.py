import asyncio
import logging

import uvloop

from roll import Roll

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
logging.getLogger('asyncio').setLevel(logging.CRITICAL)

app = Roll()


@app.route('/hello/:parameter')
async def hello(request, response, parameter):
    response.json = {'message': f'Hello {parameter}'}

if __name__ == '__main__':
    app.serve(port=8000)
