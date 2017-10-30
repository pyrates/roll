# Reference

A reference guide:

* is information-oriented
* describes the machinery
* is accurate and complete

*Analogy: a reference encyclopaedia article*

## Core objects

### `Roll`

Roll provides an asyncio protocol.

You can subclass it to set your own `Protocol` or `Routes` class.


### `HttpError`

The object to raise when an error must be returned.
Accepts a `status` and a `message`.
The `status` can be either a `http.HTTPStatus` instance or an integer.


### `Request`

A container for the result of the parsing on each request made by
`httptools.HttpRequestParser`.


### `Response`

A container for `status`, `headers` and `body`.

*Note: there is a shortcut to set JSON content as a dict (`json`).*


### `Query`

Handy parsing of GET HTTP parameters (`get`, `list`, `bool`, `int`,
`float`).


### `Protocol`

You can subclass it to set your own `Query`, `Request` or `Response`
classes.


### `Routes`

Responsible for URL-pattern matching. Allows to switch to your own
parser. Default routes use [autoroutes](https://github.com/pyrates/autoroutes),
please refers to that documentation for available patterns.


## Extensions

Please read
[How to create an extension](how-to-guides.md#how-to-create-an-extension)
for usage.

### `cors`

Add [CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/Access_control_CORS)-related headers. Especially useful for APIs.

You can set the `Access-Control-Allow-Origin` header with the `origin`
parameter, the `Access-Control-Allow-Methods` header with the
`methods` parameter (list) and the `Access-Control-Allow-Headers` header
with the `headers` parameter (list).


### `logger`

Log each and every request by default. You can pass a `level` parameter
and a `handler`. Both are classic `logging` module objects.


### `options`

Performant return in case of `OPTIONS` HTTP request.
Combine it with the `cors` extension to handle the preflight request.

This extension is applied by default, customize the `Roll` class if you
want to deactivate it.


### `traceback`

Print the traceback on the server side if any. Handy for debugging.


### `igniter`

Display a BIG message when running the server.
Quite useless, hence so essential!


### `simple_server`

Special extension that does not rely on the events’ mechanism.

Launch a local server on `127.0.0.1:3579` by default. `port` and `host`
parameters allow you to customize. The `quiet` parameter does not
display any message on startup.


## Events

Please read
[How to create an extension](how-to-guides.md#how-to-create-an-extension)
for usage.

### `startup`

Fired once when launching the server.


### `shutdown`

Fired once when shutting down the server.


### `request`

Fired at each request before any dispatching/route matching.

Receives `request` and `response` parameters.

Returning `True` allows to shortcut everything and return the current
response object directly, see the [options extension](#extensions) for
an example.


### `response`

Fired at each request after all processing.

Receives `request` and `response` parameters.


### `error`

Fired in case of error, can be at each request.
Use it to customize HTTP error formatting for instance.

Receives `request`, `response` and `error` parameters.
