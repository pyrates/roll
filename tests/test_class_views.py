import pytest

pytestmark = pytest.mark.asyncio


async def test_can_use_class_as_handler(client, app):
    @app.route("/test")
    class MyHandler:
        async def on_get(self, request, response):
            response.body = "called"

        async def on_post(self, request, response):
            response.body = "called with post"

    resp = await client.get("/test")
    assert resp.status == 200
    assert resp.body == b"called"

    resp = await client.post("/test")
    assert resp.status == 200
    assert resp.body == b"called with post"

    resp = await client.put("/test")
    assert resp.status == 405


async def test_inherited_class_based_view(client, app):
    class View:
        CUSTOM = None

        async def on_get(self, request, response):
            response.body = self.CUSTOM

    @app.route("/tomatoes")
    class Tomato(View):
        CUSTOM = "tomato"

    @app.route("/cucumbers")
    class Cucumber(View):
        CUSTOM = "cucumber"

    @app.route("/gherkins")
    class Gherkin(Cucumber):
        CUSTOM = "gherkin"

    resp = await client.get("/tomatoes")
    assert resp.status == 200
    assert resp.body == b"tomato"

    resp = await client.get("/cucumbers")
    assert resp.status == 200
    assert resp.body == b"cucumber"

    resp = await client.get("/gherkins")
    assert resp.status == 200
    assert resp.body == b"gherkin"


async def test_can_use_extra_payload_with_class(client, app):
    @app.route("/test", custom="tomato")
    class MyHandler:
        async def on_get(self, request, response):
            response.body = request.route.payload["custom"]

    resp = await client.get("/test")
    assert resp.status == 200
    assert resp.body == b"tomato"


async def test_can_use_placeholders_in_route(client, app):
    @app.route("/test/{mystery}")
    class MyHandler:
        async def on_get(self, request, response, mystery):
            response.body = mystery

    resp = await client.get("/test/salad")
    assert resp.status == 200
    assert resp.body == b"salad"


async def test_cannot_define_methods_on_class_view(app):

    with pytest.raises(AttributeError):

        @app.route("/test", methods=["POST"])
        class MyHandler:
            async def on_get(self, request, response):
                response.body = "called"


async def test_cannot_define_empty_view(app):

    with pytest.raises(ValueError):

        @app.route("/test")
        class MyHandler:
            async def bad_get_name(self, request, response):
                response.body = "called"
