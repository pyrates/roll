# Tutorials

A tutorial:

* is learning-oriented
* allows the newcomer to get started
* is a lesson

*Analogy: teaching a small child how to cook*


## Your first Roll application

Make sure you [installed Roll first](how-to-guides.md#how-to-install-roll).

The tinyest application you can make is this one:

```python
from roll import Roll
from roll.extensions import simple_server

app = Roll()


@app.route('/hello/:parameter')
async def hello(request, response, parameter):
    response.body = f'Hello {parameter}'


if __name__ == '__main__':
    simple_server(app)
```

`Roll` is a [WSGI-compliant](http://wsgi.tutorial.codepoint.net/)
application dealing with routes, requests and responses. Everything else
is done via extensions.

*Note: if you are not familiar with that `f''` thing, it is Python 3.6
shortcut for `.format()`.*

To launch that application, run it with `python yourfile.py`. You should
be able to perform HTTP requests against it:

```
$ curl localhost:3579/hello/world
Hello world
```

*Note: [HTTPie](https://httpie.org/) is definitely a nicer replacement
for curl so we will use it from now on. You can `pip install` it too.*

```
$ http :3579/hello/world
HTTP/1.1 200 OK
Content-Length: 11

Hello world
```

That’s it! Celebrate that first step and… wait!
We need to test that view before :-).


## Your first Roll test

First install `pytest` and `pytest-asyncio`.

Then create a `tests.py` file and copy-paste:

```python
from http import HTTPStatus

import pytest

from yourfile import app as app_

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope='function')
def app():
    return app_


async def test_hello_view(client, app):

    resp = await client.get('/hello/world')
    assert resp.status == HTTPStatus.OK
    assert resp.body == 'Hello world'
```

You will have to adapt the import of your `app` given the filename
you gave during the previous part of the tutorial.

Once it’s done, you can launch `py.test tests.py`.

*Note: in case the `client` fixture is not found, you probably did not
install `Roll` correctly.*


## Using extensions

There are a couple of extensions available to “enrich” your application.

These extensions have to be applied to your Roll app, for instance:

```python
from roll import Roll
from roll.extensions import logger, simple_server

app = Roll()
logger(app)  # <- This is the only change we made! (+ import)

@app.route('/hello/:parameter')
async def hello(request, response, parameter):
    response.body = f'Hello {parameter}'


if __name__ == '__main__':
    simple_server(app)
```

Once you had that `logger` extension, each and every request will be
logged on your server-side. Try it by yourself!

Relaunch the server `$ python yourfile.py` and perform a new request with
httpie: `$ http :3579/hello/world`. On your server terminal you should
have something like that:

```
python yourfile.py
Rolling on http://127.0.0.1:3579
GET /hello/world
```

Notice the `GET` line, if you perform another HTTP request, a new line
will appear. Quite handy for debugging!

Another extension is very useful for debugging: `traceback`. Try to add
it by yourself and raise any error *within* your view to see it in
application (do not forget to restart your server!).

See the [reference documentation](reference.md#extensions) for all
built-in extensions.


## Using events

Last but not least, you can directly use registered events to alter the
behaviour of Roll at runtime.

*Note: this is how extensions are working internally.*

Let’s say you want to display a custom message when you launch your
server:

```python
from roll import Roll
from roll.extensions import simple_server

app = Roll()


@app.route('/hello/:parameter')
async def hello(request, response, parameter):
    response.body = f'Hello {parameter}'

@app.listen('startup')  # <- This is the part we added (3 lines)
async def on_startup():
    print('Example message')


if __name__ == '__main__':
    simple_server(app)
```

Now restart your server and you should see the message printed.
Wonderful.

See the [reference documentation](reference.md#events) for all available
events.
