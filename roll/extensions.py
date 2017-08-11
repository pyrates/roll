import asyncio
import logging
from http import HTTPStatus
from traceback import print_exc


def cors(app, value='*'):

    @app.listen('response')
    async def add_cors_headers(response, request):
        response.headers['Access-Control-Allow-Origin'] = value


def logger(app, level=logging.DEBUG, handler=None):

    logger = logging.getLogger('roll')
    logger.setLevel(level)
    handler = handler or logging.StreamHandler()

    @app.listen('request')
    async def log_request(request, response):
        logger.info("{} {}".format(request.method, request.url.decode()))

    @app.listen('startup')
    async def startup():
        logger.addHandler(handler)

    @app.listen('shutdown')
    async def shutdown():
        logger.removeHandler(handler)


def options(app):

    @app.listen('request')
    async def handle_options(request, response):
        # Shortcut the request handling for OPTIONS requests.
        return request.method == 'OPTIONS'


def traceback(app):

    @app.listen('error')
    async def on_error(error, response):
        if error.status == HTTPStatus.INTERNAL_SERVER_ERROR:
            print_exc()


def simple_server(app, port=3579, host='127.0.0.1'):
    app.loop = asyncio.get_event_loop()
    app.loop.run_until_complete(app.startup())
    print('Rolling on http://%s:%d' % (host, port))
    server = app.loop.create_server(app.factory, host, port)
    app.loop.create_task(server)
    try:
        app.loop.run_forever()
    except KeyboardInterrupt:
        print('Bye.')
    finally:
        app.loop.run_until_complete(app.shutdown())
        server.close()
        app.loop.close()
