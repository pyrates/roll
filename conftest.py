import pytest

from roll import Roll


@pytest.fixture(scope='function')
def app():
    return Roll()
