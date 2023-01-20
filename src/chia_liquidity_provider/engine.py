import asyncio
import dataclasses
import logging
import typing

from chia.consensus.coinbase import create_puzzlehash_for_pk
from chia.util.ints import uint32
from chia.util.keychain import KeyData
from chia.wallet.derive_keys import master_sk_to_wallet_sk
from chia.wallet.trading.trade_status import TradeStatus

if typing.TYPE_CHECKING:
    from chia_liquidity_provider import dexie_api, hashgreen_api
from chia_liquidity_provider.services import DatabaseService, WalletRpcClientService
from chia_liquidity_provider.types import Asset, Grid, Order, Position

log = logging.getLogger(__name__)


@dataclasses.dataclass
class Engine:
    rpc: WalletRpcClientService
    db: DatabaseService
    dexie: "dexie_api.Api"
    hashgreen: "hashgreen_api.Api"

    @classmethod
    async def find_wallet_id(cls, rpc: WalletRpcClientService, asset: Asset) -> uint32:
        asset_id = asset.asset_id
        if asset_id is None:
            return uint32(1)
        rep = await rpc.conn.cat_asset_id_to_name(asset_id)
        if rep is not None and rep[0] is not None:
            return rep[0]
        rep2 = await rpc.conn.create_wallet_for_existing_cat(asset_id)
        return uint32(rep2["wallet_id"])

    @classmethod
    async def from_scratch(
        cls,
        base_asset: Asset,
        quote_asset: Asset,
        p_init: float,
        grid: Grid,
        rpc: WalletRpcClientService,
        db: DatabaseService,
        dexie: "dexie_api.Api",
        hashgreen: "hashgreen_api.Api",
    ) -> "Engine":
        while not await rpc.conn.get_synced():
            log.info("waiting for wallet to be synced")
            await asyncio.sleep(30)

        base_asset_wallet_id = await cls.find_wallet_id(rpc, base_asset)
        quote_asset_wallet_id = await cls.find_wallet_id(rpc, quote_asset)
        fingerprint = await rpc.conn.get_logged_in_fingerprint()
        position = Position(
            fingerprint,
            base_asset_wallet_id,
            quote_asset_wallet_id,
            grid,
        )
        await db.init_position(position)
        self = cls(rpc=rpc, db=db, dexie=dexie, hashgreen=hashgreen)

        base_asset_amts = [-delta for delta, _ in position.grid.initial_orders(p_init) if delta < 0]
        quote_asset_amts = [
            -delta for _, delta in position.grid.initial_orders(p_init) if delta < 0
        ]

        await self._split_coins(base_asset, base_asset_wallet_id, base_asset_amts)
        await self._split_coins(quote_asset, quote_asset_wallet_id, quote_asset_amts)
        await self._create_trades(p_init)
        await self.db.conn.commit()
        return self

    async def _split_coins(self, asset, wallet_id, amts):
        if len(amts) < 2:
            return  # nothing to split

        position = await self.db.get_position()
        rep = await self.rpc.conn.get_private_key(position.fingerprint)
        kd = KeyData.from_mnemonic(rep["seed"])

        def wallet_sk(i):
            return master_sk_to_wallet_sk(kd.private_key, i)

        # split coins
        offset = await self.rpc.conn.get_current_derivation_index()
        additions = [
            {
                "amount": amt,
                "puzzle_hash": create_puzzlehash_for_pk(wallet_sk(offset + i).get_g1()),
            }
            for i, amt in enumerate(amts)
        ]
        if asset == Asset.XCH:
            tx = await self.rpc.conn.send_transaction_multi(
                wallet_id=wallet_id, additions=additions
            )
        else:
            tx = await self.rpc.conn.cat_spend(wallet_id=wallet_id, additions=additions)
        while not tx.confirmed:
            tx = await self.rpc.conn.get_transaction(tx.wallet_id, tx.name)

    async def _create_trades(self, p_init):
        position = await self.db.get_position()
        for o in position.grid.initial_orders(p_init):
            await self._create_trade(*o)

    async def _create_trade(self, base_delta, quote_delta):
        position = await self.db.get_position()
        offer, trade = await self.rpc.conn.create_offer_for_ids(
            {position.base_asset_wallet_id: base_delta, position.quote_asset_wallet_id: quote_delta}
        )
        log.info("created trade %s", trade.trade_id)
        await self.db.insert_order(position, Order(trade.trade_id, base_delta, quote_delta))
        try:
            await asyncio.gather(
                self.dexie.post_offer(offer),
                self.hashgreen.post_offer(offer),
            )
        except Exception:
            log.exception("error posting trade (ignoring)")
        else:
            log.info("trade %s successfully posted", trade.trade_id)

    async def check_open_trades(self):
        confirmed_trades = []
        position = await self.db.get_position()
        await self.rpc.conn.log_in(position.fingerprint)
        for order in await self.db.get_order(position):
            trade = await self.rpc.conn.get_offer(order.trade_id)
            if TradeStatus(trade.status) == TradeStatus.CONFIRMED:
                log.info("trade %s confirmed!", order.trade_id)
                confirmed_trades.append(order)

        for order in confirmed_trades:
            await self._create_trade(*position.grid.flip(order.base_delta, order.quote_delta))
            await self.db.delete_order(order)
        await self.db.conn.commit()
