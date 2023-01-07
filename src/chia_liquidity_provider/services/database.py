import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import aiomisc
import aiosqlite
import xdg

from chia_liquidity_provider.abc import DatabaseServiceBase
from chia_liquidity_provider.types.job import JobTableMixin
from chia_liquidity_provider.types.order import OrderTableMixin
from chia_liquidity_provider.types.position import PositionTableMixin

DEFAULT_STATE_DIRECTORY = xdg.xdg_state_home() / "clp"


class DatabaseService(aiomisc.Service, PositionTableMixin, OrderTableMixin, JobTableMixin, DatabaseServiceBase):
    """
    Mediate access to the database
    """

    _conn: aiosqlite.Connection
    _location: Path

    def __init__(self, position_id: str = "default", state_dir: Optional[Path] = None, **kwargs: Any):
        super().__init__(**kwargs)

        if state_dir is None:
            self._location = DEFAULT_STATE_DIRECTORY
        else:
            self._location = state_dir

        self._location.mkdir(parents=True, exist_ok=True)

        if "/" in position_id:
            raise ValueError("bad position_id")
        self._location /= f"{position_id}.sqlite"

    async def start(self) -> None:
        self._conn = await aiosqlite.connect(self._location)
        self._conn.row_factory = aiosqlite.Row
        await self._start_hook()

    async def stop(self, exception: Optional[Exception] = None) -> None:
        await super().stop(exception)
        await self._conn.close()

    @property
    def conn(self) -> aiosqlite.Connection:
        return self._conn
