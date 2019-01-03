import os
import asyncio

import uvloop
from aiofile import AIOFile, Reader
from roll import Roll, HttpError
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


@app.listen('headers')
async def on_headers_middleware(request, response):
    print('on headers middleware')
    if request.query.bool('fail', False):
        raise HttpError(400, 'You requested to fail!')


async def on_headers(request, response):
    print('on headers decorator')


@app.route('/hello/{parameter}')
@app.listen('headers', on_headers)
async def hello(request, response, parameter):
    response.body = f'Hello {parameter}'


@app.route('/cheer')
async def cheer_for_streaming(request, response):
    filename = os.path.basename(cheering)
    response.body = file_iterator(cheering)
    response.headers['Content-Disposition'] = (
        f"attachment; filename={filename}")


@app.route('/hello/{parameter}', methods=['POST'])
@app.listen('request', on_headers)
async def post_hello(request, response, parameter):
    response.json = request.json


@app.listen('startup')
async def on_startup():
    print('https://vimeo.com/34926862')


@app.listen('error')
async def on_error(request, response, error):
    print(f"Caught {error} from {request.url}")


if __name__ == '__main__':
    simple_server(app)
