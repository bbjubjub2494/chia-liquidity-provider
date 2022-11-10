import asyncio
import dataclasses
import pathlib, shelve, os
import logging
import contextlib
from typing import Optional
from unittest.mock import Mock
from chia.types.blockchain_format.coin import Coin
from chia.wallet.trading.offer import Offer

from chia.util.ints import uint32, uint64
from chia.types.blockchain_format.sized_bytes import bytes32
from chia.rpc.wallet_rpc_client import WalletRpcClient
from chia.wallet.trading.trade_status import TradeStatus
from chia.wallet.trade_record import TradeRecord

from liquidity.utils import make_wallet_rpc_client, Asset, XCH, TDBX
from liquidity import LiquidityCurve, dexie_api, hashgreen_api

log = logging.getLogger(__name__)


@dataclasses.dataclass
class Pricing:
    base_amount: uint64
    quote_amounts: list[uint64]

    @classmethod
    def make(cls, curve, base_increment, base_total_amount):
        quote_amounts = []
        for x in range(0, base_total_amount + base_increment, base_increment):
            Δy = uint64(curve.f(x) - curve.f(x + base_increment))
            quote_amounts.append(Δy)
        return cls(base_amount=base_increment, quote_amounts=quote_amounts)

    def initial_orders(self, price):
        for i in range(1, len(self.quote_amounts)):
            if self.quote_amounts[i] / self.base_amount > price:
                yield -self.base_amount, self.quote_amounts[i - 1]
            else:
                yield self.base_amount, -self.quote_amounts[i]

    def flip(self, base_amount, quote_amount):
        if base_amount not in (-self.base_amount, self.base_amount):
            raise ValueError()
        if quote_amount < 0:
            quote_amount = self.quote_amounts[
                (i := self.quote_amounts.index(-quote_amount) - 1)
            ]
            if i < 0:
                raise ValueError()
        else:
            quote_amount = -self.quote_amounts[
                self.quote_amounts.index(quote_amount) + 1
            ]
        base_amount = -base_amount
        return base_amount, quote_amount


@dataclasses.dataclass
class TradeManager:
    @dataclasses.dataclass(frozen=True)
    class TradeData:
        encoded_offer: str

    @dataclasses.dataclass(frozen=True)
    class State:
        fingerprint: int
        base: Asset
        quote: Asset
        pricing: Pricing
        open_trades: dict[bytes32, "TradeData"]

    @dataclasses.dataclass
    class StateRepository:
        db: shelve.Shelf

        @classmethod
        @contextlib.asynccontextmanager
        async def open(cls):
            # TODO: lock file
            config_dir = pathlib.Path.home() / ".dexie-liquidity"
            config_dir.mkdir(parents=True, exist_ok=True)
            with shelve.open(os.fspath(config_dir / "state.shelf")) as db:
                yield cls(db)

        async def load(self) -> "TradeManager.State":
            return self.db["state"]

        async def store(self, state: "TradeManager.State"):
            self.db["state"] = state

    wallet: WalletRpcClient
    state_repo: StateRepository
    dexie: dexie_api.Api
    hashgreen: hashgreen_api.Api

    @classmethod
    async def from_scratch(
        cls,
        base: Asset,
        quote: Asset,
        p_init: float,
        pricing: Pricing,
        wallet: WalletRpcClient,
        state_repo: StateRepository,
        dexie: dexie_api.Api,
        hashgreen: hashgreen_api.Api,
    ) -> "TradeManager":
        while not await wallet.get_synced():
            log.info("waiting for wallet to be synced")
            await asyncio.sleep(30)

        fingerprint = await wallet.get_logged_in_fingerprint()
        st = TradeManager.State(
            fingerprint=fingerprint,
            open_trades={},
            base=base,
            quote=quote,
            pricing=pricing,
        )
        await state_repo.store(st)
        tm = cls(wallet=wallet, state_repo=state_repo, dexie=dexie, hashgreen=hashgreen)
        await tm._create_trades(p_init)
        return tm

    async def _create_trades(self, p_init):
        st = await self.state_repo.load()
        for o in st.pricing.initial_orders(p_init):
            await self._create_trade(*o)

    async def _create_trade(self, base_delta, quote_delta):
        st = await self.state_repo.load()
        offer, trade = await self.wallet.create_offer_for_ids(
            {st.base.wallet_id: base_delta, st.quote.wallet_id: quote_delta}
        )
        log.info("created trade %s", trade.trade_id)
        st.open_trades[trade.trade_id] = TradeManager.TradeData(offer.to_bech32())
        await self.dexie.post_offer(offer)
        await self.hashgreen.post_offer(offer)
        log.info("trade %s successfully posted", trade.trade_id)
        await self.state_repo.store(st)

    async def check_open_trades(self):
        confirmed_trades = []
        st = await self.state_repo.load()
        await self.wallet.log_in(st.fingerprint)
        for trade_id in st.open_trades:
            trade = await self.wallet.get_offer(trade_id)
            if TradeStatus(trade.status) == TradeStatus.CONFIRMED:
                log.info("trade %s confirmed!", trade_id)
                confirmed_trades.append(trade_id)

        for trade_id in confirmed_trades:
            offer = Offer.from_bech32(st.open_trades[trade_id].encoded_offer)
            received = offer.get_requested_amounts()
            sent = offer.get_offered_amounts()
            # FIXME: assumption: base asset quantity = increment
            if received.keys() == {st.quote.asset_id} and sent.keys() == {
                st.base.asset_id
            }:
                await self._create_trade(
                    *st.pricing.flip(
                        -sent[st.base.asset_id], received[st.quote.asset_id]
                    )
                )
            elif received.keys() == {st.base.asset_id} and sent.keys() == {
                st.quote.asset_id
            }:
                await self._create_trade(
                    *st.pricing.flip(
                        received[st.base.asset_id], -sent[st.quote.asset_id]
                    )
                )
            st = await self.state_repo.load()
            del st.open_trades[trade_id]
            await self.state_repo.store(st)
