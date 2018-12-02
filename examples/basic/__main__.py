import asyncio

import uvloop
from roll import Roll
from roll.extensions import cors, igniter, logger, simple_server, traceback

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

app = Roll()
cors(app)
logger(app)
igniter(app)
traceback(app)


@app.route('/hello/{parameter}')
async def hello(response, parameter):
    response.body = f'Hello {parameter}'


@app.route('/hello/{parameter}', methods=['POST'])
async def post_hello(json, response, parameter):
    # data = await request.read()
    response.body = json


@app.listen('startup')
async def on_startup():
    print('https://vimeo.com/34926862')


if __name__ == '__main__':
    simple_server(app)
