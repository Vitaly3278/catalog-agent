"""Фоновая очередь задач регистрации."""

import asyncio
from collections import deque

from app.agent import process_site

_queue: deque[int] = deque()
_lock = asyncio.Lock()
_running = False


async def enqueue_site(site_id: int) -> None:
    async with _lock:
        if site_id not in _queue:
            _queue.append(site_id)
    asyncio.create_task(_drain())


async def _drain() -> None:
    global _running
    async with _lock:
        if _running:
            return
        _running = True

    try:
        while True:
            async with _lock:
                if not _queue:
                    break
                site_id = _queue.popleft()
            try:
                await process_site(site_id)
            except Exception:
                pass
    finally:
        async with _lock:
            _running = False
            if _queue:
                asyncio.create_task(_drain())
