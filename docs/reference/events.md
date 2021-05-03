# Events

Please read [Using events](../tutorials.md#using-events) for usage.

## startup

Fired once when launching the server.


## shutdown

Fired once when shutting down the server.


## headers

Fired at each request after request headers have been read, but before consuming
the body.

Receives `request` and `response` parameters.

Returning `True` allows to shortcut everything and return the current
response object directly, see the [options extension](#extensions) for
an example.


## request

Fired at each request after route matching, HTTP verb check and after body has
been eventually consumed.

Receives `request` and `response` parameters.

Returning `True` allows to shortcut everything and return the current
response object directly.


## response

Fired at each request after all processing.

Receives `request` and `response` parameters.


## error

Fired in case of error, can be at each request.
Use it to customize HTTP error formatting for instance.

Receives `request`, `response` and `error` parameters.

If an unexpected error is raised during code execution, Roll will catch it and
return a 500 response. In this case, `error.__context__` is set to the original
error, so one can adapt the behaviour in the error chain management, including
the `error` event.
