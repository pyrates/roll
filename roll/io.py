from http import HTTPStatus
from urllib.parse import parse_qs

from biscuits import parse

from .http import STATUSES, HttpCode, HttpError, Multipart

try:
    # In case you use json heavily, we recommend installing
    # https://pypi.python.org/pypi/ujson for better performances.
    import ujson as json
    JSONDecodeError = ValueError
except ImportError:
    import json as json
    from json.decoder import JSONDecodeError


class Request(dict):
    """A container for the result of the parsing on each request.

    The default parsing is made by `httptools.HttpRequestParser`.
    """
    __slots__ = (
        'app', 'url', 'path', 'query_string', '_query',
        'method', '_chunk', 'headers', 'route', '_cookies', '_form', '_files',
        'upgrade', 'protocol', '_json'
    )

    __namespace__ = (
        'app', 'query', 'json', 'form', 'cookies', 'body', 'route', 'files'
    )

    def __init__(self, app, protocol):
        self.app = app
        self.protocol = protocol
        self.headers = {}
        self._chunk = b''
        self.method = None
        self.upgrade = None
        self._cookies = None
        self._query = None
        self._form = None
        self._files = None
        self._json = None

    @property
    def cookies(self):
        if self._cookies is None:
            self._cookies = parse(self.headers.get('COOKIE', ''))
        return self._cookies

    @property
    def query(self):
        if self._query is None:
            parsed_qs = parse_qs(self.query_string, keep_blank_values=True)
            self._query = self.app.Query(parsed_qs)
        return self._query

    async def _parse_multipart(self):
        parser = Multipart(self.app)
        self._form, self._files = parser.initialize(self.content_type)
        async for data in self:
            try:
                parser.feed_data(data)
            except ValueError:
                raise HttpError(HTTPStatus.BAD_REQUEST,
                                'Unparsable multipart body')

    async def _parse_urlencoded(self):
        try:
            parsed_qs = parse_qs((await self.read()).decode(),
                                 keep_blank_values=True, strict_parsing=True)
            print(parsed_qs)
        except ValueError:
            raise HttpError(HTTPStatus.BAD_REQUEST,
                            'Unparsable urlencoded body')
        self._form = self.app.Form(parsed_qs)

    @property
    async def form(self):
        if self._form is None:
            if 'multipart/form-data' in self.content_type:
                await self._parse_multipart()
            elif 'application/x-www-form-urlencoded' in self.content_type:
                await self._parse_urlencoded()
            else:
                self._form = self.app.Form()
        return self._form

    @property
    async def files(self):
        if self._files is None:
            if 'multipart/form-data' in self.content_type:
                await self._parse_multipart()
            else:
                self._files = self.app.Files()
        return self._files

    @property
    async def json(self):
        if self._json is None:
            try:
                return json.loads(await self.read())
            except (UnicodeDecodeError, JSONDecodeError):
                raise HttpError(HTTPStatus.BAD_REQUEST, 'Unparsable JSON body')
        return self._json

    @property
    async def body(self):
        return await self.read()

    @property
    def content_type(self):
        return self.headers.get('CONTENT-TYPE', '')

    @property
    def host(self):
        return self.headers.get('HOST', '')

    async def read(self):
        data = b''
        async for chunk in self:
            data += chunk
        return data

    async def __aiter__(self):
        data = self._chunk
        if not data:
            return
        self.protocol.pause_reading()
        yield data


class Response:
    """A container for `status`, `headers` and `body`."""
    __slots__ = ('app', '_status', 'headers', 'body', '_cookies', 'protocol')

    def __init__(self, app, protocol):
        self.app = app
        self.protocol = protocol
        self.body = b''
        self.status = HTTPStatus.OK
        self.headers = {}
        self._cookies = None

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, http_code: HttpCode):
        # Idempotent if `http_code` is already an `HTTPStatus` instance.
        self._status = STATUSES[http_code]

    def json(self, value: dict):
        # Shortcut from a dict to JSON with proper content type.
        self.headers['Content-Type'] = 'application/json; charset=utf-8'
        self.body = json.dumps(value)

    json = property(None, json)

    @property
    def cookies(self):
        if self._cookies is None:
            self._cookies = self.app.Cookies()
        return self._cookies
