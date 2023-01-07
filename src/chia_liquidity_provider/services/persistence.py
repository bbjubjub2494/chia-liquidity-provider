import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence, Set

import aiomisc
import aiomisc.service.base

from chia_liquidity_provider.types import Job

from .database import DatabaseService


class PersistenceService(aiomisc.service.base.TaskStoreBase, aiomisc.Service):
    """
    Store jobs for eventual execution, crash-resiliently.

    Once a job is defered, it will run to completion at least once, even if
    the application crashes in the meantime.
    """

    _handlers: Dict[str, Callable[[Any], Awaitable[Any]]]
    _db: DatabaseService
    _cond: asyncio.Condition
    _busy_jobs_index: Set[int]

    def __init__(self, db: DatabaseService, **kwargs: Any):
        super().__init__(**kwargs)
        self._handlers = {}
        self._db = db
        self._cond = asyncio.Condition()
        self._busy_jobs_index = set()

    async def start(self) -> None:
        self.create_task(self._loop())

    def register(
        self,
        handler_name: str,
        function: Callable[[Any], Awaitable[Any]],
    ) -> None:
        """
        Bind the function to be invoked when a job specifies the given handler name.
        """
        if not isinstance(handler_name, str):
            raise ValueError(f"duplicate callback: {handler_name!r}")
        self._handlers[handler_name] = function

    async def defer(self, handler_name: str, params: Any) -> None:
        """
        Create a job for later execution.

        params will be passed to the handler function.
        """
        async with self._cond:
            await self._db.add_job(Job(handler_name, params))
            self._cond.notify()

    async def _process(self, job: Job) -> None:
        try:
            await self._handlers[job.handler_name](job.params)
        finally:
            async with self._cond:
                await self._db.remove_job(job)
                assert job.oid is not None
                self._busy_jobs_index.remove(job.oid)

    async def _loop(self) -> None:
        await self._db.start_event.wait()

        while True:
            async with self._cond:
                ready_jobs = [job for job in await self._db.get_jobs() if job.oid not in self._busy_jobs_index]
                if not ready_jobs:
                    await self._cond.wait()

            for job in ready_jobs:
                assert job.oid is not None
                self._busy_jobs_index.add(job.oid)
                self.create_task(self._process(job))
