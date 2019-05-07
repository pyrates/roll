import os
import asyncio

import uvloop
from aiofile import AIOFile, Reader
from roll import Roll
from roll.extensions import cors, igniter, logger, simple_server, traceback


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

app = Roll()
cors(app)
logger(app)
igniter(app)
traceback(app)


cheering = os.path.join(os.path.dirname(__file__), 'crowd-cheering.mp3')


async def file_iterator(path):
    async with AIOFile(path, 'rb') as afp:
        reader = Reader(afp, chunk_size=4096)
        async for data in reader:
            yield data


@app.route('/hello/{parameter}')
async def hello(request, response, parameter):
    response.body = f'Hello {parameter}'


@app.route('/cheer')
async def cheer_for_streaming(request, response):
    filename = os.path.basename(cheering)
    response.body = file_iterator(cheering)
    response.headers['Content-Disposition'] = (
        f"attachment; filename={filename}")


@app.listen('startup')
async def on_startup():
    print('https://vimeo.com/34926862')


if __name__ == '__main__':
    simple_server(app)
