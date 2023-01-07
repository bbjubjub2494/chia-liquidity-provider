import contextlib
import dataclasses
from decimal import Decimal, localcontext
from typing import Optional, Union

from chia.rpc.wallet_rpc_client import WalletRpcClient
from chia.types.blockchain_format.sized_bytes import bytes32
from chia.util.config import load_config
from chia.util.default_root import DEFAULT_ROOT_PATH
from chia.util.ints import uint32, uint64


@contextlib.asynccontextmanager
async def make_wallet_rpc_client(fingerprint: Optional[int] = None) -> WalletRpcClient:
    root_path = DEFAULT_ROOT_PATH
    config = load_config(root_path, "config.yaml")
    client = await WalletRpcClient.create("localhost", 9256, root_path, config)
    if fingerprint is not None:
        rep = await client.log_in(fingerprint)
        if rep["success"] is False:
            raise Exception("error logging in", rep)
    try:
        yield client
    finally:
        client.close()
        await client.await_closed()


MOJOS_PER_XCH = 1_000_000_000_000
MOJOS_PER_CAT = 1_000


@dataclasses.dataclass
class Asset:
    asset_id: Optional[bytes32]
    wallet_id: uint32

    @property
    def mojos_per_unit(self):
        if self.asset_id is None:
            return MOJOS_PER_XCH
        else:
            return MOJOS_PER_CAT

    def __rmul__(self, amt: Union[int, str, Decimal]) -> uint64:
        with localcontext():
            return uint64(Decimal(amt) * self.mojos_per_unit)


XCH = Asset(None, 1)

# Stably USD
USDS = Asset(
    bytes32.from_hexstr("6d95dae356e32a71db5ddcb42224754a02524c615c5fc35f568c2af04774e589"),
    2,
)

# Testnet Dexie Bucks
TDBX = Asset(
    bytes32.from_hexstr("d82dd03f8a9ad2f84353cd953c4de6b21dbaaf7de3ba3f4ddd9abe31ecba80ad"),
    2,
)
