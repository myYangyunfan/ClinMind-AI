"""1Hz Real-Time Bedside Telemetry Monitor WebSocket Feed.

One simulation tick loop per session (not per connection): the ticker advances
the physiology engine at exactly 1 Hz and broadcasts to every connected monitor,
so N clients watching the same session still see exactly 1 Hz progression.
"""

import asyncio
import time
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.session_manager import SessionStore
from app.models.entities import PatientStateEnum

router = APIRouter(tags=["Real-time Telemetry WebSocket"])

# Custom close code: the client should stop reconnecting and start a new case.
WS_SESSION_NOT_FOUND = 4404


class ConnectionManager:
    """Manages active WebSocket telemetry monitor client connections."""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        self.active_connections[session_id].add(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket):
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    def has_connections(self, session_id: str) -> bool:
        return bool(self.active_connections.get(session_id))

    async def broadcast_to_session(self, session_id: str, data: dict):
        if session_id in self.active_connections:
            dead_sockets = set()
            for ws in self.active_connections[session_id]:
                try:
                    await ws.send_json(data)
                except Exception:
                    dead_sockets.add(ws)
            for ws in dead_sockets:
                self.active_connections[session_id].discard(ws)


ws_manager = ConnectionManager()

# One asyncio task per session drives the 1 Hz simulation.
_ticker_tasks: Dict[str, asyncio.Task] = {}


def _start_ticker(session_id: str) -> None:
    existing = _ticker_tasks.get(session_id)
    if existing and not existing.done():
        return
    _ticker_tasks[session_id] = asyncio.create_task(_session_ticker(session_id))


async def _session_ticker(session_id: str) -> None:
    """Single 1 Hz simulation loop for one session, broadcast to all monitors."""
    store = SessionStore.get_instance()
    session = store.get_session(session_id)
    if not session:
        return
    try:
        while not session.is_finished:
            vitals = session.tick(dt=1.0)
            state = session.physiology_engine.get_state()
            countdown = session.physiology_engine.get_rupture_countdown()

            # check_spontaneous_events may call the (synchronous) LLM client;
            # run it off the event loop so telemetry never stalls behind it.
            spontaneous_msgs = await asyncio.to_thread(
                session.agent_engine.check_spontaneous_events,
                session.virtual_seconds,
                state
            )

            payload = {
                "type": "vitals_update",
                "timestamp": time.time(),
                "virtual_seconds": session.virtual_seconds,
                "vitals": vitals.model_dump(),
                "patient_state": state.value,
                "trust_level": round(session.agent_engine.state.patient_trust, 2),
                "family_anxiety": round(session.agent_engine.state.family_anxiety, 2),
                "alarms": list(session.agent_engine.state.active_critical_alarms),
                "rupture_countdown": countdown,
                "spontaneous_dialogues": [m.model_dump() for m in spontaneous_msgs]
            }

            await ws_manager.broadcast_to_session(session_id, payload)

            # Pause the simulation while no monitor is watching (e.g. page
            # refresh) so trainees are not penalized for reconnecting.
            if not ws_manager.has_connections(session_id):
                break

            await asyncio.sleep(1.0)
    except asyncio.CancelledError:
        raise
    except Exception as e:
        print(f"⚠️ [Telemetry] ticker for session {session_id} stopped: {e}")
    finally:
        _ticker_tasks.pop(session_id, None)


@router.websocket("/ws/vitals/{session_id}")
async def websocket_vitals_endpoint(websocket: WebSocket, session_id: str):
    """Subscribe a bedside monitor to a session's 1 Hz telemetry broadcast."""
    await ws_manager.connect(session_id, websocket)
    store = SessionStore.get_instance()
    session = store.get_session(session_id)

    if not session:
        await websocket.close(code=WS_SESSION_NOT_FOUND, reason="session not found")
        ws_manager.disconnect(session_id, websocket)
        return

    _start_ticker(session_id)

    try:
        # The per-session ticker drives all updates; this loop only keeps the
        # socket open and detects client disconnects.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(session_id, websocket)
