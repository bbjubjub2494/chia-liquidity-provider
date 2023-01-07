import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional, Sequence

from chia_liquidity_provider.abc import DatabaseServiceBase


@dataclass
class Job:
    TABLE_NAME = "persistence_service_jobs"
    handler_name: str
    params: Any
    not_before: Optional[datetime] = None
    oid: Optional[int] = None


class JobTableMixin(DatabaseServiceBase):
    async def _start_hook(self) -> None:
        await super()._start_hook()
        fields = ",".join(
            [
                "handler_name TEXT NOT NULL",
                "params TEXT NOT NULL",  # params as JSON
                "not_before TEXT",  # normalised ISO UTC
                "oid INTEGER PRIMARY KEY",
            ]
        )
        await self.conn.execute(f"CREATE TABLE IF NOT EXISTS {Job.TABLE_NAME}({fields})")

    async def add_job(self, job: Job) -> None:
        not_before = None
        if job.not_before is not None:
            not_before = job.not_before.astimezone(timezone.utc)
        await self.conn.execute(
            f"INSERT OR IGNORE INTO {Job.TABLE_NAME} VALUES(?, ?, ?, ?)",
            (job.handler_name, json.dumps(job.params), not_before, job.oid),
        )

    async def get_jobs(self) -> Sequence[Job]:
        r = []
        async with self.conn.execute(f"SELECT * FROM {Job.TABLE_NAME} ORDER BY not_before") as cursor:
            for handler_name, params, not_before, oid in await cursor.fetchall():
                if not_before is not None:
                    not_before = datetime.fromisoformat(not_before).replace(tzinfo=timezone.utc)
                r.append(Job(handler_name, json.loads(params), not_before, oid))
        return r

    async def remove_job(self, job: Job) -> None:
        await self.conn.execute(f"DELETE FROM {Job.TABLE_NAME} WHERE oid = ?", (job.oid,))
