import asyncio
import sys

import uvloop
from roll import Roll as BaseRoll
from roll import Response
from roll.extensions import logger, simple_server, traceback

try:
    from jinja2 import Environment, PackageLoader, select_autoescape
except ImportError:
    sys.exit('Install the Jinja2 package to be able to run this example.')


env = Environment(
    loader=PackageLoader('html', 'templates'),
    autoescape=select_autoescape(['html'])
)
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


class HTMLResponse(Response):

    def html(self, template_name, *args, **kwargs):
        self.headers['Content-Type'] = 'text/html; charset=utf-8'
        self.body = env.get_template(template_name).render(*args, **kwargs)


class Roll(BaseRoll):
    Response = HTMLResponse


app = Roll()
logger(app)
traceback(app)


@app.route('/hello/{parameter}')
async def hello(request, response, parameter):
    response.html('home.html', title='Hello', content=parameter)


if __name__ == '__main__':
    simple_server(app)
