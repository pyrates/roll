# Core objects

## Roll

Roll provides an asyncio protocol.

You can subclass it to set your own [Protocol](#protocol), [Route](#route),
[Query](#query), [Form](#form), [Files](#files), [Request](#request),
[Response](#response) and/or [Cookies](#cookies) class(es).

See [How to subclass Roll itself](./../how-to/advanced.md#how-to-subclass-roll-itself)
guide.


### Methods

- **route(path: str, methods: list, protocol: str='http', lazy_body: bool='False', \**extras: dict)**:
  register a route handler. Usually used as a decorator:

        @app.route('/path/with/{myvar}')
        async def my_handler(request, response, myvar):
             do_something

    By default, Roll routing is powered by [autoroutes](https://github.com/pyrates/autoroutes).
    Check out its documentation to get more details on which placeholders you
    can use on route paths.

    `methods` lists the HTTP methods accepted by this handler. If not defined,
    the handler will accept only `GET`. When the handler is a *class*, `methods` must
    not be used, as Roll will extrapolate them from the defined methods on the
    *class* itself. See [How to use class-based views](./../how-to/basic.md#how-to-use-class-based-views)
    for an example of class-based view.

    The `lazy_body` boolean parameter allows you to consume manually the body of the `Request`. It can be handy if you need to check for instance headers prior to load the whole body into RAM (think [images upload for instance](../how-to/advanced.md#how-to-consume-a-request-body-the-asynchronous-way)) or if you plan to accept a streaming incoming request. By default, the body of the request will be fully loaded.

    Any `extra` passed will be stored on the route payload, and accessible through
    `request.route.payload`.

    Raise `ValueError` if two URLs with the same name are registred.

- **listen(name: str)**: listen the event `name`.

        @app.listen('request')
        def on_request(request, response):
            do_something

    See [Events](#events) for a list of available events in Roll core.



## HttpError

The object to raise when an error must be returned.
Accepts a `status` and a `message`.
The `status` can be either a `http.HTTPStatus` instance or an integer.


## Request

A container for the result of the parsing on each request.
The default parsing is made by `httptools.HttpRequestParser`.

You can use the empty `kwargs` dict to attach whatever you want,
especially useful for extensions.


### Properties

- **url** (`bytes`): raw URL as received by Roll
- **path** (`str`): path element of the URL
- **query_string** (`str`): extracted query string
- **query** (`Query`): Query instance with parsed query string
- **method** (`str`): HTTP verb
- **body** (`bytes`): raw body as received by Roll by default. In case you activated the `lazy_body` option in the route, you will have to call the `load_body()` method *before* you access it
- **form** (`Form`): a [Form instance](#form) with multipart or url-encoded
  key/values parsed
- **files** (`Files`): a [Files instance](#files) with multipart files parsed
- **json** (`dict` or `list`): body parsed as JSON
- **content_type** (`str`): shortcut to the `Content-Type` header
- **host** (`str`): shortcut to the `Host` header
- **referrer** (`str`): shortcut to the `Referer` header
- **origin** (`str`): shortcut to the `Origin` header
- **headers** (`dict`): HTTP headers normalized in upper case
- **cookies** (`Cookies`): a [Cookies instance](#cookies) with request cookies
- **route** (`Route`): a [Route instance](#Route) storing results from URL matching

In case of errors during the parsing of `form`, `files` or `json`,
an [HttpError](#httperror) is raised with a `400` (Bad request) status code.

### Methods

- **load_body**: consume request body and load it in memory
- **read** -> `bytes`: call `load_body` and return the loaded body

### Custom properties

While `Request` cannot accept arbitrary attributes, it's a `dict` like object,
which keys are never used by Roll itself, they are dedicated to external use,
for example for session data.

See
[How to store custom data in the request](../how-to/basic.md#how-to-store-custom-data-in-the-request)
for an example of use.

### Iterating over Request’s data

If you set the `lazy_body` parameter to `True` in your route, you will be able to iterate over the `Request` object itself to access the data (this is what is done under the hood when you `load_body()` by the way). Note that it is only relevant to iterate once across the data.


## Response

A container for `status`, `headers` and `body`.

### Properties

- **status** (`http.HTTPStatus`): the response status

        # you can set the `status` with the HTTP code directly
        response.status = 204
        # same as
        response.status = http.HTTPStatus.OK

- **headers** (`dict`): case sensitive HTTP headers

- **cookies** (`Cookies`): a [Cookies instance](#cookies)

        response.cookies.set(name='cookie', value='value', path='/some/path')

- **body** (`bytes`): raw Response body; by default, Roll expects `body` to be
  `bytes`. If it's not, there are two cases:
    - if `body` is an [async generator](https://www.python.org/dev/peps/pep-0525/),
      Roll will serve a chunked response (see
      [How to serve a chunked response](../how-to/advanced.md#how-to-serve-a-chunked-response))
    - if it's anything else, Roll will convert it to `str` (by calling `str()`),
      and then to `bytes` (by calling its `encode()` method)


### Shortcuts

- **json**: takes any python object castable to `json` and set the body and the
  `Content-Type` header

        response.json = {'some': 'dict'}
        # Works also with a `list`:
        response.json = [{'some': 'dict'}, {'another': 'one'}]

- **redirect**: takes a `location, status` tuple, and set the Location header and
  the status accordingly.

        response.redirect = "https://example.org", 302

## Multipart

Responsible of the parsing of multipart encoded `request.body`.

### Methods

- **initialize(content_type: str)**: returns a tuple
  ([Form](#form) instance, [Files](#files) instance) filled with data
  from subsequent calls to `feed_data`
- **feed_data(data: bytes)**: incrementally fills [Form](#form) and
  [Files](#files) objects with bytes from the body


## Multidict

Data structure to deal with several values for the same key.
Useful for query string parameters or form-like POSTed ones.

### Methods

- **get(key: str, default=...)**: returns a single value for the given `key`,
  raises an `HttpError(BAD_REQUEST)` if the `key` is missing and no `default` is
  given
- **list(key: str, default=...)**: returns the values for the given `key` as `list`,
  raises an `HttpError(BAD_REQUEST)` if the `key` is missing and no `default` is
  given


## Query

Handy parsing of GET HTTP parameters.
Inherits from [Multidict](#multidict) with all the `get`/`list` goodies.

### Methods

- **bool(key: str, default=...)**: same as `get` but try to cast the value as
  `boolean`; raises an `HttpError(BAD_REQUEST)` if the value is not castable
- **int(key: str, default=...)**: same as `get` but try to cast the value as
  `int`; raises an `HttpError(BAD_REQUEST)` if the value is not castable
- **float(key: str, default=...)**: same as `get` but try to cast the value as
  `float`; raises an `HttpError(BAD_REQUEST)` if the value is not castable


## Form

Allow to access casted POST parameters from `request.body`.
Inherits from [Query](#query) with all the `get`/`list` + casting goodies.


## Files

Allow to access POSTed files from `request.body`.
Inherits from [Multidict](#multidict) with all the `get`/`list` goodies.


## Cookies

A Cookies management class, built on top of
[biscuits](https://github.com/pyrates/biscuits).

### Methods

- **set(name, value, max_age=None, expires=None, secure=False, httponly=False,
  path=None, domain=None)**: set a new cookie

See [How to deal with cookies](../how-to/basic.md#how-to-deal-with-cookies) for
examples.


## Protocol

Responsible of parsing the request and writing the response.


## Routes

Responsible for URL-pattern matching. Allows to switch to your own
parser. Default routes use [autoroutes](https://github.com/pyrates/autoroutes),
please refers to that documentation for available patterns.


## Route

A namedtuple to collect matched route data with attributes:

* **payload** (`dict`): the data received by the `@app.route` decorator,
  contains all handlers plus optionnal custom data. Value is `None` when request
  path is not found.
* **vars** (`dict`): URL placeholders resolved for the current route.


## Websocket

Communication protocol using a socket between a client (usually the browser)
and the server (a route endpoint).

See [The Websocket Protocol RFC](https://tools.ietf.org/html/rfc6455)

- **recv()**: receive the next message (async).
- **send(data)**: send data to the client. Can handle `str` or `bytes`
  arg (async).
- **close(code: int, reason: str)**: close the websocket (async).
- **ping(data)**: send a ping/heartbeat packet (async).
  This method returns an `asyncio.Future` object.
- **pong()**: send a pong packet in response to a ping (async).

The websocket object can be used as an asynchronous iterator. Using it that
way will yield a message at each iteration while keeping the websocket
connection alive.

```python
async def myendpoint(request, ws, **params):
    async for message in ws:
        print(message)
```
