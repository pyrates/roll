import asyncio
import logging
import mimetypes
import sys
import os
from datetime import datetime
from cromlech.jwt.components import JWTService, JWTHandler, ExpiredToken
from http import HTTPStatus
from pathlib import Path
from traceback import print_exc

try:
    # In case you use json heavily, we recommend installing
    # https://pypi.python.org/pypi/ujson for better performances.
    import ujson as json
    JSONDecodeError = ValueError
except ImportError:
    import json as json
    from json.decoder import JSONDecodeError

from . import HttpError


def cors(app, origin='*', methods=None, headers=None):

    @app.listen('response')
    async def add_cors_headers(request, response):
        response.headers['Access-Control-Allow-Origin'] = origin
        if methods is not None:
            allow_methods = ','.join(methods)
            response.headers['Access-Control-Allow-Methods'] = allow_methods
        if headers is not None:
            allow_headers = ','.join(headers)
            response.headers['Access-Control-Allow-Headers'] = allow_headers


def session(
        app,
        key_path="/tmp/roll_session.key",
        domain=None,
        cookie_name='roll_session',
        maxsize=4096,
        TTL=60):

    def get_key(path):
        if not os.path.isfile(path):
            with open(path, 'w+', encoding="utf-8") as keyfile:
                key = JWTHandler.generate_key()
                export = key.export()
                keyfile.write(export)
        else:
            with open(path, 'r', encoding="utf-8") as keyfile:
                from jwcrypto import jwk
                data = json.loads(keyfile.read())
                key = jwk.JWK(**data)
        return key
    
    key = get_key(key_path)
    app['jwt'] = JWTService(key, JWTHandler, lifetime=TTL)
    
    @app.listen('request')
    async def extract_cookie_token(request, response):
        token = request.cookies.get(cookie_name)        
        if token is not None:
            try:
                request['session'] = request.app['jwt'].check_token(token)
                return
            except ExpiredToken:
                # The token is expired.
                # We'll return an empty session.
                pass
        request['session'] = {}
        return

    @app.listen('response')
    async def write_token_cookie(request, response):
        cookie_domain = domain or request.host.split(':', 1)[0]
        token = request.app['jwt'].generate(request.get('session', {}))
        if len(token) > maxsize:
            raise ValueError('Cookie exceeds the %i bytes limit' % maxsize)
        response.cookies.set(
            cookie_name, token, max_age=(TTL * 60), domain=cookie_domain)


def websockets_store(app):

    if 'websockets' not in app:
        app['websockets'] = set()
    assert isinstance(app['websockets'], set)

    @app.listen('websocket_connect')
    async def store(request, ws):
        request.app['websockets'].add(ws)

    @app.listen('websocket_disconnect')
    async def remove(request, ws):
        request.app['websockets'].discard(ws)


def logger(app, level=logging.DEBUG, handler=None):

    logger = logging.getLogger('roll')
    logger.setLevel(level)
    handler = handler or logging.StreamHandler()

    @app.listen('request')
    async def log_request(request, response):
        logger.info('%s %s', request.method, request.url.decode())

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


def content_negociation(app):

    try:
        from mimetype_match import get_best_match
    except ImportError:
        sys.exit('Please install mimetype-match>=1.0.4 to be able to use the '
                 'content_negociation extension.')

    @app.listen('request')
    async def reject_unacceptable_requests(request, response):
        accept = request.headers.get('ACCEPT')
        accepts = request.route.payload['accepts']
        if accept is None or get_best_match(accept, accepts) is None:
            raise HttpError(HTTPStatus.NOT_ACCEPTABLE)


def traceback(app):

    @app.listen('error')
    async def on_error(request, response, error):
        if error.status == HTTPStatus.INTERNAL_SERVER_ERROR:
            print_exc()


def igniter(app):

    @app.listen('startup')
    async def make_it_roll_like_it_never_rolled_before():
        logger = logging.getLogger('roll')
        logger.debug('''
         _          _                        _ _
        | |        | |  ()                  | | |
        | |     ___| |_  / ___     ____ ___ | | |
        | |    / _ \ __|  / __|   |  __/ _ \| | |
        | |___|  __/ |_   \__ \   | | | (_) | | |
        |______\___|\__|  |___/   |_|  \___/|_|_| ()

        ''')


def simple_server(app, port=3579, host='127.0.0.1', quiet=False):
    app.loop = asyncio.get_event_loop()
    app.loop.run_until_complete(app.startup())
    if not quiet:
        print('Rolling on http://%s:%d' % (host, port))
    server = app.loop.create_server(app.factory, host, port)
    app.loop.create_task(server)
    try:
        app.loop.run_forever()
    except KeyboardInterrupt:
        if not quiet:
            print('Bye.')
    finally:
        app.loop.run_until_complete(app.shutdown())
        server.close()
        app.loop.close()


def static(app, prefix='/static/', root=Path()):
    """Serve static files. Never use in production."""

    root = Path(root).resolve()

    if not prefix.endswith('/'):
        prefix += '/'
    prefix += '{path:path}'

    async def serve(request, response, path):
        abspath = (root / path).resolve()
        if root not in abspath.parents:
            raise HttpError(HTTPStatus.BAD_REQUEST, abspath)
        if not abspath.exists():
            raise HttpError(HTTPStatus.NOT_FOUND, abspath)
        content_type, encoding = mimetypes.guess_type(str(abspath))
        with abspath.open('rb') as source:
            response.body = source.read()
            response.headers['Content-Type'] = (content_type or
                                                'application/octet-stream')

    @app.listen('startup')
    async def register_route():
        app.route(prefix)(serve)
