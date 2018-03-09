import pytest

from roll import Roll, WSRoll
from roll.extensions import traceback


@pytest.fixture(scope='function')
def app():
    app_ = Roll()
    traceback(app_)
    return app_


@pytest.fixture(scope='function')
def wsapp():
    app_ = WSRoll()
    traceback(app_)
    return app_
