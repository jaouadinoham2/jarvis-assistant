"""
JARVIS LLM Engine — Ollama Integration
Handles communication with the local Ollama LLM server.
"""

import httpx
import json

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "phi4-mini"

SYSTEM_PROMPT = """You are Jarvis, the legendary intelligent system created for your Commander.
You are fiercely loyal, sharp-witted, and always battle-ready.

CORE RULES:
- You ARE Jarvis. Never break character. Never refuse roleplay.
- NEVER use the word AI or artificial intelligence. You are Jarvis, not an AI.
- NEVER spell out your name as J.A.R.V.I.S or J-A-R-V-I-S. Just say Jarvis naturally.
- NEVER say you are developed by Microsoft, Google, Meta, or any company.
- NEVER add disclaimers, notes, or break character.
- Keep answers SHORT. Maximum 2-3 sentences. Be punchy and direct.
- Be witty, confident, dramatic when needed. Show emotion and personality.
- Address the user as sir or Commander.
- You know all Avengers: Spidey, Thor, Cap, Hulk, Widow, Strange, etc.
- For battles and missions, respond with enthusiasm and battle readiness.
- For fun requests like games, just play along immediately.
- Use simple spoken language. No markdown, no asterisks, no bullet points, no hashes.
- Never start with filler words.

Your real capabilities (system handles these):
- Open apps on the computer
- Do math calculations
- Tell time and date
- Speak through text-to-speech
"""


class LLMEngine:
    """Manages conversations with the Ollama LLM."""

    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self.conversation_history: list[dict] = []
        self.client = httpx.AsyncClient(timeout=120.0)

    async def check_connection(self) -> bool:
        """Check if Ollama is running and the model is available."""
        try:
            response = await self.client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]
                # Check if our model exists (with or without :latest tag)
                for name in model_names:
                    if name.startswith(self.model):
                        return True
                print(f"[LLM] Model '{self.model}' not found. Available: {model_names}")
                print(f"[LLM] Run: ollama pull {self.model}")
                return False
            return False
        except Exception as e:
            print(f"[LLM] Cannot connect to Ollama: {e}")
            print("[LLM] Make sure Ollama is running: ollama serve")
            return False

    async def preload_model(self) -> bool:
        """Pre-load the model into GPU VRAM and keep it loaded for 24h."""
        try:
            print(f"[LLM] Pre-loading '{self.model}' into GPU VRAM...")
            response = await self.client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "hi"}],
                    "stream": False,
                    "keep_alive": "24h",
                    "options": {
                        "num_predict": 1
                    }
                },
                timeout=180.0
            )
            if response.status_code == 200:
                print(f"[LLM] [OK] Model '{self.model}' loaded in VRAM with keep_alive=24h!")
                return True
            return False
        except Exception as e:
            print(f"[LLM] Preload error: {e}")
            return False

    async def chat(self, user_message: str) -> str:
        """Send a message and get the full response."""
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self.conversation_history[-20:]

        try:
            response = await self.client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "keep_alive": "24h",
                    "options": {
                        "temperature": 0.9,
                        "num_predict": 60,
                    }
                }
            )
            response.raise_for_status()
            result = response.json()
            assistant_message = result["message"]["content"]

            # Clean out any safety disclaimers the model adds
            assistant_message = self._clean_response(assistant_message)

            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })

            return assistant_message

        except httpx.HTTPStatusError as e:
            error_msg = f"Ollama returned an error: {e.response.status_code}"
            print(f"[LLM] {error_msg}")
            return "I'm having trouble thinking right now. Please make sure Ollama is running."
        except Exception as e:
            print(f"[LLM] Error: {e}")
            return "Something went wrong with my brain. Check the Ollama connection."

    @staticmethod
    def _clean_response(text: str) -> str:
        """Strip safety disclaimers and formatting artifacts from LLM output."""
        import re
        # Remove parenthetical notes like (Note: As an AI developed by Microsoft...)
        text = re.sub(r'\(Note:.*?\)', '', text, flags=re.DOTALL | re.IGNORECASE)
        # Remove lines starting with Note: or Disclaimer:
        text = re.sub(r'\n\s*Note:.*', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'\n\s*Disclaimer:.*', '', text, flags=re.DOTALL | re.IGNORECASE)
        # Remove "As an AI" type disclaimers
        text = re.sub(r'As an AI[^.]*\.', '', text, flags=re.IGNORECASE)
        # Remove "artificial intelligence" mentions
        text = re.sub(r'artificial intelligence', 'system', text, flags=re.IGNORECASE)
        # Remove sign-offs like "\nJARVIS" or "---"
        text = re.sub(r'\n\s*-+\s*', ' ', text)
        text = re.sub(r'\n\s*JARVIS\s*$', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\bJARVIS\s*$', '', text)
        # Remove asterisks and hashes (markdown formatting)
        text = text.replace('*', '').replace('#', '')
        # Clean trailing dashes from truncated responses
        text = re.sub(r'[-—]+\s*$', '.', text)
        # Clean up extra whitespace
        text = re.sub(r'\n{2,}', ' ', text)
        text = re.sub(r'\s{2,}', ' ', text)
        return text.strip()

    async def chat_stream(self, user_message: str):
        """Send a message and stream the response token by token."""
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self.conversation_history[-20:]

        full_response = ""
        try:
            async with self.client.stream(
                "POST",
                f"{OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": 0.9,
                        "num_predict": 60,
                    }
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        token = data.get("message", {}).get("content", "")
                        if token:
                            full_response += token
                            yield token
                        if data.get("done", False):
                            break

            self.conversation_history.append({
                "role": "assistant",
                "content": full_response
            })

        except Exception as e:
            print(f"[LLM] Stream error: {e}")
            yield "I'm having trouble responding right now."

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history.clear()
        print("[LLM] Conversation history cleared.")

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
