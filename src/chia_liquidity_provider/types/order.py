from dataclasses import dataclass
from typing import TYPE_CHECKING, Sequence

from chia.types.blockchain_format.sized_bytes import bytes32

from chia_liquidity_provider.abc import DatabaseServiceBase

if TYPE_CHECKING:
    from . import Position


@dataclass(frozen=True)
class Order:
    TABLE_NAME = "orders"
    trade_id: bytes32
    base_delta: int
    quote_delta: int


class OrderTableMixin(DatabaseServiceBase):
    async def _start_hook(self) -> None:
        await super()._start_hook()
        fields = ",".join(
            [
                "trade_id BLOB UNIQUE NOT NULL",
                "base_delta INTEGER NOT NULL",
                "quote_delta INTEGER NOT NULL",
                # No position foreign key since the position is locally unique
            ]
        )
        await self.conn.execute(f"CREATE TABLE IF NOT EXISTS {Order.TABLE_NAME}({fields})")

    async def insert_order(self, _: "Position", order: Order) -> None:
        await self.conn.execute(
            f"INSERT OR IGNORE INTO {Order.TABLE_NAME} VALUES(?, ?, ?)",
            (
                order.trade_id,
                order.base_delta,
                order.quote_delta,
            ),
        )

    async def get_order(self, _: "Position") -> Sequence[Order]:
        r = []
        async with self.conn.execute(f"SELECT * FROM {Order.TABLE_NAME}") as cursor:
            for row in await cursor.fetchall():
                r.append(Order(bytes32(row["trade_id"]), row["base_delta"], row["quote_delta"]))
        return r

    async def delete_order(self, order: Order) -> None:
        await self.conn.execute(
            f"DELETE FROM {Order.TABLE_NAME} WHERE trade_id = ?", (order.trade_id,)
        )
