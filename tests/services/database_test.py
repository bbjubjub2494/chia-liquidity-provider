import pytest
from chia.util.ints import uint32

from chia_liquidity_provider import LiquidityCurve
from chia_liquidity_provider.types import Asset, Grid, Position


@pytest.fixture
async def services(db):
    return [db]


async def test_init_position(db):
    x_max = 1 * Asset.XCH
    p_min = 60 * Asset.USDS / (1 * Asset.XCH)
    p_max = 200 * Asset.USDS / (1 * Asset.XCH)
    curve = LiquidityCurve.make_out_of_range(x_max, p_min, p_max)

    grid = Grid.make(curve, ".1" * Asset.XCH, x_max)
    position = Position(123456789, uint32(1), uint32(2), grid)
    await db.init_position(position)
    row = await db.get_position()
    assert row == position
