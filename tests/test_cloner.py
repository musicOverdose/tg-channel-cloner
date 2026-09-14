import pytest
import time
import asyncio
from backend.app.engine.rate_limiter import BotRateLimiter, RateLimiterRegistry


@pytest.mark.asyncio
async def test_bot_rate_limiter_backoff():
    limiter = BotRateLimiter(bot_id=1)
    # Simulate receiving Telegram 429 retry_after = 1 second
    limiter.handle_rate_limit(retry_after=1)

    t0 = time.time()
    await limiter.acquire()
    t1 = time.time()

    # Should have waited at least 1.0 second
    assert (t1 - t0) >= 1.0


@pytest.mark.asyncio
async def test_rate_limiter_per_bot_isolation():
    registry = RateLimiterRegistry()
    bot1 = await registry.get_limiter(bot_id=101)
    bot2 = await registry.get_limiter(bot_id=102)

    # Put bot 1 into a 2-second rate-limit backoff
    bot1.handle_rate_limit(retry_after=2)

    # Bot 2 acquire should complete immediately without delay!
    t0 = time.time()
    await bot2.acquire()
    t1 = time.time()

    assert (t1 - t0) < 0.2, "Bot 2 must not be delayed by Bot 1's rate limit"
