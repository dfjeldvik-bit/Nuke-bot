"""
KORAI Rate Limit Handler
Made by laxzytbh
"""

import asyncio
import time


class RateLimitHandler:
    def __init__(self):
        self.buckets = {}
        self.global_reset = 0
    
    async def wait_if_ratelimited(self, bucket: str = "default"):
        now = time.time()
        
        if now < self.global_reset:
            wait = self.global_reset - now
            await asyncio.sleep(wait)
        
        if bucket in self.buckets:
            reset_time = self.buckets[bucket]
            if now < reset_time:
                wait = reset_time - now
                await asyncio.sleep(wait)
    
    def update_bucket(self, bucket: str, retry_after: float):
        self.buckets[bucket] = time.time() + retry_after
    
    def update_global(self, retry_after: float):
        self.global_reset = time.time() + retry_after