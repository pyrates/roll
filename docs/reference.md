# Reference

A reference guide:

* is information-oriented
* describes the machinery
* is accurate and complete

*Analogy: a reference encyclopaedia article*

## Core objects

### Roll

Roll provides an asyncio protocol.

You can subclass it to set your own `Protocol` or `Routes` class.


### HttpError

The object to raise when an error must be returned.
Accepts a `status` and a `message`.
The `status` can be either a `http.HTTPStatus` instance or an integer.


### Request

A container for the result of the parsing on each request.
The default parsing is made by `httptools.HttpRequestParser`.

You can use the empty `kwargs` dict to attach whatever you want,
especially useful for extensions.


#### Properties

- **url** (`bytes`): raw URL as received by Roll
- **path** (`str`): path element of the URL
- **query_string** (`str`): extracted query string
- **query** (`Query`): Query instance with parsed query string
- **method** (`str`): HTTP verb
- **body** (`bytes`): raw body as received by Roll
- **headers** (`dict`): HTTP headers
- **route** (`Route`): a [Route instance](#Route) storing results from URL matching
- **kwargs** (`dict`): store here any extra data needed in the Request lifetime


### Response

A container for `status`, `headers` and `body`.

#### Properties

- **status** (`http.HTTPStatus`): the response status

```python
# you can set the `status` with the HTTP code directly
response.status = 204
# same as
response.status = http.HTTPStatus.OK
```
- **headers** (`dict`): case sensitive HTTP headers

*`Set-Cookie` exception*: if you want to set multiple `Set-Cookie` headers,
use a list as value (see [rfc7230](https://tools.ietf.org/html/rfc7230#page-23))*:

```python
response.headers['Set-Cookie'] = ['cookie1=value', 'cookie2=value']
```

- **body** (`bytes`): raw Response body; if `str` body is set, Roll will convert
  to `bytes` on the fly


#### Shortcuts

- **json**: takes any python object castable to `json` and set the body and the
  `Content-Type` header

```python
response.json = {'some': 'dict'}
# Works also with a `list`:
response.json = [{'some': 'dict'}, {'another': 'one'}]
```

### Query

Handy parsing of GET HTTP parameters.

#### Methods

- **get(key: str, default=...)**: returns a single value for the given `key`,
  raises an `HttpError(BAD_REQUEST)` if the `key` is missing and no `default` is
  given
- **list(key: str, default=...)**: returns the values for the given `key` as `list`,
  raises an `HttpError(BAD_REQUEST)` if the `key` is missing and no `default` is
  given
- **bool(key: str, default=...)**: same as `get` but try to cast the value as
  `boolean`; raises an `HttpError(BAD_REQUEST)` if the value is not castable
- **int(key: str, default=...)**: same as `get` but try to cast the value as
  `int`; raises an `HttpError(BAD_REQUEST)` if the value is not castable
- **float(key: str, default=...)**: same as `get` but try to cast the value as
  `float`; raises an `HttpError(BAD_REQUEST)` if the value is not castable


### Protocol

You can subclass it to set your own `Query`, `Request` or `Response`
classes. See [How to subclass Roll itself](how-to-guides.md#how-to-subclass-roll-itself)
guide.


### Routes

Responsible for URL-pattern matching. Allows to switch to your own
parser. Default routes use [autoroutes](https://github.com/pyrates/autoroutes),
please refers to that documentation for available patterns.


### Route

A namedtuple to collect matched route data with attributes:

* **payload** (`dict`): the data received by the `@app.route` decorator,
  contains all handlers plus optionnal custom data.
* **vars** (`dict`): URL placeholders resolved for the current route.


## Extensions

Please read
[How to create an extension](how-to-guides.md#how-to-create-an-extension)
for usage.

All built-in extensions are imported from `roll.extensions`:

    from roll.extensions import cors, logger, …

### cors

Add [CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/Access_control_CORS)-related headers.
Especially useful for APIs. You generally want to also use the `options`
extension in the same time.

#### Parameters

- **app**: Roll app to register the extension against
- **origin** (`str`; default: `*`): value of the `Access-Control-Allow-Origin` header
- **methods** (`list` of `str`; default: `None`): value of the
  `Access-Control-Allow-Methods` header; if `None` the header will not be set
- **headers** (`list` of `str`; default: `None`): value of the
  `Access-Control-Allow-Methods` header; if `None` the header will not be set


### logger

Log each and every request by default.

#### Parameters

- **app**: Roll app to register the extension against
- **level** (default: `logging.DEBUG`): `logging` level
- **handler** (default: `logging.StreamHandler`): `logging` handler


### options

Performant return in case of `OPTIONS` HTTP request.
Combine it with the `cors` extension to handle the preflight request.

#### Parameters

- **app**: Roll app to register the extension against


### content_negociation

Deal with content negociation declared during routes definition.
Will return a `406 Not Acceptable` response in case of mismatch between
the `Accept` header from the client and the `accepts` parameter set in
routes. Useful to reject requests which are not expecting the available
response.

#### Parameters

- **app**: Roll app to register the extension against


#### Requirements

- mimetype-match>=1.0.4


### traceback

Print the traceback on the server side if any. Handy for debugging.

#### Parameters

- **app**: Roll app to register the extension against


### igniter

Display a BIG message when running the server.
Quite useless, hence so essential!

#### Parameters

- **app**: Roll app to register the extension against


### static

Serve static files. Should not be used in production.

#### Parameters

- **app**: Roll app to register the extension against
- **prefix** (`str`, default=`/static/`): URL prefix to serve the statics
- **root** (`str` or `pathlib.Path`, default=current executable path):
  filesystem path to look for static files


### simple_server

Special extension that does not rely on the events’ mechanism.

Launch a local server on `127.0.0.1:3579` by default.

#### Parameters

- **app**: Roll app to register the extension against
- **port** (`int`; default=`3579`): the port to listen
- **host** (`str`; default=`127.0.0.1`): where to bind the server
- **quiet** (`bool`; default=`False`): prevent the server to output startup
  debug infos


## Events

Please read
[How to create an extension](how-to-guides.md#how-to-create-an-extension)
for usage.

### startup

Fired once when launching the server.


### shutdown

Fired once when shutting down the server.


### request

Fired at each request before any dispatching/route matching.

Receives `request` and `response` parameters.

Returning `True` allows to shortcut everything and return the current
response object directly, see the [options extension](#extensions) for
an example.


### response

Fired at each request after all processing.

Receives `request` and `response` parameters.


### error

Fired in case of error, can be at each request.
Use it to customize HTTP error formatting for instance.

Receives `request`, `response` and `error` parameters.
