import asyncio

import uvloop

from roll import Roll
from roll.extensions import cors, logger, igniter
from roll.extensions import cors, logger, traceback, simple_server, igniter

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

app = Roll()
cors(app)
logger(app)
igniter(app)
traceback(app)


@app.route('/hello/:parameter')
async def hello(request, response, parameter):
    response.body = f'Hello {parameter}'


@app.listen('startup')
async def on_startup():
    print('https://vimeo.com/34926862')


if __name__ == '__main__':
    simple_server(app)
