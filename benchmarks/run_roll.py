import asyncio

import uvloop

from roll import Roll

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

app = Roll()


@app.route('/hello/:param')
async def hello(request, response, param):
    response.json = {'message': f'Hello {param}'}


if __name__ == '__main__':
    app.serve(port=8000)
