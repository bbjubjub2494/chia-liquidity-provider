import dataclasses

import aiohttp
from chia.wallet.trading.offer import Offer


@dataclasses.dataclass
class Api:
    base_url: str

    async def post_offer(self, offer: Offer) -> None:
        async with (
            aiohttp.ClientSession() as session,
            session.post(f"{self.base_url}/offers", json={"offer": offer.to_bech32()}) as rep,
        ):
            if not rep.ok:
                raise RuntimeError(rep.reason)


mainnet = Api("https://api.dexie.space/v1")
testnet = Api("https://api-testnet.dexie.space/v1")
