import pytest

from roll.extensions import named_url

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def activate_named_url(app, client):
    app.url_for = named_url(app)


async def test_named_url(app):
    @app.route("/test", name="myroute")
    async def get(req, resp):
        pass

    assert app.url_for("myroute") == "/test"


async def test_default_url_name(app):
    @app.route("/test")
    async def myroute(req, resp):
        pass

    assert app.url_for("myroute") == "/test"


async def test_url_with_simple_params(app):
    @app.route("/test/{param}")
    async def myroute(req, resp):
        pass

    assert app.url_for("myroute", param="foo") == "/test/foo"


async def test_url_with_typed_param(app):
    @app.route("/test/{param:int}")
    async def myroute(req, resp):
        pass

    assert app.url_for("myroute", param=22) == "/test/22"


async def test_url_with_regex_param(app):
    @app.route("/test/{param:[xyz]+}")
    async def myroute(req, resp):
        pass

    assert app.url_for("myroute", param=22) == "/test/22"


async def test_missing_name(app):
    with pytest.raises(ValueError):
        app.url_for("missing")


async def test_missing_param(app):
    @app.route("/test/{param}")
    async def myroute(req, resp):
        pass

    with pytest.raises(ValueError):
        assert app.url_for("myroute", badparam=22)


async def test_with_class_based_view(app):
    @app.route("/test")
    class MyRoute:
        async def on_get(self, request, response):
            pass

    assert app.url_for("myroute") == "/test"


async def test_duplicate_name(app):
    @app.route("/test")
    async def myroute(req, resp):
        pass

    with pytest.raises(ValueError):

        @app.route("/something", name="myroute")
        async def other(req, resp):
            pass


async def test_can_decorate_twice_same_handler(app):
    @app.route("/test")
    @app.route("/alias-url", name="legacy")
    async def myroute(req, resp):
        pass

    assert app.url_for("myroute") == "/test"
