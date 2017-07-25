import pytest

from roll import Roll
from roll.testing import req  # noqa: not detected otherwise.


@pytest.fixture(scope='function')
def app():
    return Roll()
