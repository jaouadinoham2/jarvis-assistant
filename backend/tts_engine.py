"""
JARVIS TTS Engine — Text-to-Speech (Fast Direct Playback)
Speaks directly through PC speakers for zero delay.
Fallback chain: Kokoro → pyttsx3 direct speak
"""

import io
import base64
import threading

# ─── Try Kokoro (primary) ───────────────────────────────────
kokoro_available = False
try:
    from kokoro import KPipeline
    import soundfile as sf
    import numpy as np
    kokoro_available = True
except ImportError:
    pass

# ─── Try pyttsx3 (fallback) ─────────────────────────────────
pyttsx3_available = False
try:
    import pyttsx3
    pyttsx3_available = True
except ImportError:
    pass


class TTSEngine:
    """Text-to-speech with direct speaker output for minimal delay."""

    SAMPLE_RATE = 24000

    def __init__(self, lang_code="a", voice="am_adam"):
        self.lang_code = lang_code
        self.voice = voice
        self.pipeline = None
        self.pyttsx_engine = None
        self.use_kokoro = False
        self.use_pyttsx3 = False
        self._pyttsx_lock = threading.Lock()
        self._stop_speaking = False

    def stop_speaking(self):
        """Stop current speech immediately."""
        self._stop_speaking = True
        try:
            import sounddevice as sd
            sd.stop()
        except:
            pass

    def load_model(self):
        """Try Kokoro first, fall back to pyttsx3."""
        if kokoro_available:
            try:
                print("[TTS] Loading Kokoro TTS...")
                self.pipeline = KPipeline(lang_code=self.lang_code)
                test_gen = self.pipeline("test", voice=self.voice, speed=1.0)
                for gs, ps, audio in test_gen:
                    pass
                self.use_kokoro = True
                print("[TTS] [OK] Kokoro TTS loaded!")
                return
            except Exception as e:
                print(f"[TTS] Kokoro failed: {e}")
                self.pipeline = None

        if pyttsx3_available:
            try:
                print("[TTS] Loading Windows TTS (pyttsx3)...")
                self.pyttsx_engine = pyttsx3.init()
                voices = self.pyttsx_engine.getProperty('voices')
                # Prefer David (male, heavy) over Zira (female)
                david_voice = None
                zira_voice = None
                for v in voices:
                    if "david" in v.name.lower():
                        david_voice = v.id
                        break
                    elif "zira" in v.name.lower():
                        zira_voice = v.id
                
                selected_voice = david_voice or zira_voice or (voices[0].id if voices else None)
                if selected_voice:
                    self.pyttsx_engine.setProperty('voice', selected_voice)
                
                self.pyttsx_engine.setProperty('rate', 150) # Slower rate makes it sound heavier
                self.pyttsx_engine.setProperty('volume', 0.9)
                self.use_pyttsx3 = True
                print("[TTS] [OK] Windows TTS loaded!")
                return
            except Exception as e:
                print(f"[TTS] pyttsx3 failed: {e}")

        print("[TTS] [!!] No TTS available. Text-only mode.")

    def speak_directly(self, text):
        """Speak text directly through PC speakers (fastest method)."""
        if self._stop_speaking:
            print("[TTS] Speak cancelled (stopped).")
            return

        if not text or not text.strip():
            return

        # Clean text for speech
        text = text.strip()

        # Preprocessing for natural speech
        import re
        # Replace JARVIS acronym forms so TTS reads it as a word, not letters
        text = re.sub(r'J\.?A\.?R\.?V\.?I\.?S\.?', 'Jarvis', text, flags=re.IGNORECASE)
        text = text.replace('J.A.R.V.I.S', 'Jarvis').replace('J.A.R.V.I.S.', 'Jarvis')
        # Remove any remaining markdown formatting
        text = text.replace('*', '').replace('#', '').replace('_', '')

        if self.use_kokoro:
            self._speak_kokoro(text)
        elif self.use_pyttsx3:
            self._speak_pyttsx3(text)
        else:
            print(f"[TTS] No engine available to speak: {text[:50]}...")

    def _speak_pyttsx3(self, text):
        """Speak using pyttsx3 directly through speakers."""
        try:
            with self._pyttsx_lock:
                if self._stop_speaking:
                    return
                self.pyttsx_engine.say(text)
                self.pyttsx_engine.runAndWait()
        except Exception as e:
            print(f"[TTS] pyttsx3 speak error: {e}")
            # Reinitialize engine if it crashed
            try:
                self.pyttsx_engine = pyttsx3.init()
                self.pyttsx_engine.setProperty('rate', 150)
                self.pyttsx_engine.setProperty('volume', 0.9)
                self.pyttsx_engine.say(text)
                self.pyttsx_engine.runAndWait()
            except:
                pass

    def _speak_kokoro(self, text):
        """Speak using Kokoro TTS with natural pitch variation and instant stop capability."""
        try:
            import sounddevice as sd
            import random
            import time
            base_rate = 0.84  # Deep voice pitch shift

            # Stream: play each chunk with slight speed variation for natural feel
            generator = self.pipeline(text, voice=self.voice, speed=1.0)
            while True:
                if self._stop_speaking:
                    print("[TTS] Speech stopped by user (before generator next).")
                    break
                
                try:
                    # Manually get the next chunk. This prevents the standard for-loop from
                    # blocking to fetch the next chunk when stop was already requested.
                    gs, ps, audio = next(generator)
                except StopIteration:
                    break

                if self._stop_speaking:
                    print("[TTS] Speech stopped by user (after generator next).")
                    break

                if audio is not None and len(audio) > 0:
                    # Vary playback rate slightly (±3%) for natural pitch fluctuation
                    variation = random.uniform(-0.03, 0.03)
                    playback_rate = int(self.SAMPLE_RATE * (base_rate + variation))
                    sd.play(audio, playback_rate)
                    
                    # Instead of blocking on sd.wait(), poll stream activity to stop instantly
                    while True:
                        if self._stop_speaking:
                            sd.stop()
                            print("[TTS] Sound stopped instantly.")
                            break
                        try:
                            stream = sd.get_stream()
                            if not stream.active:
                                break
                        except Exception:
                            # Fallback if get_stream fails
                            break
                        time.sleep(0.02)
        except Exception as e:
            print(f"[TTS] Kokoro speak error: {e}, trying pyttsx3...")
            if pyttsx3_available:
                try:
                    if not self.pyttsx_engine:
                        self.pyttsx_engine = pyttsx3.init()
                        self.pyttsx_engine.setProperty('rate', 150)
                    self.use_pyttsx3 = True
                    self._speak_pyttsx3(text)
                except:
                    pass

    def synthesize_to_base64(self, text):
        """Fallback: Convert text to base64 WAV for WebSocket transmission."""
        if not text or not text.strip():
            return ""

        if self.use_kokoro:
            try:
                audio_segments = []
                generator = self.pipeline(text, voice=self.voice, speed=1.0)
                for gs, ps, audio in generator:
                    if audio is not None:
                        audio_segments.append(audio)
                if audio_segments:
                    full_audio = np.concatenate(audio_segments)
                    wav_buffer = io.BytesIO()
                    sf.write(wav_buffer, full_audio, self.SAMPLE_RATE, format="WAV", subtype="PCM_16")
                    return base64.b64encode(wav_buffer.getvalue()).decode("utf-8")
            except Exception as e:
                print(f"[TTS] Kokoro base64 error: {e}")

        return ""

    def is_loaded(self):
        return self.use_kokoro or self.use_pyttsx3
