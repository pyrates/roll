import asyncio

import uvloop
from roll import Roll
from roll.extensions import simple_server, session

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

app = Roll()
session(app)


@app.route('/index.html')
async def hello(request, response):
    number = request.session.get('visits', 0)
    if not number:
        response.body = f'Hello, this is your first visit !'
    else:
        response.body = (
            f'Welcome back, you visited this page {number} times before!')
    request.session['visits'] = number + 1


if __name__ == '__main__':
    simple_server(app)
