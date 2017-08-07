import asyncio

import uvloop

from roll import Roll
from roll.extensions import cors, logger, traceback, simple_server

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

app = Roll()
cors(app)
logger(app)
traceback(app)


@app.route('/hello/:parameter')
async def hello(request, response, parameter):
    response.body = f'Hello {parameter}'


@app.listen('startup')
async def on_startup():
    # Because https://www.youtube.com/watch?v=hh9rUe_JARE
    print("Ready to roll out!")


if __name__ == '__main__':
    simple_server(app)
