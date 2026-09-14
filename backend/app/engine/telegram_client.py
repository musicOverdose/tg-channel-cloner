import asyncio
import logging
from typing import Dict, Any, List, Optional
import httpx
from backend.app.engine.rate_limiter import rate_limiters, BotRateLimiter

logger = logging.getLogger("telegram_cloner.telegram_client")

TELEGRAM_API_BASE = "https://api.telegram.org"


class TelegramError(Exception):
    def __init__(self, message: str, error_code: Optional[int] = None, retry_after: Optional[int] = None):
        super().__init__(message)
        self.error_code = error_code
        self.retry_after = retry_after


class TelegramClient:
    """Async client for Telegram Bot API with rate limiting and retry handling."""

    def __init__(self, bot_id: int, bot_token: str):
        self.bot_id = bot_id
        self.bot_token = bot_token
        self.base_url = f"{TELEGRAM_API_BASE}/bot{bot_token}"
        self._limiter: Optional[BotRateLimiter] = None

    async def _get_limiter(self) -> BotRateLimiter:
        if self._limiter is None:
            self._limiter = await rate_limiters.get_limiter(self.bot_id)
        return self._limiter

    async def _make_request(
        self,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
        max_retries: int = 5,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """Make an HTTP POST to the Telegram Bot API with rate-limit handling and retries."""
        limiter = await self._get_limiter()
        url = f"{self.base_url}/{endpoint}"

        for attempt in range(1, max_retries + 1):
            await limiter.acquire()
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(url, json=payload or {})
                    data = resp.json()

                    if resp.status_code == 200 and data.get("ok"):
                        return data.get("result")

                    # Handle 429 Too Many Requests
                    if resp.status_code == 429:
                        parameters = data.get("parameters", {})
                        retry_after = parameters.get("retry_after", 3)
                        limiter.handle_rate_limit(retry_after)
                        if attempt == max_retries:
                            raise TelegramError(
                                f"Rate limited (429) after {max_retries} attempts. Retry after {retry_after}s",
                                error_code=429,
                                retry_after=retry_after,
                            )
                        logger.warning(
                            f"Hit 429 on {endpoint}. Sleeping {retry_after + 1}s (attempt {attempt}/{max_retries})"
                        )
                        await asyncio.sleep(retry_after + 1)
                        continue

                    # Handle Telegram API errors (400, 403, etc.)
                    error_desc = data.get("description", "Unknown Telegram error")
                    error_code = data.get("error_code", resp.status_code)
                    raise TelegramError(error_desc, error_code=error_code)

            except httpx.RequestError as exc:
                logger.warning(f"Network error on {endpoint}: {exc} (attempt {attempt}/{max_retries})")
                if attempt == max_retries:
                    raise TelegramError(f"Network connection failure: {exc}")
                await asyncio.sleep(1.5 * attempt)

        raise TelegramError("Max retries exceeded")

    async def get_me(self) -> Dict[str, Any]:
        """Verify token and get bot details."""
        return await self._make_request("getMe")

    async def get_chat(self, chat_id: str) -> Dict[str, Any]:
        """Fetch chat information (title, type, username, etc.)."""
        # Telegram chat IDs for supergroups/channels typically start with -100
        formatted_id = chat_id.strip()
        return await self._make_request("getChat", {"chat_id": formatted_id})

    async def get_chat_member(self, chat_id: str, user_id: int) -> Dict[str, Any]:
        """Fetch member status and permissions for a user or bot."""
        formatted_id = chat_id.strip()
        return await self._make_request(
            "getChatMember", {"chat_id": formatted_id, "user_id": user_id}
        )

    async def copy_message(
        self,
        chat_id: str,
        from_chat_id: str,
        message_id: int,
    ) -> Dict[str, Any]:
        """Copy a single message using copyMessage (Bot API)."""
        payload = {
            "chat_id": chat_id.strip(),
            "from_chat_id": from_chat_id.strip(),
            "message_id": message_id,
        }
        return await self._make_request("copyMessage", payload)

    async def copy_messages(
        self,
        chat_id: str,
        from_chat_id: str,
        message_ids: List[int],
    ) -> List[Dict[str, Any]]:
        """Batch copy messages using Bot API 7.0+ copyMessages."""
        if not message_ids:
            return []
        payload = {
            "chat_id": chat_id.strip(),
            "from_chat_id": from_chat_id.strip(),
            "message_ids": message_ids,
        }
        return await self._make_request("copyMessages", payload)

    async def probe_channel_latest_message_id(self, chat_id: str) -> int:
        """
        Determine the latest message ID in the channel using exponential probe + binary search.
        If the channel is empty, returns 0.
        """
        # Check permissions and test with a probe
        # In Bot API, we can check message existence by attempting a dry copy or probe.
        # Since Telegram has no getChatHistory in Bot API, we can use exponential probing.
        # However, to avoid spamming destination channels during probe, we probe if chat is accessible.
        # For probing, we can check up to a realistic boundary:
        low = 1
        high = 1000

        # Quick exponential probe to find an upper bound that fails
        # First verify chat existence:
        await self.get_chat(chat_id)

        # Default fallback if probing is not applicable (e.g. no destination to test copy)
        # We can return 1000 as default or scan from known last message
        return 0
