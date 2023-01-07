import asyncio
import logging
from decimal import Decimal
from unittest.mock import Mock

import aiomisc
import click
from chia.types.blockchain_format.sized_bytes import bytes32
from chia.wallet.trade_record import TradeRecord

from chia_liquidity_provider import Engine, Grid, LiquidityCurve, dexie_api, hashgreen_api
from chia_liquidity_provider.services import DatabaseService, WalletRpcClientService
from chia_liquidity_provider.types import Asset

log = logging.getLogger("chia_liquidity_provider")


db = DatabaseService()
rpc = WalletRpcClientService()
services = [db, rpc]


@click.group()
def main():
    pass


@main.command()
@click.argument("x_max", type=Decimal)
@click.argument("p_min", type=Decimal)
@click.argument("p_max", type=Decimal)
@click.argument("p_init", type=Decimal, default=0)
def show_init(x_max, p_min, p_max, p_init) -> None:
    """
    x_max: Total liquidity depth [XCH]"
    p_min: Minimum price [USD/XCH]
    p_max: Maximum price [USD/XCH]
    """
    base = Asset.XCH
    quote = Asset.USDS
    x_max = x_max * base
    Δx = ".1" * base
    p_min = p_min * quote / (1 * base)
    p_max = p_max * quote / (1 * base)
    p_init = p_init * quote / (1 * base)
    curve = LiquidityCurve.make_out_of_range(x_max, p_min, p_max)

    p = Grid.make(curve, Δx, x_max)

    total_x = 0.0
    total_y = 0.0
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
def init(fingerprint: int, x_max, p_min, p_max, p_init) -> None:
    """
    x_max: Total liquidity depth [XCH]"
    p_min: Minimum price [USD/XCH]
    p_max: Maximum price [USD/XCH]
    """
    base = Asset.XCH
    quote = Asset.USDS
    x_max = x_max * base
    Δx = ".1" * base
    p_min = p_min * quote / (1 * base)
    p_max = p_max * quote / (1 * base)
    p_init = p_init * quote / (1 * base)
    curve = LiquidityCurve.make_out_of_range(x_max, p_min, p_max)

    async def amain() -> None:
        tm = await Engine.from_scratch(
            base,
            quote,
            p_init,
            Grid.make(curve, Δx, x_max),
            rpc,
            db,
            dexie_api.mainnet,
            hashgreen_api.mainnet,
        )

    aiomisc.run(amain(), *services)


@main.command()
def manage() -> None:
    async def amain() -> None:
        tm = Engine(rpc, db, dexie_api.mainnet, hashgreen_api.mainnet)
        while True:
            try:
                await tm.check_open_trades()
            except Exception as err:
                log.error("could not check open trades %s", err)
            await asyncio.sleep(30)

    aiomisc.run(amain(), *services)
