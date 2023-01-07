from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import ClassVar, Optional, Sequence, Union

from chia.types.blockchain_format.sized_bytes import bytes32
from chia.util.ints import uint32, uint64

MOJOS_PER_XCH = 1_000_000_000_000
MOJOS_PER_CAT = 1_000


@dataclass(frozen=True)
class Asset:
    asset_id: Optional[bytes32]

    @property
    def mojos_per_unit(self):
        if self.asset_id is None:
            return MOJOS_PER_XCH
        else:
            return MOJOS_PER_CAT

    def __rmul__(self, amt: Union[int, str, Decimal]) -> uint64:
        with localcontext():
            return uint64(Decimal(amt) * self.mojos_per_unit)

    XCH: ClassVar["Asset"]
    USDS: ClassVar["Asset"]
    TDBX: ClassVar["Asset"]


Asset.XCH = Asset(None)

# Stably USD
Asset.USDS = Asset(
    bytes32.from_hexstr("6d95dae356e32a71db5ddcb42224754a02524c615c5fc35f568c2af04774e589"),
)

# Testnet Dexie Bucks
Asset.TDBX = Asset(
    bytes32.from_hexstr("d82dd03f8a9ad2f84353cd953c4de6b21dbaaf7de3ba3f4ddd9abe31ecba80ad"),
)
