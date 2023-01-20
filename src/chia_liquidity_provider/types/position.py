import json
from dataclasses import dataclass

from chia.util.ints import uint32

from chia_liquidity_provider.abc import DatabaseServiceBase

from .grid import Grid


@dataclass(frozen=True)
class Position:
    """
    State of a liquidity position.

    Currently, there is one database per position, so the table will contain at most one row.
    """

    TABLE_NAME = "position"
    fingerprint: int
    base_asset_wallet_id: uint32
    quote_asset_wallet_id: uint32
    grid: Grid


class PositionTableMixin(DatabaseServiceBase):
    async def _start_hook(self) -> None:
        await super()._start_hook()
        fields = ",".join(
            [
                "fingerprint INTEGER NOT NULL",
                "base_asset_wallet_id INTEGER NOT NULL",
                "quote_asset_wallet_id INTEGER NOT NULL",
                "grid TEXT NOT NULL",  # as JSON
            ]
        )
        await self.conn.execute(f"CREATE TABLE IF NOT EXISTS {Position.TABLE_NAME}({fields})")

    async def init_position(self, position: Position) -> None:
        await self.conn.execute(
            f"INSERT OR IGNORE INTO {Position.TABLE_NAME} VALUES(?, ?, ?, ?)",
            (
                position.fingerprint,
                int(position.base_asset_wallet_id),
                int(position.quote_asset_wallet_id),
                json.dumps(position.grid.to_json_dict()),
            ),
        )

    async def get_position(self) -> Position:
        async with self.conn.execute(f"SELECT * FROM {Position.TABLE_NAME}") as cursor:
            for row in await cursor.fetchall():
                return Position(
                    fingerprint=row["fingerprint"],
                    base_asset_wallet_id=uint32(row["base_asset_wallet_id"]),
                    quote_asset_wallet_id=uint32(row["quote_asset_wallet_id"]),
                    grid=Grid.from_json_dict(json.loads(row["grid"])),
                )
        raise RuntimeError("no position found")
