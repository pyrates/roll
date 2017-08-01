import logging
from traceback import print_exc

try:
    import ujson as json
except ImportError:
    import json as json


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
        logger.info("{} {}".format(request.method, request.path))

    @app.listen('startup')
    async def startup():
        logger.addHandler(handler)

    @app.listen('shutdown')
    async def shutdown():
        logger.removeHandler(handler)


def options(app):

    @app.listen('request')
    async def serve_request(request, response):
        if request.method == 'OPTIONS':
            return True  # Shortcut the request handling.


def traceback(app):

    @app.listen('error')
    async def on_error(error, response):
        if error.status.value == 500:
            print_exc()


def json_response(response, code_=200, **kwargs):
    response.status = code_
    response.headers['Content-Type'] = 'application/json'
    response.body = json.dumps(kwargs)
