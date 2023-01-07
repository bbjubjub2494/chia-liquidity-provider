import copy
import importlib.resources
import json
from unittest.mock import Mock

import pytest
from chia.rpc.wallet_rpc_client import WalletRpcClient
from chia.types.blockchain_format.coin import Coin
from chia.types.blockchain_format.sized_bytes import bytes32
from chia.util.ints import uint32, uint64
from chia.wallet.trade_record import TradeRecord
from chia.wallet.trading.offer import Offer

from liquidity import LiquidityCurve, Pricing, TradeManager, dexie_api, hashgreen_api
from liquidity.utils import TDBX, XCH, Asset


@pytest.fixture
def dexie():
    return Mock(spec=dexie_api.testnet)


@pytest.fixture
def hashgreen():
    return Mock(spec=hashgreen_api.mainnet)


@pytest.fixture
def state_repo():
    state_repo = Mock(spec=TradeManager.StateRepository)
    st = None

    async def load():
        return st

    async def store(state):
        nonlocal st
        st = state

    state_repo.load = Mock(side_effect=load)
    state_repo.store = Mock(side_effect=store)
    return state_repo


@pytest.fixture
def test_data():
    with importlib.resources.open_text("tests", "testdata.json") as f:
        return json.load(f)


@pytest.fixture
def select_coins(test_data):
    n = 0
    coins = [Coin.from_json_dict(c) for c in test_data["selected_coins"]]

    async def select_coins(wallet_id, amount, excluded_coins):
        nonlocal n
        assert wallet_id == 1
        assert amount == 100_000_000_000
        assert excluded_coins == coins[:n]
        if n < len(coins):
            coin = coins[n]
            n += 1
            return [coin]
        else:
            raise ValueError(
                {
                    "error": "Transaction for 100000000000 is greater than spendable balance of 0. There may be other transactions pending or our minimum coin amount is too high.",
                    "success": False,
                }
            )

    return select_coins


@pytest.fixture
def create_offer_for_ids(test_data):
    n = 0
    results = test_data["created_offers"]

    async def create_offer_for_ids(offer_dict):
        nonlocal n
        assert offer_dict[1] == -100_000_000_000
        if n < len(results):
            offer, traderec = results[n]
            n += 1
        else:
            raise NotImplementedError("create_offer_for_ids")
        offer = Offer.from_bech32(offer)
        offered, requested, infos = offer.summary()
        assert int(offer_dict[2]) == requested[TDBX.asset_id.hex()]
        return offer, TradeRecord.from_json_dict(traderec)

    return create_offer_for_ids


@pytest.fixture
def create_offer_for_ids_2(test_data):
    result = test_data["created_offer_2"]

    async def create_offer_for_ids(offer_dict):
        assert offer_dict == {1: 100_000_000_000, 2: -5_867}
        offer, traderec = result
        offer = Offer.from_bech32(offer)
        offered, requested, infos = offer.summary()
        assert offered == {TDBX.asset_id.hex(): 5_867}
        assert requested == {"xch": 100_000_000_000}
        return offer, TradeRecord.from_json_dict(traderec)

    return create_offer_for_ids


@pytest.fixture
def create_offer_for_ids_3(test_data):
    result = test_data["created_offer_3"]

    async def create_offer_for_ids(offer_dict):
        assert offer_dict == {1: -100_000_000_000, 2: 6_138}
        offer, traderec = result
        offer = Offer.from_bech32(offer)
        offered, requested, infos = offer.summary()
        assert offered == {"xch": 100_000_000_000}
        assert requested == {TDBX.asset_id.hex(): 6_138}
        return offer, TradeRecord.from_json_dict(traderec)

    return create_offer_for_ids


@pytest.fixture
def get_all_offers(test_data):
    data = test_data["created_offers"]

    async def get_all_offers(start=0, end=50, *, exclude_taken_offers):
        assert exclude_taken_offers
        return [TradeRecord.from_json_dict(t) for _, t in data[start:end]]

    return get_all_offers


@pytest.fixture
def get_offer_1(test_data):
    data = test_data["get_offer_1"]

    async def get_offer(trade_id):
        return TradeRecord.from_json_dict(data[trade_id.hex()])

    return get_offer


@pytest.fixture
def get_offer_2(test_data):
    data = test_data["get_offer_2"]

    async def get_offer(trade_id):
        return TradeRecord.from_json_dict(data[trade_id.hex()])

    return get_offer


@pytest.fixture
def get_offer_3(test_data):
    data = test_data["get_offer_3"]

    async def get_offer(trade_id):
        return TradeRecord.from_json_dict(data[trade_id.hex()])

    return get_offer


async def get_synced():
    return True


async def get_logged_in_fingerprint():
    return 1765569812


async def log_in(fingerprint):
    assert fingerprint == 1765569812
    return {"fingerprint": fingerprint}


@pytest.fixture
def expected_trades():
    return {
        bytes32.from_hexstr(s)
        for s in [
            "0d16cde4e76034169f74e5bf880a599eae6dc69b5aa0c2b5f11febe07bfa4fd1",
            "0153d425c3d3b6e2252f135dd4fcd3a55fdff16c4d7cae5b93892b0a7b220443",
            "306bc994d9a08cd7522d122ea2edaf47883b6989e69093200bad744dd4c08ac6",
            "859968a5d3a3b4248391ede192d1e57ebe8684fbba0fe7268bbda492e178f744",
            "c4dce0199a5e8684039dd118ac0b088b729c91942082ccd05b7391ab26a68ad0",
            "d284f8d00a1a40f804d073ec75c2c4b0e4f29d157bea4ea3800b8bfad297aef9",
            "682bfd0725630c06401c5c2a951f6bb17baf6b744313b9ffd819ffe18b14b547",
            "f353d17c36af4aa4d76218020400b689e02295bb07b7af1c32d247ef7bba0ab7",
            "e8008a35f716dd756d7e3c0e8d8264de39c92231513b778896dc119793e93b39",
            "c00da8b0f6c9ad178212536a83e2ec739b9f0d7b879b8aefc3ab5b88386175d5",
            "60ceb2d5bdb0b0472544b81e04494bac120ab51f64aca77f1023f836e13e530e",
            "ddc324c55a8304a7af7406b483f7bcbf772047c3b92b15acd6d4bfc2107dc063",
            "c6b26207771e725b30a2822f7170a8bf860e494a77b18c9181b80fa96fabc6de",
            "b507da53a442f7b33976db347e917687bf55249782d52460b2c8c42e8b3db1eb",
            "521f99630ab261a3a38fdddd77d901b2549ab021445ae6fd420d853308cc60ed",
            "3bb30ac4655e8d99b06671bdb68cbcb3c81157a40e44e16be8b35b6db753e6e7",
            "b0fa6d85eab5b3c0a733c996013130acb2febff212f3e006e264d6be624935ba",
            "f11d1ccd90314a9a78ef2af00d1bde9dd3886f3237cea8b4ed3b7963435dac79",
            "dc954c28464829b4370dddd88adf760dc67925eb06bac35e9657e76693fa0049",
            "8da577a72cdce2b006789ec5e361f401e60862270ff812e9a13e438f25d94499",
        ]
    }


@pytest.mark.asyncio
async def test_coin_selection(select_coins, state_repo, dexie, hashgreen):
    wallet = Mock()
    wallet.select_coins = select_coins
    wallet.create_offer_for_ids = Mock(side_effect=NotImplementedError("create_offer_for_ids"))
    wallet.get_synced = get_synced
    wallet.get_logged_in_fingerprint = get_logged_in_fingerprint

    x_max = 2 * XCH
    p_min = 60 * TDBX / (1 * XCH)
    p_max = 200 * TDBX / (1 * XCH)
    curve = LiquidityCurve.make_out_of_range(x_max, p_min, p_max)
    with pytest.raises(NotImplementedError, match="create_offer_for_ids"):
        await TradeManager.from_scratch(
            XCH,
            TDBX,
            p_min,
            Pricing.make(curve, ".1" * XCH, x_max),
            wallet,
            state_repo,
            dexie,
            hashgreen,
        )


@pytest.mark.asyncio
async def test_coin_selection_toomuch(select_coins, state_repo, dexie, hashgreen):
    pytest.skip("FIXME")
    wallet = Mock()
    wallet.select_coins = select_coins
    wallet.create_offer_for_ids = Mock(side_effect=NotImplementedError("create_offer_for_ids"))
    wallet.get_synced = get_synced
    wallet.get_logged_in_fingerprint = get_logged_in_fingerprint

    x_max = 21 * XCH
    p_min = "600" * TDBX / (1 * XCH)
    p_max = "2000" * TDBX / (1 * XCH)
    curve = LiquidityCurve.make_out_of_range(x_max, p_min, p_max)
    with pytest.raises(ValueError):
        await TradeManager.from_scratch(
            XCH,
            TDBX,
            p_min,
            Pricing.make(curve, ".1" * XCH, x_max),
            wallet,
            state_repo,
            dexie,
            hashgreen,
        )


@pytest.mark.asyncio
async def test_create_offers(state_repo, select_coins, create_offer_for_ids, expected_trades, dexie, hashgreen):
    wallet = Mock()
    wallet.select_coins = select_coins
    wallet.create_offer_for_ids = create_offer_for_ids
    wallet.get_synced = get_synced
    wallet.get_logged_in_fingerprint = get_logged_in_fingerprint

    x_max = 2 * XCH
    p_min = 60 * TDBX / (1 * XCH)
    p_max = 200 * TDBX / (1 * XCH)
    curve = LiquidityCurve.make_out_of_range(x_max, p_min, p_max)
    trade_manager = await TradeManager.from_scratch(
        XCH,
        TDBX,
        0,
        Pricing.make(curve, ".1" * XCH, x_max),
        wallet,
        state_repo,
        dexie,
        hashgreen,
    )

    state_repo.store.assert_called
    assert (await state_repo.load()).open_trades.keys() == expected_trades


@pytest.mark.asyncio
async def test_existing_offers(state_repo, select_coins, get_all_offers, dexie, hashgreen):
    pytest.skip("FIXME")
    wallet = Mock()
    wallet.select_coins = select_coins
    wallet.get_all_offers = get_all_offers

    x_max = 2 * XCH
    p_min = 60 * TDBX / (1 * XCH)
    p_max = 200 * TDBX / (1 * XCH)
    curve = LiquidityCurve.make_out_of_range(x_max, p_min, p_max)
    trade_manager = await TradeManager.from_existing_offers(wallet, curve, state_repo)
    state_repo.store.assert_called_with(trade_manager.state)


@pytest.mark.asyncio
async def test_poll_offers_negative(
    state_repo,
    select_coins,
    create_offer_for_ids,
    get_offer_1,
    expected_trades,
    dexie,
    hashgreen,
):
    wallet = Mock()
    wallet.select_coins = select_coins
    wallet.create_offer_for_ids = create_offer_for_ids
    wallet.get_synced = get_synced
    wallet.get_offer = get_offer_1
    wallet.get_logged_in_fingerprint = get_logged_in_fingerprint

    x_max = 2 * XCH
    p_min = 60 * TDBX / (1 * XCH)
    p_max = 200 * TDBX / (1 * XCH)
    curve = LiquidityCurve.make_out_of_range(x_max, p_min, p_max)
    trade_manager = await TradeManager.from_scratch(
        XCH,
        TDBX,
        0,
        Pricing.make(curve, ".1" * XCH, x_max),
        wallet,
        state_repo,
        dexie,
        hashgreen,
    )

    state_repo.store.assert_called
    assert (await state_repo.load()).open_trades.keys() == expected_trades


@pytest.mark.asyncio
async def test_poll_offers_positive(
    state_repo,
    select_coins,
    create_offer_for_ids,
    create_offer_for_ids_2,
    get_offer_2,
    expected_trades,
    dexie,
    hashgreen,
):
    wallet = Mock()
    wallet.select_coins = select_coins
    wallet.create_offer_for_ids = create_offer_for_ids
    wallet.get_synced = get_synced
    wallet.get_logged_in_fingerprint = get_logged_in_fingerprint
    wallet.log_in = log_in
    wallet.get_offer = get_offer_2

    x_max = 2 * XCH
    p_min = 60 * TDBX / (1 * XCH)
    p_max = 200 * TDBX / (1 * XCH)
    curve = LiquidityCurve.make_out_of_range(x_max, p_min, p_max)
    trade_manager = await TradeManager.from_scratch(
        XCH,
        TDBX,
        0,
        Pricing.make(curve, ".1" * XCH, x_max),
        wallet,
        state_repo,
        dexie,
        hashgreen,
    )

    wallet.create_offer_for_ids = create_offer_for_ids_2
    await trade_manager.check_open_trades()
    expected_trades.remove(bytes32.from_hexstr("3bb30ac4655e8d99b06671bdb68cbcb3c81157a40e44e16be8b35b6db753e6e7"))
    expected_trades.add(bytes32.from_hexstr("3f4cea32579aeac6a5d8a1b16b597028ffc2f81f2efe61cba257c0fe88687805"))
    state_repo.store.assert_called
    assert (await state_repo.load()).open_trades.keys() == expected_trades


@pytest.mark.asyncio
async def test_flip_offer(
    state_repo,
    select_coins,
    create_offer_for_ids,
    create_offer_for_ids_2,
    create_offer_for_ids_3,
    get_offer_2,
    get_offer_3,
    expected_trades,
    dexie,
    hashgreen,
):
    wallet = Mock()
    wallet.select_coins = select_coins
    wallet.create_offer_for_ids = create_offer_for_ids
    wallet.get_synced = get_synced
    wallet.get_logged_in_fingerprint = get_logged_in_fingerprint
    wallet.log_in = log_in
    wallet.get_offer = get_offer_2

    x_max = 2 * XCH
    p_min = 60 * TDBX / (1 * XCH)
    p_max = 200 * TDBX / (1 * XCH)
    curve = LiquidityCurve.make_out_of_range(x_max, p_min, p_max)
    trade_manager = await TradeManager.from_scratch(
        XCH,
        TDBX,
        0,
        Pricing.make(curve, ".1" * XCH, x_max),
        wallet,
        state_repo,
        dexie,
        hashgreen,
    )

    wallet.create_offer_for_ids = create_offer_for_ids_2
    await trade_manager.check_open_trades()

    wallet.get_offer = get_offer_3
    wallet.create_offer_for_ids = create_offer_for_ids_3
    await trade_manager.check_open_trades()

    expected_trades.remove(bytes32.from_hexstr("3bb30ac4655e8d99b06671bdb68cbcb3c81157a40e44e16be8b35b6db753e6e7"))
    expected_trades.add(bytes32.from_hexstr("453240bff4a250eeb7d4ebc53700585b79e4daf7cfca162db7393778a0688b28"))
    state_repo.store.assert_called
    assert (await state_repo.load()).open_trades.keys() == expected_trades
