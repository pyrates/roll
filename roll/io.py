from asyncio import Event
from http import HTTPStatus
from queue import deque
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


class StreamQueue:

    def __init__(self):
        self.items = deque()
        self.event = Event()
        self.waiting = False
        self.dirty = False
        self.finished = False

    async def get(self):
        try:
            return self.items.popleft()
        except IndexError:
            if self.finished is True:
                return b''
            else:
                self.event.clear()
                self.waiting = True
                await self.event.wait()
                self.event.clear()
                self.waiting = False
                return self.items.popleft()

    def put(self, item):
        self.dirty = True
        self.items.append(item)
        if self.waiting is True:
            self.event.set()

    def clear(self):
        if self.dirty:
            self.items.clear()
            self.event.clear()
            self.dirty = False
        self.finished = False

    def end(self):
        if self.waiting:
            self.put(None)
        self.finished = True


class Request(dict):
    """A container for the result of the parsing on each request.

    The default parsing is made by `httptools.HttpRequestParser`.
    """
    __slots__ = (
        'app', 'url', 'path', 'query_string', '_query', '_body',
        'method', '_chunk', 'headers', 'route', '_cookies', '_form', '_files',
        'upgrade', 'protocol', 'queue', '_json'
    )

    def __init__(self, app, protocol):
        self.app = app
        self.protocol = protocol
        self.queue = StreamQueue()
        self.headers = {}
        self._body = None
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

    def _parse_multipart(self):
        parser = Multipart(self.app)
        self._form, self._files = parser.initialize(self.content_type)
        try:
            parser.feed_data(self.body)
        except ValueError:
            raise HttpError(HTTPStatus.BAD_REQUEST,
                            'Unparsable multipart body')

    def _parse_urlencoded(self):
        try:
            parsed_qs = parse_qs(self.body.decode(), keep_blank_values=True,
                                 strict_parsing=True)
        except ValueError:
            raise HttpError(HTTPStatus.BAD_REQUEST,
                            'Unparsable urlencoded body')
        self._form = self.app.Form(parsed_qs)

    @property
    def form(self):
        if self._form is None:
            if 'multipart/form-data' in self.content_type:
                self._parse_multipart()
            elif 'application/x-www-form-urlencoded' in self.content_type:
                self._parse_urlencoded()
            else:
                self._form = self.app.Form()
        return self._form

    @property
    def files(self):
        if self._files is None:
            if 'multipart/form-data' in self.content_type:
                self._parse_multipart()
            else:
                self._files = self.app.Files()
        return self._files

    @property
    def json(self):
        if self._json is None:
            try:
                self._json = json.loads(self.body)
            except (UnicodeDecodeError, JSONDecodeError):
                raise HttpError(HTTPStatus.BAD_REQUEST, 'Unparsable JSON body')
        return self._json

    @property
    def content_type(self):
        return self.headers.get('CONTENT-TYPE', '')

    @property
    def host(self):
        return self.headers.get('HOST', '')

    @property
    def referrer(self):
        # https://en.wikipedia.org/wiki/HTTP_referer#Etymology
        return self.headers.get('REFERER', '')

    referer = referrer

    @property
    def origin(self):
        return self.headers.get('ORIGIN', '')

    @property
    def body(self):
        if self._body is None:
            raise HttpError(HTTPStatus.INTERNAL_SERVER_ERROR,
                            "Trying to consume lazy body")
        return self._body

    @body.setter
    def body(self, data):
        self._body = data

    async def load_body(self):
        if self._body is None:
            self._body = b''
            async for chunk in self:
                self._body += chunk

    async def read(self):
        await self.load_body()
        return self._body

    async def __aiter__(self):
        # TODO raise if already consumed?
        while True:
            self.protocol.resume_reading()
            data = await self.queue.get()
            if not data:
                break
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

    @property
    def redirect(self):
        return self.headers.get("Location"), self.status

    @redirect.setter
    def redirect(self, to):
        """Shortcut to set a redirect."""
        location, status = to
        self.headers["Location"] = location
        self.status = status
