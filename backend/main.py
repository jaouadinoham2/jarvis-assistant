"""
JARVIS — Local AI Voice Assistant
FastAPI server with WebSocket support for real-time voice and text interaction.
"""

import asyncio
import json
import base64
import os
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from llm_engine import LLMEngine
from stt_engine import STTEngine
from tts_engine import TTSEngine
from command_engine import detect_command

# ─── Engine Instances ─────────────────────────────────────────
llm = LLMEngine(model="phi4-mini")
# Use CPU for STT because cublas64_12.dll is missing on this system
stt = STTEngine(model_size="base", device="cpu", compute_type="int8")
tts = TTSEngine(lang_code="a", voice="am_adam")


async def load_models_background():
    """Load models in background after server binds, so startup is instant."""
    # Check Ollama connection and preload model into GPU memory
    print("\n[STARTUP] Checking Ollama connection in background...")
    try:
        connected = await llm.check_connection()
        if connected:
            print("[STARTUP] [OK] Ollama is running! Preloading model into VRAM...")
            await llm.preload_model()
        else:
            print("[STARTUP] [!!] Ollama not available.")
    except Exception as e:
        print(f"[STARTUP] [!!] Ollama check failed: {e}")

    # Pre-load STT model
    print("\n[STARTUP] Loading Speech-to-Text model in background...")
    try:
        await asyncio.to_thread(stt.load_model)
    except Exception as e:
        print(f"[STARTUP] [!!] STT failed to load: {e}")

    # Pre-load TTS model
    print("\n[STARTUP] Loading Text-to-Speech model in background...")
    try:
        await asyncio.to_thread(tts.load_model)
    except Exception as e:
        print(f"[STARTUP] [!!] TTS failed to load: {e}")

    print("\n[STARTUP] All models initialized. JARVIS is fully ready!")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    print("=" * 60)
    print("  JARVIS -- Local AI Voice Assistant")
    print("=" * 60)

    # Start background model loading so Uvicorn starts instantly
    asyncio.create_task(load_models_background())

    print("\n" + "=" * 60)
    print("  Open http://localhost:8000 in your browser")
    print("=" * 60 + "\n")

    yield

    # Shutdown
    await llm.close()
    print("\n[SHUTDOWN] JARVIS signing off. Goodbye, sir.")


# ─── FastAPI App ──────────────────────────────────────────────
app = FastAPI(title="JARVIS", lifespan=lifespan)

# Serve frontend static files
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
async def serve_index():
    """Serve the JARVIS web UI."""
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    ollama_ok = await llm.check_connection()
    return {
        "status": "online",
        "ollama": "connected" if ollama_ok else "disconnected",
        "stt": "loaded" if stt.is_loaded() else "not loaded",
        "tts": "loaded" if tts.is_loaded() else "not loaded",
    }


async def process_and_respond(ws, user_text, source="text"):
    """
    Process user input: check for commands first, then fall back to LLM.
    Handles the full flow: command/LLM -> text response -> TTS audio.
    """
    # Reset stop speaking flag for the new command
    tts._stop_speaking = False

    # ─── Step 1: Check if it's a system command ──────────────
    command_result = detect_command(user_text)

    if command_result:
        cmd_type, response_text = command_result
        print(f"[CMD] ({cmd_type}) {response_text}")

        # Also tell the LLM what happened so it has context
        llm.conversation_history.append({"role": "user", "content": user_text})
        llm.conversation_history.append({"role": "assistant", "content": response_text})
    else:
        # ─── Step 2: Send to LLM for a response ─────────────
        # Send "thinking" status
        await ws.send_text(json.dumps({
            "type": "status", "content": "thinking"
        }))

        response_text = await llm.chat(user_text)

    print(f"[JARVIS] {response_text}")

    # ─── Step 3+4: Send text to UI AND start TTS simultaneously ─
    # This eliminates the delay between chat text appearing and voice starting
    await ws.send_text(json.dumps({
        "type": "status", "content": "speaking"
    }))

    async def send_text_to_ui():
        await ws.send_text(json.dumps({
            "type": "response", "content": response_text
        }))

    async def speak_audio():
        try:
            await asyncio.to_thread(tts.speak_directly, response_text)
        except Exception as e:
            print(f"[TTS] Error: {e}")

    # Run both at the same time — text appears while TTS generates
    await asyncio.gather(send_text_to_ui(), speak_audio())

    # ─── Step 5: Back to idle ────────────────────────────────
    await ws.send_text(json.dumps({
        "type": "status", "content": "idle"
    }))


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """Main WebSocket endpoint for JARVIS communication."""
    await ws.accept()
    print("[WS] Client connected.")

    # ─── Welcome greeting on connect ─────────────────────────
    # If models are still loading, notify frontend and wait
    if not (stt.is_loaded() and tts.is_loaded()):
        await ws.send_text(json.dumps({
            "type": "status", "content": "thinking"
        }))
        await ws.send_text(json.dumps({
            "type": "response", "content": "Initializing neural networks. Please stand by, sir..."
        }))
        while not (stt.is_loaded() and tts.is_loaded()):
            await asyncio.sleep(0.5)

    hour = datetime.now().hour
    if 5 <= hour < 12:
        time_greeting = "Good morning"
    elif 12 <= hour < 17:
        time_greeting = "Good afternoon"
    elif 17 <= hour < 21:
        time_greeting = "Good evening"
    else:
        time_greeting = "Good night"

    welcome_text = (
        f"{time_greeting}, Commander. "
        "All servers checked and found online. "
        "All configurations working fine. "
        "Boot menu checked, all good. "
        "GPU working absolutely fine, no problems detected. "
        "Suit is ready to use. "
        "Arc reactor is safe and in perfect condition. "
        "Ready to receive commands."
    )
    print(f"[JARVIS] Greeting: {welcome_text}")

    await ws.send_text(json.dumps({
        "type": "response", "content": welcome_text
    }))
    await ws.send_text(json.dumps({
        "type": "status", "content": "speaking"
    }))
    try:
        await asyncio.to_thread(tts.speak_directly, welcome_text)
        print("[TTS] Welcome greeting spoken successfully!")
    except Exception as e:
        print(f"[TTS] Welcome greeting error: {e}")
    await ws.send_text(json.dumps({
        "type": "status", "content": "idle"
    }))

    # Background task reference so we can track/cancel it
    current_task = None

    try:
        while True:
            raw_message = await ws.receive_text()
            message = json.loads(raw_message)
            msg_type = message.get("type", "")

            if msg_type == "text":
                user_text = message.get("content", "").strip()
                if not user_text:
                    continue

                print(f"[USER] (text) {user_text}")
                # Run as background task so the loop keeps listening for "stop"
                current_task = asyncio.create_task(
                    process_and_respond(ws, user_text, source="text")
                )

            elif msg_type == "audio":
                audio_b64 = message.get("content", "")
                if not audio_b64:
                    continue

                try:
                    # Send "listening" status
                    await ws.send_text(json.dumps({
                        "type": "status", "content": "listening"
                    }))

                    # Decode and transcribe audio
                    audio_bytes = base64.b64decode(audio_b64)
                    transcribed = await asyncio.to_thread(stt.transcribe_audio, audio_bytes)

                    if not transcribed:
                        await ws.send_text(json.dumps({
                            "type": "error", "content": "I couldn't hear you clearly. Please try again."
                        }))
                        await ws.send_text(json.dumps({
                            "type": "status", "content": "idle"
                        }))
                        continue

                    # Send transcription to client
                    await ws.send_text(json.dumps({
                        "type": "transcription", "content": transcribed
                    }))

                    print(f"[USER] (voice) {transcribed}")
                    # Run as background task so the loop keeps listening for "stop"
                    current_task = asyncio.create_task(
                        process_and_respond(ws, transcribed, source="voice")
                    )

                except Exception as e:
                    print(f"[AUDIO] Error processing audio: {e}")
                    await ws.send_text(json.dumps({
                        "type": "error", "content": "Audio processing failed. Please try again."
                    }))
                    await ws.send_text(json.dumps({
                        "type": "status", "content": "idle"
                    }))

            elif msg_type == "stop":
                # Stop TTS immediately
                tts.stop_speaking()
                print("[WS] Stop requested by user.")
                # Cancel the background task if it's still running
                if current_task and not current_task.done():
                    current_task.cancel()
                    current_task = None
                await ws.send_text(json.dumps({
                    "type": "status", "content": "idle"
                }))

            elif msg_type == "clear_history":
                llm.clear_history()
                await ws.send_text(json.dumps({
                    "type": "response",
                    "content": "Memory cleared. Starting fresh, sir."
                }))
                await ws.send_text(json.dumps({
                    "type": "status", "content": "idle"
                }))

            else:
                await ws.send_text(json.dumps({
                    "type": "error",
                    "content": f"Unknown message type: {msg_type}"
                }))

    except WebSocketDisconnect:
        print("[WS] Client disconnected.")
    except Exception as e:
        print(f"[WS] Error: {e}")
        try:
            await ws.send_text(json.dumps({
                "type": "error", "content": str(e)
            }))
        except:
            pass


# ─── Run Server ───────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
