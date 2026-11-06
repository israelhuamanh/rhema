import asyncio
import contextlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Blindaje de salidas estándar cuando corre como ejecutable sin consola en Windows
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
elif hasattr(sys.stdout, "reconfigure"):
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")
elif hasattr(sys.stderr, "reconfigure"):
    with contextlib.suppress(Exception):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Asegurar que el directorio raíz de rhema-engine esté en sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import uvicorn
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from src.audio_stream import AudioStream
from src.config import WS_HOST, WS_PORT
from src.db_manager import DBManager
from src.stt_engine import STTEngine
from src.verse_extractor import VerseExtractor


def safe_print(msg: str) -> None:
    """Imprime de forma segura sin fallar si no hay consola o si el encoding es limitado."""
    with contextlib.suppress(Exception):
        if sys.stdout:
            sys.stdout.write(msg + "\n")
            sys.stdout.flush()


class ConnectionManager:
    """Gestiona las conexiones WebSocket activas (StudioWindow, ProjectorWindow, etc.)."""

    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)

    async def send_personal(self, websocket: WebSocket, message: Dict[str, Any]) -> None:
        try:
            await websocket.send_text(json.dumps(message, ensure_ascii=False))
        except Exception:
            self.disconnect(websocket)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        if not self.active_connections:
            return
        payload_str = json.dumps(message, ensure_ascii=False)
        disconnected: List[WebSocket] = []
        for connection in list(self.active_connections):
            try:
                await connection.send_text(payload_str)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)


class RhemaEngineRuntime:
    """Orquestador principal de captura de audio, Vosk STT, extractor NLP y SQLite."""

    def __init__(self) -> None:
        self.db = DBManager()
        self.stt = STTEngine()
        self.audio = AudioStream()
        self.ws_manager = ConnectionManager()
        self._running = False
        self._audio_task: Optional[asyncio.Task] = None
        self.last_projected_verse: Optional[Dict[str, Any]] = None

    async def start(self) -> None:
        self._running = True
        try:
            self.audio.start(device_id=None)
            safe_print(
                f"[RhemaEngine] Captura de micrófono iniciada (ID={self.audio.current_device_id})."
            )
        except Exception as exc:
            safe_print(f"[RhemaEngine] Advertencia al iniciar micrófono: {exc}")

        self._audio_task = asyncio.create_task(self._audio_processing_loop())

    async def stop(self) -> None:
        self._running = False
        if self._audio_task is not None:
            self._audio_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._audio_task
        self.audio.stop()
        self.db.close()
        safe_print("[RhemaEngine] Motor detenido correctamente.")

    async def _audio_processing_loop(self) -> None:
        """
        Bucle asíncrono en segundo plano que lee bloques de audio sin bloquear el event loop,
        ejecuta Vosk STT, extrae citas bíblicas y emite eventos WebSocket en tiempo real.
        """
        last_partial = ""
        last_emitted_ref: Optional[str] = None
        recent_final_text = ""
        recent_final_ts = 0.0
        empty_reads = 0
        last_level_sent = -1

        while self._running:
            chunk = await asyncio.to_thread(self.audio.read_chunk, 0.2)
            if chunk is None:
                empty_reads += 1
                if empty_reads >= 15:
                    empty_reads = 0
                    devices = await asyncio.to_thread(
                        AudioStream.refresh_and_list_input_devices
                    )
                    if devices:
                        fallback_id = devices[0]["id"]
                        try:
                            await asyncio.to_thread(
                                self.audio.switch_device, fallback_id
                            )
                            self.stt.reset()
                            await self.ws_manager.broadcast(
                                {"event": "AUDIO_DEVICES_LIST", "payload": devices}
                            )
                            await self.ws_manager.broadcast(
                                {
                                    "event": "AUDIO_DEVICE_CHANGED",
                                    "payload": {"device_id": fallback_id},
                                }
                            )
                        except Exception:
                            pass
                await asyncio.sleep(0.01)
                continue

            empty_reads = 0

            # Emitir nivel de audio en vivo (vúmetro 0..100) si cambió significativamente
            lvl = self.audio.current_level
            if abs(lvl - last_level_sent) >= 2 or (lvl == 0 and last_level_sent != 0):
                last_level_sent = lvl
                await self.ws_manager.broadcast(
                    {
                        "event": "AUDIO_LEVEL",
                        "payload": {
                            "level": lvl,
                            "device_id": self.audio.current_device_id,
                        },
                    }
                )

            is_final, text = await asyncio.to_thread(self.stt.process_chunk, chunk)
            if not text:
                continue

            if text != last_partial:
                last_partial = text
                await self.ws_manager.broadcast(
                    {
                        "event": "TRANSCRIPTION_PARTIAL",
                        "payload": {"text": text},
                    }
                )

            # Evaluar extracción de cita bíblica (versículo único o rango, con memoria de capítulo activo)
            now_mono = asyncio.get_running_loop().time()
            combined_text = (
                f"{recent_final_text} {text}".strip()
                if (now_mono - recent_final_ts) <= 4.0 and recent_final_text
                else text
            )
            ctx_book = (
                str(self.last_projected_verse["book"])
                if self.last_projected_verse
                else None
            )
            ctx_chapter = (
                int(self.last_projected_verse["chapter"])
                if self.last_projected_verse
                else None
            )

            detected = (
                VerseExtractor.extract_range(text)
                or VerseExtractor.extract_range(combined_text)
                or VerseExtractor.extract_range(
                    text, context_book=ctx_book, context_chapter=ctx_chapter
                )
            )
            if detected:
                book, chapter, verse_start, verse_end = detected
                ref_key = (
                    f"{book} {chapter}:{verse_start}-{verse_end}"
                    if verse_end
                    else f"{book} {chapter}:{verse_start}"
                )
                if ref_key != last_emitted_ref:
                    verse_record = self.db.get_verse(
                        book, chapter, verse_start, verse_end=verse_end
                    )
                    if verse_record:
                        last_emitted_ref = ref_key
                        self.last_projected_verse = verse_record
                        safe_print(
                            f"[VERSE_DETECTED] {verse_record['reference']} ({verse_record['version']})"
                        )
                        await self.ws_manager.broadcast(
                            {
                                "event": "VERSE_DETECTED",
                                "payload": verse_record,
                            }
                        )

            if is_final:
                recent_final_text = text
                recent_final_ts = now_mono
                last_partial = ""
                last_emitted_ref = None

    async def handle_command(self, websocket: WebSocket, data: Dict[str, Any]) -> None:
        """Procesa comandos enviados desde Tauri (`rhema-ui`) hacia Python (`rhema-engine`)."""
        command = data.get("command")
        payload = data.get("payload") or {}

        if command == "CHANGE_AUDIO_DEVICE":
            device_id = payload.get("device_id")
            try:
                await asyncio.to_thread(self.audio.switch_device, device_id)
                self.stt.reset()
                safe_print(f"[RhemaEngine] Dispositivo de audio cambiado a ID={device_id}")
                await self.ws_manager.broadcast(
                    {
                        "event": "AUDIO_DEVICE_CHANGED",
                        "payload": {"device_id": device_id},
                    }
                )
            except Exception as exc:
                safe_print(f"[RhemaEngine] Error al cambiar dispositivo de audio: {exc}")

        elif command == "REQUEST_AUDIO_DEVICES":
            active_id = self.audio.current_device_id
            self.audio.stop()
            devices = await asyncio.to_thread(AudioStream.refresh_and_list_input_devices)
            try:
                self.audio.start(device_id=active_id)
            except Exception:
                with contextlib.suppress(Exception):
                    self.audio.start(device_id=None)
            await self.ws_manager.broadcast(
                {"event": "AUDIO_DEVICES_LIST", "payload": devices},
            )
            await self.ws_manager.broadcast(
                {
                    "event": "AUDIO_DEVICE_CHANGED",
                    "payload": {"device_id": self.audio.current_device_id},
                }
            )

        elif command == "ADJACENT_VERSE":
            if self.last_projected_verse:
                step = int(payload.get("step", 1))
                adj = self.db.get_adjacent_verse(
                    self.last_projected_verse["book"],
                    int(self.last_projected_verse["chapter"]),
                    int(self.last_projected_verse["verse"]),
                    step=step,
                )
                if adj:
                    self.last_projected_verse = adj
                    await self.ws_manager.broadcast(
                        {"event": "VERSE_PROJECTED", "payload": adj}
                    )

        elif command == "PROJECT_VERSE":
            verse_payload = payload.get("verse")
            if not verse_payload and all(k in payload for k in ("book", "chapter", "verse")):
                verse_payload = self.db.get_verse(
                    str(payload["book"]), int(payload["chapter"]), int(payload["verse"])
                )
            if verse_payload:
                self.last_projected_verse = verse_payload
                await self.ws_manager.broadcast(
                    {"event": "VERSE_PROJECTED", "payload": verse_payload}
                )

        elif command == "CLEAR_PROJECTION":
            self.last_projected_verse = None
            await self.ws_manager.broadcast(
                {"event": "PROJECTION_CLEARED", "payload": {}}
            )

        elif command == "SEARCH_VERSES":
            query = str(payload.get("query", "")).strip()
            results = self.db.search_manual(query)
            await self.ws_manager.send_personal(
                websocket,
                {"event": "SEARCH_RESULTS", "payload": results},
            )


runtime = RhemaEngineRuntime()


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    await runtime.start()
    try:
        yield
    finally:
        await runtime.stop()


app = FastAPI(
    title="Rhema Engine API",
    description="Motor 100% local de reconocimiento de voz bíblico y servidor WebSocket",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "rhema-engine",
        "websocket_url": f"ws://{WS_HOST}:{WS_PORT}/ws",
        "note": "Este puerto es el motor backend WebSocket. La interfaz visual nativa se ejecuta en Tauri v2 (rhema-ui).",
        "audio_devices": AudioStream.list_input_devices(),
        "current_device_id": runtime.audio.current_device_id,
        "last_projected_verse": runtime.last_projected_verse,
    }


@app.get("/search")
async def search_endpoint(q: str = Query("", description="Referencia o texto a buscar")) -> Dict[str, Any]:
    results = runtime.db.search_manual(q)
    return {"results": results}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await runtime.ws_manager.connect(websocket)
    try:
        devices = AudioStream.list_input_devices()
        await runtime.ws_manager.send_personal(
            websocket,
            {
                "event": "AUDIO_DEVICES_LIST",
                "payload": devices,
            },
        )
        await runtime.ws_manager.send_personal(
            websocket,
            {
                "event": "AUDIO_DEVICE_CHANGED",
                "payload": {"device_id": runtime.audio.current_device_id},
            },
        )
        if runtime.last_projected_verse:
            await runtime.ws_manager.send_personal(
                websocket,
                {
                    "event": "VERSE_PROJECTED",
                    "payload": runtime.last_projected_verse,
                },
            )

        while True:
            raw_message = await websocket.receive_text()
            try:
                data = json.loads(raw_message)
                if isinstance(data, dict):
                    await runtime.handle_command(websocket, data)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        runtime.ws_manager.disconnect(websocket)
    except Exception:
        runtime.ws_manager.disconnect(websocket)


if __name__ == "__main__":
    safe_print("=" * 68)
    safe_print(f"  RHEMA ENGINE - Servidor WebSocket activo en ws://{WS_HOST}:{WS_PORT}/ws")
    safe_print("=" * 68)
    # log_config=None evita errores de isatty() cuando corre sin consola (PyInstaller/Tauri)
    uvicorn.run(app, host=WS_HOST, port=WS_PORT, log_config=None)
