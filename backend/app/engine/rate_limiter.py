import asyncio
import logging
import time
from typing import Dict

logger = logging.getLogger("telegram_cloner.rate_limiter")


class BotRateLimiter:
    """Per-bot rate limiter with isolated 429 Too Many Requests backoff."""

    def __init__(self, bot_id: int):
        self.bot_id = bot_id
        self._lock = asyncio.Lock()
        self._backoff_until: float = 0.0
        self._last_call: float = 0.0
        self.min_interval: float = 0.05  # minimum spacing between API calls

    async def acquire(self):
        """Wait until this bot is allowed to make an API call."""
        async with self._lock:
            now = time.time()
            # If we are in a backoff period from a 429 response
            if self._backoff_until > now:
                wait_time = self._backoff_until - now
                logger.warning(
                    f"Bot {self.bot_id} in rate-limit backoff. Waiting {wait_time:.2f}s..."
                )
                await asyncio.sleep(wait_time)
                now = time.time()

            # Ensure minimum interval between requests
            elapsed = now - self._last_call
            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)

            self._last_call = time.time()

    def handle_rate_limit(self, retry_after: int):
        """Register a 429 retry_after received from Telegram."""
        now = time.time()
        # Add a 1.0s buffer for safety
        self._backoff_until = max(self._backoff_until, now + retry_after + 1.0)
        logger.warning(
            f"Bot {self.bot_id} hit Telegram 429! Backing off for {retry_after + 1.0}s until {self._backoff_until}"
        )


class RateLimiterRegistry:
    """Registry maintaining per-bot rate limiters."""

    def __init__(self):
        self._limiters: Dict[int, BotRateLimiter] = {}
        self._lock = asyncio.Lock()

    async def get_limiter(self, bot_id: int) -> BotRateLimiter:
        async with self._lock:
            if bot_id not in self._limiters:
                self._limiters[bot_id] = BotRateLimiter(bot_id)
            return self._limiters[bot_id]


rate_limiters = RateLimiterRegistry()
