"""
KORAI Request Queue
Made by laxzytbh
"""

import asyncio
from typing import Callable, List, Any


class RequestQueue:
    def __init__(self, max_concurrent: int = 10):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.max_concurrent = max_concurrent
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        async with self.semaphore:
            return await func(*args, **kwargs)
    
    async def execute_many(self, funcs: List[tuple]) -> List[Any]:
        tasks = []
        for func, args, kwargs in funcs:
            task = self.execute(func, *args, **kwargs)
            tasks.append(task)
        return await asyncio.gather(*tasks, return_exceptions=True)