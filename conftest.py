import pytest

from roll import Roll
from roll.websockets import websockets
from roll.extensions import traceback


@pytest.fixture(scope='function')
def app():
    app_ = Roll()
    traceback(app_)
    websockets(app_)
    return app_
