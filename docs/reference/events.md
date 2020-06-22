# Events

Please read [Using events](../tutorials.md#using-events) for usage.

## startup

Fired once when launching the server.


## shutdown

Fired once when shutting down the server.


## request

Fired at each request before any dispatching/route matching.

Receives `request` and `response` parameters.

Returning `True` allows to shortcut everything and return the current
response object directly, see the [options extension](#extensions) for
an example.


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
