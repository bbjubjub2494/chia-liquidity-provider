import asyncio
import click
import logging
from decimal import Decimal
from unittest.mock import Mock
from chia.types.blockchain_format.sized_bytes import bytes32
from chia.wallet.trade_record import TradeRecord

from liquidity.utils import make_wallet_rpc_client, XCH, USDS
from liquidity import LiquidityCurve, Pricing, TradeManager, dexie_api

log = logging.getLogger("liquidity")


@click.group()
def main():
    pass


async def logging_config():
    logging.basicConfig(format="[%(levelname)s] %(message)s", level=logging.INFO)


@main.command()
@click.argument("x_max", type=Decimal)
@click.argument("p_min", type=Decimal)
@click.argument("p_max", type=Decimal)
@click.argument("p_init", type=Decimal, default=0)
def show_init(x_max, p_min, p_max, p_init):
    """
    x_max: Total liquidity depth [XCH]"
    p_min: Minimum price [USD/XCH]
    p_max: Maximum price [USD/XCH]
    """
    base = XCH
    quote = USDS
    x_max = x_max * base
    Δx = ".1" * base
    p_min = p_min * quote / (1 * base)
    p_max = p_max * quote / (1 * base)
    p_init = p_init * quote / (1 * base)
    curve = LiquidityCurve.make_out_of_range(x_max, p_min, p_max)

    p = Pricing.make(curve, Δx, x_max)

    total_x = 0
    total_y = 0
    for Δx, Δy in p.initial_orders(p_init):
        print(Δx / (1 * base), Δy / (1 * quote))
        total_x += max(0, -Δx / (1 * base))
        total_y += max(0, -Δy / (1 * quote))

    print("total inputs required")
    print(total_x, total_y)


@main.command()
@click.option(
    "-f",
    "--fingerprint",
    help="Set the fingerprint to specify which wallet to use",
    type=int,
)
@click.argument("x_max", type=Decimal)
@click.argument("p_min", type=Decimal)
@click.argument("p_max", type=Decimal)
@click.argument("p_init", type=Decimal, default=0)
def init(fingerprint, x_max, p_min, p_max, p_init):
    """
    x_max: Total liquidity depth [XCH]"
    p_min: Minimum price [USD/XCH]
    p_max: Maximum price [USD/XCH]
    """
    base = XCH
    quote = USDS
    x_max = x_max * base
    Δx = ".1" * base
    p_min = p_min * quote / (1 * base)
    p_max = p_max * quote / (1 * base)
    p_init = p_init * quote / (1 * base)
    curve = LiquidityCurve.make_out_of_range(x_max, p_min, p_max)

    async def amain():
        await logging_config()
        async with make_wallet_rpc_client(
            fingerprint
        ) as wallet, TradeManager.StateRepository.open() as state_repo:
            tm = await TradeManager.from_scratch(
                base,
                quote,
                p_init,
                Pricing.make(curve, Δx, x_max),
                wallet,
                state_repo,
                dexie_api.mainnet,
            )

    asyncio.run(amain())


@main.command()
def manage():
    async def amain():
        await logging_config()
        async with make_wallet_rpc_client() as wallet, TradeManager.StateRepository.open() as state_repo:
            tm = TradeManager(wallet, state_repo, dexie_api.mainnet)
            while True:
                try:
                    await tm.check_open_trades()
                except Exception as err:
                    log.error("could not check open trades %s", err)
                await asyncio.sleep(30)

    asyncio.run(amain())
