from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.security.utils import get_authorization_scheme_param


router = APIRouter()


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket) -> None:
    token = websocket.app.state.settings.server.auth_token
    if token:
        scheme, credentials = get_authorization_scheme_param(websocket.headers.get("Authorization"))
        query_token = websocket.query_params.get("token")
        if not ((scheme.lower() == "bearer" and credentials == token) or query_token == token):
            await websocket.close(code=1008)
            return

    await websocket.accept()
    orchestrator = websocket.app.state.orchestrator
    try:
        while True:
            payload = await websocket.receive_json()
            message = str(payload.get("message", "")).strip()
            session_id = str(payload.get("session_id", "default"))
            if not message:
                await websocket.send_json({"type": "error", "message": "message is required"})
                continue
            try:
                async for chunk in orchestrator.stream(message, session_id=session_id):
                    await websocket.send_json({"type": "token", "content": chunk})
                await websocket.send_json({"type": "done"})
            except Exception as exc:
                await websocket.send_json({"type": "error", "message": str(exc)})
    except WebSocketDisconnect:
        return
