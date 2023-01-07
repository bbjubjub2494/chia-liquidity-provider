import os
import pathlib
from decimal import Decimal, localcontext
from typing import Optional, Union

import aiomisc
from chia.rpc.wallet_rpc_client import WalletRpcClient
from chia.types.blockchain_format.sized_bytes import bytes32
from chia.util.config import load_config
from chia.util.default_root import DEFAULT_ROOT_PATH
from chia.util.ints import uint16, uint32, uint64


class WalletRpcClientService(aiomisc.Service):
    """
    Mediate access to the chia wallet rpc interface
    """

    _conn: WalletRpcClient

    def __init__(self, fingerprint: Optional[int] = None):
        self._fingerprint = fingerprint

    async def start(self) -> None:
        root_path = pathlib.Path(os.environ.get("CHIA_ROOT", DEFAULT_ROOT_PATH))
        config = load_config(root_path, "config.yaml")
        self._conn = await WalletRpcClient.create("localhost", config["wallet"]["rpc_port"], root_path, config)
        fingerprint = self._fingerprint
        if fingerprint is not None:
            rep = await self._conn.log_in(fingerprint)
            if rep["success"] is False:
                raise Exception("error logging in", rep)

    async def stop(self, exc: Optional[Exception] = None):
        await super().stop(exc)
        self._conn.close()
        await self._conn.await_closed()

    @property
    def conn(self) -> WalletRpcClient:
        return self._conn
