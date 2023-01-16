import dataclasses
import hashlib
import json
import time

import aiohttp
import secp256k1
from chia.types.blockchain_format.sized_bytes import bytes32
from chia.wallet.trading.offer import Offer


@dataclasses.dataclass(frozen=True)
class Event:
    "A nostr event per NIP-01"
    pubkey: bytes32
    created_at: int
    kind: int
    tags: list
    content: str
    sig: bytes

    @property
    def id(self) -> bytes32:
        return bytes32(self._compute_id(self.pubkey, self.created_at, self.kind, self.tags, self.content))

    @staticmethod
    def _compute_id(pubkey: bytes32, created_at: int, kind: int, tags: list, content: str) -> bytes:
        payload = json.dumps([0, pubkey.hex(), created_at, kind, tags, content], separators=(",", ":"))
        return hashlib.sha256(payload.encode()).digest()

    @classmethod
    def make(cls, privkey: secp256k1.PrivateKey, created_at: int, kind: int, tags: list, content: str) -> "Event":
        pubkey0 = privkey.pubkey.serialize()
        assert pubkey0[0] in (2, 3)  # BIP-340
        pubkey = bytes32(pubkey0[1:])
        sig = privkey.schnorr_sign(cls._compute_id(pubkey, created_at, kind, tags, content), None, raw=True)
        return cls(pubkey, created_at, kind, tags, content, sig)

    def to_json_dict(self) -> dict:
        return dict(
            id=self.id.hex(),
            pubkey=self.pubkey.hex(),
            created_at=self.created_at,
            kind=self.kind,
            tags=self.tags,
            content=self.content,
            sig=self.sig.hex(),
        )


@dataclasses.dataclass
class Api:
    """
    Adapter to post offers to  Andreas Greimel's Nostr Dex

    https://nostr-dex.vercel.app
    """

    relay_url: str

    async def post_offer(self, offer: Offer) -> None:
        privkey = secp256k1.PrivateKey()  # throwaway
        event = Event.make(privkey=privkey, created_at=int(time.time()), kind=8444, tags=[], content=offer.to_bech32())
        async with (
            aiohttp.ClientSession() as session,
            session.ws_connect(self.relay_url) as socket,
        ):
            await socket.send_str(json.dumps(["EVENT", event.to_json_dict()]))
            rep = json.loads((await socket.receive()).data)
            if not rep[2]:
                raise RuntimeError(rep[3])


mainnet = Api("wss://nostr.8e23.net/")
