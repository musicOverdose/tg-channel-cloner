import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from backend.app.security import decode_access_token
from backend.app.workers.job_manager import job_manager

logger = logging.getLogger("telegram_cloner.ws")
router = APIRouter(tags=["websocket"])


@router.websocket("/api/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(None),
):
    # Verify token
    if not token and "access_token" in websocket.cookies:
        token = websocket.cookies.get("access_token")

    if not token or not decode_access_token(token):
        await websocket.close(code=1008)  # Policy Violation
        return

    await websocket.accept()
    queue = asyncio.Queue()
    job_manager.register_ws_listener(queue)

    try:
        # Keep sending updates from queue to websocket
        while True:
            # Wait for either an event to send or a message from client
            done, pending = await asyncio.wait(
                [
                    asyncio.create_task(queue.get()),
                    asyncio.create_task(websocket.receive_text()),
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()

            for task in done:
                res = task.result()
                if isinstance(res, dict):  # Item from queue
                    await websocket.send_text(json.dumps(res))
                elif isinstance(res, str):  # Ping/pong from client
                    if res == "ping":
                        await websocket.send_text(json.dumps({"type": "PONG"}))

    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except Exception as exc:
        logger.warning(f"WebSocket client error: {exc}")
    finally:
        job_manager.unregister_ws_listener(queue)
