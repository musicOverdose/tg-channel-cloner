from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.database import get_db
from backend.app.models import Bot, Job, User
from backend.app.schemas import BotCreate, BotUpdate, BotResponse, BotTestResponse
from backend.app.security import encrypt_token, decrypt_token, mask_token
from backend.app.engine.telegram_client import TelegramClient, TelegramError
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/api/bots", tags=["bots"])


def format_bot_response(bot: Bot) -> BotResponse:
    try:
        raw = decrypt_token(bot.token_encrypted)
        masked = mask_token(raw)
    except Exception:
        masked = "********"

    return BotResponse(
        id=bot.id,
        name=bot.name,
        bot_username=bot.bot_username,
        telegram_id=bot.telegram_id,
        masked_token=masked,
        is_active=bot.is_active,
        created_at=bot.created_at,
    )


@router.get("", response_model=List[BotResponse])
async def list_bots(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Bot).order_by(Bot.id.asc())
    result = await db.execute(stmt)
    bots = result.scalars().all()
    return [format_bot_response(b) for b in bots]


@router.post("", response_model=BotResponse)
async def create_bot(
    payload: BotCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    raw_token = payload.token.strip()
    if not raw_token or ":" not in raw_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Telegram Bot token format. Expected format: 123456789:ABCdef...",
        )

    # Validate token with Telegram getMe
    temp_client = TelegramClient(bot_id=0, bot_token=raw_token)
    try:
        me = await temp_client.get_me()
    except TelegramError as te:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Telegram token validation failed: {te}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not connect to Telegram API: {exc}",
        )

    bot_username = me.get("username")
    telegram_id = me.get("id")

    # Encrypt token at rest
    encrypted = encrypt_token(raw_token)
    new_bot = Bot(
        name=payload.name.strip() or f"Bot @{bot_username}",
        token_encrypted=encrypted,
        bot_username=bot_username,
        telegram_id=telegram_id,
        is_active=True,
    )
    db.add(new_bot)
    await db.commit()
    await db.refresh(new_bot)
    return format_bot_response(new_bot)


@router.put("/{bot_id}", response_model=BotResponse)
async def update_bot(
    bot_id: int,
    payload: BotUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    bot = await db.get(Bot, bot_id)
    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")

    if payload.name is not None:
        bot.name = payload.name.strip()
    if payload.is_active is not None:
        bot.is_active = payload.is_active

    if payload.token is not None and payload.token.strip():
        raw_token = payload.token.strip()
        temp_client = TelegramClient(bot_id=bot.id, bot_token=raw_token)
        try:
            me = await temp_client.get_me()
            bot.bot_username = me.get("username")
            bot.telegram_id = me.get("id")
            bot.token_encrypted = encrypt_token(raw_token)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to validate updated token: {exc}",
            )

    await db.commit()
    await db.refresh(bot)
    return format_bot_response(bot)


@router.delete("/{bot_id}")
async def delete_bot(
    bot_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    bot = await db.get(Bot, bot_id)
    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")

    # Check if any jobs use this bot
    stmt = select(Job).where(Job.bot_id == bot_id)
    res = await db.execute(stmt)
    linked_jobs = res.scalars().all()
    if linked_jobs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete bot: It is assigned to {len(linked_jobs)} existing job(s). Please reassign or delete those jobs first.",
        )

    await db.delete(bot)
    await db.commit()
    return {"status": "success", "message": f"Bot {bot_id} deleted successfully"}


@router.post("/{bot_id}/test", response_model=BotTestResponse)
async def test_bot(
    bot_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    bot = await db.get(Bot, bot_id)
    if not bot:
        return BotTestResponse(success=False, error="Bot not found")

    try:
        raw_token = decrypt_token(bot.token_encrypted)
        client = TelegramClient(bot_id=bot.id, bot_token=raw_token)
        me = await client.get_me()
        return BotTestResponse(
            success=True,
            bot_id=me.get("id"),
            bot_username=me.get("username"),
            first_name=me.get("first_name"),
        )
    except Exception as exc:
        return BotTestResponse(success=False, error=str(exc))
