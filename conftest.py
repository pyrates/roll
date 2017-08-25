import pytest

from roll import Roll
from roll.extensions import traceback


@pytest.fixture(scope='function')
def app():
    app_ = Roll()
    traceback(app_)
    return app_
