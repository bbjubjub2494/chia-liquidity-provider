import asyncio
import logging
from decimal import Decimal
from unittest.mock import Mock

import aiomisc
import click
import coincurve
from bip32 import BIP32
from chia.types.blockchain_format.sized_bytes import bytes32
from chia.util.keychain import mnemonic_to_seed
from chia.wallet.trade_record import TradeRecord

from chia_liquidity_provider import Engine, Grid, LiquidityCurve, dexie_api, hashgreen_api, nostrdex_api
from chia_liquidity_provider.services import DatabaseService, WalletRpcClientService
from chia_liquidity_provider.types import Asset

log = logging.getLogger("chia_liquidity_provider")


db = DatabaseService()
rpc = WalletRpcClientService()
services = [db, rpc]
dexes = [dexie_api.mainnet, hashgreen_api.mainnet]


async def init_nostr():
    # FIXME: digusting hack
    global dexes
    while not await rpc.conn.get_synced():
        log.info("waiting for wallet to be synced")
        await asyncio.sleep(30)

    fingerprint = await rpc.conn.get_logged_in_fingerprint()
    rep = await rpc.conn.get_private_key(fingerprint)
    mnemonic = rep["seed"]
    bip32 = BIP32.from_seed(mnemonic_to_seed(mnemonic))
    privkey = coincurve.PrivateKey(bip32.get_privkey_from_path("m/44'/1237'/0'/0'/0/0"))
    dexes.append(nostrdex_api.mainnet(privkey))


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
        await init_nostr()
        tm = await Engine.from_scratch(base, quote, p_init, Grid.make(curve, Δx, x_max), rpc, db, dexes)

    aiomisc.run(amain(), *services)


@main.command()
def manage() -> None:
    async def amain() -> None:
        await init_nostr()
        tm = Engine(rpc, db, dexes)
        while True:
            try:
                await tm.check_open_trades()
            except Exception as err:
                log.error("could not check open trades %s", err)
            await asyncio.sleep(30)

    aiomisc.run(amain(), *services)
