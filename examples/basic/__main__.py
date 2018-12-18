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


async def check_for_happiness(query):
    if query.bool("happiness", True) is True:
        print("Happy happiness!")
    else:
        raise HttpError(412, "Unhandled happiness issue!")


@app.route('/hello/{parameter}', before=check_for_happiness)
async def hello(response, parameter):
    response.body = f'Hello {parameter}'


@app.route('/cheer')
async def cheer_for_streaming(response):
    filename = os.path.basename(cheering)
    response.body = file_iterator(cheering)
    response.headers['Content-Disposition'] = (
        f"attachment; filename={filename}")


@app.route('/hello/{parameter}', methods=['POST'])
async def post_hello(json, response, parameter):
    response.body = json


@app.route('/app', methods=['GET'])
async def hello_app(response, app, query, form, body, **rest):
    response.body = f"{app.__class__.__name__}\n"
    print(rest, query, form, body)


@app.listen('startup')
async def on_startup():
    print('https://vimeo.com/34926862')


if __name__ == '__main__':
    simple_server(app)
