import logging

try:
    import ujson as json_
except ImportError:
    import json as json_


def cors(app, value='*'):

    @app.listen('response')
    async def add_cors_headers(response, request):
        response.headers['Access-Control-Allow-Origin'] = value


def logger(app, level=logging.DEBUG, handler=None):

    logger = logging.getLogger('roll')
    logger.setLevel(level)
    handler = handler or logging.StreamHandler()
    logger.addHandler(handler)

    @app.listen('request')
    async def log_request(request):
        logger.info("{} {}".format(request.method, request.path))


def options(app):

    @app.listen('request')
    async def serve_request(request):
        if request.method == 'OPTIONS':
            return b'', 200


def json(code=200, **kwargs):
    return (json_.dumps(kwargs), code, {'Content-Type': 'application/json'})
