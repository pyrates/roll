import asyncio
from http import HTTPStatus

import uvloop
from roll import Roll, check_headers, HttpError
from roll.extensions import cors, igniter, logger, simple_server, traceback

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

app = Roll()
cors(app)
logger(app)
igniter(app)
traceback(app)


async def validate_size(request, response):
    print(request.headers)
    # import ipdb; ipdb.set_trace()
    if 'true' in request.headers.get('FAIL', ''):
        # return True
        raise HttpError(HTTPStatus.NOT_ACCEPTABLE, 'ok I fail')


@app.route('/hello/{parameter}', methods=['GET', 'POST'])
@check_headers(validate_size)
async def hello(request, response, parameter):
    response.body = f'Hello {parameter}'


@app.listen('startup')
async def on_startup():
    print('https://vimeo.com/34926862')


if __name__ == '__main__':
    simple_server(app)
