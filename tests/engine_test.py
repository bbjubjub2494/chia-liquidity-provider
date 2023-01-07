import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import Mock

import aiohttp
import aiomisc
import pytest
from chia.consensus.coinbase import create_puzzlehash_for_pk
from chia.types.blockchain_format.sized_bytes import bytes32
from chia.util.bech32m import encode_puzzle_hash
from chia.util.ints import uint16, uint32, uint64
from chia.util.keychain import Keychain, KeyData, generate_mnemonic
from chia.wallet.derive_keys import master_sk_to_wallet_sk
from chia.wallet.trading.offer import Offer

from chia_liquidity_provider import Engine, Grid, LiquidityCurve, dexie_api, hashgreen_api
from chia_liquidity_provider.types import Asset

XCH = Asset.XCH
TRILLION = 1_000_000_000_000


@pytest.fixture
def dexie():
    return Mock(spec=dexie_api.testnet)


@pytest.fixture
def hashgreen():
    return Mock(spec=hashgreen_api.mainnet)


@pytest.fixture
def services(db, rpc):
    return [db, rpc]


@pytest.fixture
def switch_fingerprint(rpc):
    @aiomisc.asyncretry(max_tries=100, exceptions=(aiohttp.client_exceptions.ClientConnectorError,), pause=1)
    async def switch_fingerprint(fingerprint):
        rep = await rpc.conn.log_in(fingerprint)
        if rep["success"] is False:
            raise Exception("error logging in", rep)

    return switch_fingerprint


@pytest.fixture
def wait_until_synced(rpc):
    async def wait_until_synced():
        while not await rpc.conn.get_synced():
            pass

    return wait_until_synced


@pytest.fixture
def wait_until_settled(rpc):
    async def wait_until_settled(wallet_id):
        while True:
            for t in await rpc.conn.get_transactions(wallet_id):
                if not t.confirmed:
                    break
            else:
                break

    return wait_until_settled


@dataclass
class TestWallet:
    fingerprint: int
    cat: Asset


XCH_WALLET_ID = uint32(1)


@pytest.fixture
async def test_wallet(rpc, switch_fingerprint, wait_until_synced, wait_until_settled, chia_simulator):
    """
    generate a fresh set of wallets, funded with 1 XCH and a billion CATs.
    """
    mnemonic = generate_mnemonic()
    await rpc.conn.add_key(mnemonic.split())
    kd = KeyData.from_mnemonic(mnemonic)
    first_wallet_sk = master_sk_to_wallet_sk(kd.private_key, 0)
    dest = encode_puzzle_hash(create_puzzlehash_for_pk(first_wallet_sk.get_g1()), "txch")

    await switch_fingerprint(chia_simulator.farmer_fingerprint)
    await wait_until_synced()
    rep = await rpc.conn.create_new_cat_and_wallet(amount=2 * TRILLION)
    test_wallet_id = uint32(rep["wallet_id"])
    test_asset_id = bytes32.from_hexstr(rep["asset_id"])
    await rpc.conn.send_transaction(XCH_WALLET_ID, TRILLION, dest)
    await wait_until_settled(int(XCH_WALLET_ID))
    await rpc.conn.cat_spend(test_wallet_id, TRILLION, dest)
    await wait_until_settled(test_wallet_id)

    return TestWallet(fingerprint=kd.fingerprint, cat=Asset(test_asset_id))


async def test_coin_create_offers(
    test_wallet, rpc, switch_fingerprint, wait_until_synced, wait_until_settled, db, dexie, hashgreen
):
    await switch_fingerprint(test_wallet.fingerprint)
    await wait_until_settled(int(XCH_WALLET_ID))
    await wait_until_synced()

    rep = await rpc.conn.create_wallet_for_existing_cat(test_wallet.cat.asset_id)
    test_cat_wallet_id = uint32(rep["wallet_id"])

    while True:
        rep = await rpc.conn.get_wallet_balance(int(XCH_WALLET_ID))
        if rep["confirmed_wallet_balance"] == TRILLION:
            break
    while True:
        rep = await rpc.conn.get_wallet_balance(int(test_cat_wallet_id))
        if rep["confirmed_wallet_balance"] == TRILLION:
            break

    x_max = 1 * XCH
    p_min = 60 * test_wallet.cat / (1 * XCH)
    p_max = 200 * test_wallet.cat / (1 * XCH)
    curve = LiquidityCurve.make_out_of_range(x_max, p_min, p_max)
    await Engine.from_scratch(
        XCH,
        test_wallet.cat,
        0.0,
        Grid.make(curve, ".1" * XCH, x_max),
        rpc,
        db,
        dexie,
        hashgreen,
    )

    rep = await rpc.conn.get_all_offers(exclude_taken_offers=True, file_contents=True)
    cat_amounts = []
    for tr in rep:
        offer = Offer.from_bytes(tr.offer)
        assert offer.get_offered_amounts() == {None: TRILLION // 10}
        assert offer.get_requested_amounts().keys() == {test_wallet.cat.asset_id}
        cat_amounts.append(offer.get_requested_amounts()[test_wallet.cat.asset_id])
    assert sorted(cat_amounts) == [6284, 6909, 7632, 8475, 9465, 10640, 12049, 13757, 15855, 18474]


async def test_cat_create_offers(
    test_wallet, rpc, switch_fingerprint, wait_until_synced, wait_until_settled, db, dexie, hashgreen
):
    await switch_fingerprint(test_wallet.fingerprint)
    await wait_until_settled(int(XCH_WALLET_ID))
    await wait_until_synced()

    rep = await rpc.conn.create_wallet_for_existing_cat(test_wallet.cat.asset_id)
    test_cat_wallet_id = uint32(rep["wallet_id"])

    while True:
        rep = await rpc.conn.get_wallet_balance(int(XCH_WALLET_ID))
        if rep["confirmed_wallet_balance"] == TRILLION:
            break
    while True:
        rep = await rpc.conn.get_wallet_balance(int(test_cat_wallet_id))
        if rep["confirmed_wallet_balance"] == TRILLION:
            break

    x_max = 1 * test_wallet.cat
    p_min = 60 * XCH / (1 * test_wallet.cat)
    p_max = 200 * XCH / (1 * test_wallet.cat)
    curve = LiquidityCurve.make_out_of_range(x_max, p_min, p_max)
    await Engine.from_scratch(
        test_wallet.cat,
        XCH,
        0.0,
        Grid.make(curve, ".1" * test_wallet.cat, x_max),
        rpc,
        db,
        dexie,
        hashgreen,
    )

    rep = await rpc.conn.get_all_offers(exclude_taken_offers=True, file_contents=True)
    xch_amounts = []
    for tr in rep:
        offer = Offer.from_bytes(tr.offer)
        assert offer.get_offered_amounts() == {test_wallet.cat.asset_id: 100}
        assert offer.get_requested_amounts().keys() == {XCH.asset_id}
        xch_amounts.append(offer.get_requested_amounts()[XCH.asset_id])
    assert sorted(xch_amounts) == [
        6284221146836,
        6909195830850,
        7632281055729,
        8475146351039,
        9465793543672,
        10640915108187,
        12049345045296,
        13757221709166,
        15855907225320,
        18474484484934,
    ]


async def test_coin_selection_toomuch(
    rpc, switch_fingerprint, wait_until_synced, wait_until_settled, test_wallet, db, dexie, hashgreen
):
    await switch_fingerprint(test_wallet.fingerprint)
    await wait_until_settled(int(XCH_WALLET_ID))

    x_max = 1.1 * XCH
    p_min = "600" * test_wallet.cat / (1 * XCH)
    p_max = "2000" * test_wallet.cat / (1 * XCH)
    curve = LiquidityCurve.make_out_of_range(x_max, p_min, p_max)
    with pytest.raises(ValueError):
        await Engine.from_scratch(
            XCH,
            test_wallet.cat,
            0.0,
            Grid.make(curve, ".1" * XCH, x_max),
            rpc,
            db,
            dexie,
            hashgreen,
        )


async def test_flip_offer(
    test_wallet, rpc, switch_fingerprint, wait_until_synced, wait_until_settled, db, dexie, hashgreen, chia_simulator
):
    await switch_fingerprint(test_wallet.fingerprint)
    await wait_until_settled(int(XCH_WALLET_ID))
    await wait_until_synced()

    rep = await rpc.conn.create_wallet_for_existing_cat(test_wallet.cat.asset_id)
    test_cat_wallet_id = uint32(rep["wallet_id"])

    x_max = 1 * XCH
    p_min = 60 * test_wallet.cat / (1 * XCH)
    p_max = 200 * test_wallet.cat / (1 * XCH)
    curve = LiquidityCurve.make_out_of_range(x_max, p_min, p_max)
    tm = await Engine.from_scratch(
        XCH,
        test_wallet.cat,
        0.0,
        Grid.make(curve, ".1" * XCH, x_max),
        rpc,
        db,
        dexie,
        hashgreen,
    )

    rep = await rpc.conn.get_all_offers(exclude_taken_offers=True, file_contents=True)
    best_offer = Offer.from_bytes(rep[0].offer)
    for tr in rep[1:]:
        offer = Offer.from_bytes(tr.offer)
        if (
            offer.get_requested_amounts()[test_wallet.cat.asset_id]
            < best_offer.get_requested_amounts()[test_wallet.cat.asset_id]
        ):
            best_offer = offer
    assert best_offer.get_requested_amounts()[test_wallet.cat.asset_id] == 6284
    await switch_fingerprint(chia_simulator.farmer_fingerprint)
    await wait_until_synced()
    await rpc.conn.take_offer(best_offer)
    await wait_until_settled(int(XCH_WALLET_ID))
    await switch_fingerprint(test_wallet.fingerprint)
    while True:
        rep = await rpc.conn.get_wallet_balance(int(XCH_WALLET_ID))
        if rep["confirmed_wallet_balance"] != TRILLION:
            break
    await tm.check_open_trades()

    rep = await rpc.conn.get_all_offers(exclude_taken_offers=True, file_contents=True)
    summaries = []
    for tr in rep:
        offer = Offer.from_bytes(tr.offer)
        summary = {}
        for asset_id, amt in offer.get_offered_amounts().items():
            summary[asset_id] = amt
        for asset_id, amt in offer.get_requested_amounts().items():
            summary[asset_id] = -amt
        assert summary.keys() == {None, test_wallet.cat.asset_id}
        summary = summary[None], summary[test_wallet.cat.asset_id]
        summaries.append(summary)
    assert sorted(summaries) == [
        (-100000000000, 5740),
        (100000000000, -18474),
        (100000000000, -15855),
        (100000000000, -13757),
        (100000000000, -12049),
        (100000000000, -10640),
        (100000000000, -9465),
        (100000000000, -8475),
        (100000000000, -7632),
        (100000000000, -6909),
    ]
