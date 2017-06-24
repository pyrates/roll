import logging


def cors(app, value='*'):

    @app.listen('response')
    async def add_cors_headers(response, request):
        response.headers['Allow-Cross-Origin'] = value


def logger(app, level=logging.DEBUG, handler=None):

    logger = logging.getLogger('roll')
    logger.setLevel(level)
    handler = handler or logging.StreamHandler()
    logger.addHandler(handler)

    @app.listen('request')
    async def log_request(request):
        logger.info("{} {}".format(request.method, request.path))
