# Extensions

Please read
[How to create an extension](../how-to/advanced.md#how-to-create-an-extension)
for usage.

All built-in extensions are imported from `roll.extensions`:

    from roll.extensions import cors, logger, …

## cors

Add [CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/Access_control_CORS)-related headers.
Especially useful for APIs. You generally want to also use the `options`
extension in the same time.

### Parameters

- **app**: Roll app to register the extension against
- **origin** (`str`; default: `*`): value of the `Access-Control-Allow-Origin` header
- **methods** (`list` of `str`; default: `None`): value of the
  `Access-Control-Allow-Methods` header; if `None` the header will not be set
- **headers** (`list` of `str`; default: `None`): value of the
  `Access-Control-Allow-Headers` header; if `None` the header will not be set


## logger

Log each and every request by default.

### Parameters

- **app**: Roll app to register the extension against
- **level** (default: `logging.DEBUG`): `logging` level
- **handler** (default: `logging.StreamHandler`): `logging` handler


## options

Performant return in case of `OPTIONS` HTTP request.
Combine it with the `cors` extension to handle the preflight request.

### Parameters

- **app**: Roll app to register the extension against


## content_negociation

Deal with content negociation declared during routes definition.
Will return a `406 Not Acceptable` response in case of mismatch between
the `Accept` header from the client and the `accepts` parameter set in
routes. Useful to reject requests which are not expecting the available
response.

### Parameters

- **app**: Roll app to register the extension against


### Requirements

- mimetype-match>=1.0.4


## traceback

Print the traceback on the server side if any. Handy for debugging.

### Parameters

- **app**: Roll app to register the extension against


## igniter

Display a BIG message when running the server.
Quite useless, hence so essential!

### Parameters

- **app**: Roll app to register the extension against


## static

Serve static files. Should not be used in production.

### Parameters

- **app**: Roll app to register the extension against
- **prefix** (`str`, default=`/static/`): URL prefix to serve the statics
- **root** (`str` or `pathlib.Path`, default=current executable path):
  filesystem path to look for static files
- **default_index** (`str`, default=empty string): filename, for instance `index.html`, useful to serve a static HTML website
- **name** (`str`, default=`static`): optional name to be used when calling `url_for` helper


## simple_server

Special extension that does not rely on the events’ mechanism.

Launch a local server on `127.0.0.1:3579` by default.

### Parameters

- **app**: Roll app to register the extension against
- **port** (`int`; default=`3579`): the port to listen
- **host** (`str`; default=`127.0.0.1`): where to bind the server
- **quiet** (`bool`; default=`False`): prevent the server to output startup
  debug infos

## named_url

Allow two things:

- name the routes
- build routes URL from these names and their optional parameters.

When using this extension, you can then optionaly pass a `name` parameter to the
`route` decorator. Otherwise, the name will be computed from the route handler
name.


### Parameters

- **app**: Roll app to register the extension against


### Usage

```python
from roll import Roll
from roll.extensions import named_url

app = Roll()

# Registering the extension will return the `url_for` helper.
url_for = named_url(app)


# Define a route
@app.route("/mypath/{myvar}")
async def myroute(request, response, myvar):
    pass

# Now we can build the url
url_for("myroute", myvar="value")
# /mypath/value


# To control the route name, we can pass it as a route kwarg:
@app.route("/mypath/{myvar}", name="custom_name")
async def otherroute(request, response, myvar):
    pass

# And then we can use it
url_for("custom_name", myvar="value")
```

Hint: the helper can be attached to the `app`, to have it available everywhere:

    app.url_for = named_url(app)
