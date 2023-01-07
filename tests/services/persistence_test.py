import asyncio
from unittest.mock import Mock, call

import pytest

from chia_liquidity_provider.services.persistence import *


@pytest.fixture
async def services(db, persistence):
    return [db, persistence]


async def handler_spec(params):
    return


@pytest.fixture
def handler1(persistence):
    handler1 = Mock(handler_spec, name="handler1")
    persistence.register("handler1", handler1)
    return handler1


@pytest.fixture
def handler2(persistence):
    handler2 = Mock(handler_spec, name="handler2")
    persistence.register("handler2", handler2)
    return handler2


@pytest.fixture
def handler3(persistence):
    handler3 = Mock(handler_spec, name="handler3")
    persistence.register("handler3", handler3)
    return handler3


async def test_simple_job(persistence, handler1):
    params = {"my_extra_info": 42}
    await persistence.defer("handler1", params)
    await asyncio.sleep(1)
    handler1.assert_called_once_with(params)


async def test_many_jobs(persistence, handler1):
    params_list = [{"my_extra_info": i} for i in range(42, 69)]
    for params in params_list:
        await persistence.defer("handler1", params)
    await asyncio.sleep(1)
    handler1.assert_has_calls([call(params) for params in params_list])
