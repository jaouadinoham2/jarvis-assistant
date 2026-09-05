"""
JARVIS STT Engine — faster-whisper Speech-to-Text
Handles audio transcription using GPU-accelerated Whisper.
"""

import io
import tempfile
import os
import numpy as np

# Try to import faster_whisper, provide helpful error if missing
try:
    from faster_whisper import WhisperModel
except ImportError:
    print("[STT] faster-whisper not installed. Run: pip install faster-whisper")
    WhisperModel = None


class STTEngine:
    """Manages speech-to-text transcription using faster-whisper."""

    def __init__(self, model_size: str = "small", device: str = "cuda", compute_type: str = "float16"):
        """
        Initialize the STT engine.
        
        Args:
            model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large-v3')
                       'small' is recommended for RTX 3050 — good accuracy, low VRAM (~1GB)
            device: 'cuda' for GPU, 'cpu' for CPU
            compute_type: 'float16' for GPU, 'int8' for CPU
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model = None

    def load_model(self):
        """Load the Whisper model. Called once at startup."""
        if WhisperModel is None:
            raise RuntimeError("faster-whisper is not installed!")

        print(f"[STT] Loading Whisper '{self.model_size}' model on {self.device}...")
        try:
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
            print(f"[STT] Model loaded successfully on {self.device.upper()}!")
        except Exception as e:
            print(f"[STT] Failed to load on {self.device}: {e}")
            if self.device == "cuda":
                print("[STT] Falling back to CPU...")
                self.device = "cpu"
                self.compute_type = "int8"
                self.model = WhisperModel(
                    self.model_size,
                    device="cpu",
                    compute_type="int8"
                )
                print("[STT] Model loaded on CPU (slower but works).")

    def transcribe_audio(self, audio_bytes: bytes) -> str:
        """
        Transcribe audio bytes to text.
        
        Args:
            audio_bytes: Raw audio data in WAV format
            
        Returns:
            Transcribed text string
        """
        if self.model is None:
            self.load_model()

        # Write audio bytes to a temporary file (faster-whisper needs a file path)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_path = temp_file.name

            # Transcribe with VAD filter to skip silence
            segments, info = self.model.transcribe(
                temp_path,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=200
                )
            )

            # Collect all segment texts
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())

            transcribed_text = " ".join(text_parts).strip()

            if transcribed_text:
                print(f"[STT] Transcribed: \"{transcribed_text}\"")
            else:
                print("[STT] No speech detected in audio.")

            return transcribed_text

        except Exception as e:
            print(f"[STT] Transcription error: {e}")
            return ""
        finally:
            # Clean up temp file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass

    def is_loaded(self) -> bool:
        """Check if the model is loaded."""
        return self.model is not None
