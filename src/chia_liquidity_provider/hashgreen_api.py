import dataclasses

import aiohttp
from chia.wallet.trade_record import TradeRecord
from chia.wallet.trading.offer import Offer


@dataclasses.dataclass
class Api:
    base_url: str

    async def post_offer(self, tr: TradeRecord) -> None:
        async with (
            aiohttp.ClientSession() as session,
            session.post(f"{self.base_url}/orders", data={"offer": Offer.from_bytes(tr.offer).to_bech32()}) as rep,
        ):
            if not rep.ok:
                raise RuntimeError(rep.reason)


mainnet = Api("https://hash.green/api/v1")
