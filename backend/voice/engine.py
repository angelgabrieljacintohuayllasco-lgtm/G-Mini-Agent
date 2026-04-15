"""
G-Mini Agent — Voice Engine.
TTS (Text-to-Speech), STT (Speech-to-Text) y Real-Time Voice.
"""

from __future__ import annotations

import asyncio
import base64
import io
import time
from typing import Any, AsyncGenerator

from loguru import logger

from backend.config import config

# ── TTS Engines ───────────────────────────────────────────

HAS_MELOTTS = False
HAS_ELEVENLABS = False

try:
    from melo.api import TTS as MeloTTSModel
    HAS_MELOTTS = True
except ImportError:
    pass

try:
    from elevenlabs import AsyncElevenLabs
    HAS_ELEVENLABS = True
except ImportError:
    pass

# ── STT Engine ────────────────────────────────────────────

HAS_WHISPER = False
_WhisperModel = None

def _lazy_load_whisper():
    """Importa faster_whisper de forma lazy para evitar bloqueo de av/ffmpeg al inicio."""
    global HAS_WHISPER, _WhisperModel
    if _WhisperModel is not None:
        return
    try:
        from faster_whisper import WhisperModel
        _WhisperModel = WhisperModel
        HAS_WHISPER = True
    except ImportError:
        HAS_WHISPER = False


class VoiceEngine:
    """
    Motor de voz del agente.
    - TTS: MeloTTS (offline) o ElevenLabs (online, cloning)
    - STT: Faster-Whisper (offline, large-v3)
    - Real-Time Voice: WebSocket APIs (OpenAI, Gemini, Grok)
    """

    _TTS_CACHE_MAX = 128  # Max cached phrases

    def __init__(self):
        self._tts_engine: str = "none"
        self._stt_model: Any = None
        self._melo_model: Any = None
        self._melo_speaker_ids: dict = {}
        self._melo_language: str = "ES"
        self._eleven_client: Any = None
        self._initialized = False
        self._tts_cache: dict[str, bytes] = {}  # key=text_hash → audio bytes

    async def initialize(self) -> None:
        """Inicializa los motores de voz configurados."""
        tts_pref = config.get("voice", "tts_engine", default="melotts")
        stt_enabled = config.get("voice", "stt_enabled", default=True)

        # TTS
        await self._init_tts(tts_pref)

        # STT
        if stt_enabled:
            await self._init_stt()

        self._initialized = True
        logger.info(f"VoiceEngine inicializado (TTS: {self._tts_engine})")

    async def _init_tts(self, preference: str) -> None:
        """Inicializa el motor TTS."""
        if preference == "none":
            logger.info("TTS: Desactivado explícitamente")
            return
            
        if preference == "melotts" and HAS_MELOTTS:
            try:
                lang = config.get("voice", "melotts_language", default="ES")
                device = config.get("voice", "melotts_device", default="auto")
                loop = asyncio.get_running_loop()
                self._melo_model = await loop.run_in_executor(
                    None,
                    lambda: MeloTTSModel(language=lang, device=device),
                )
                self._melo_speaker_ids = dict(self._melo_model.hps.data.spk2id.items())
                self._melo_language = lang
                self._tts_engine = "melotts"
                logger.info(f"TTS: MeloTTS inicializado (lang={lang}, speakers={list(self._melo_speaker_ids.keys())})")
                return
            except Exception as e:
                logger.warning(f"MeloTTS no disponible: {e}")

        if (preference == "elevenlabs" or self._tts_engine == "none") and HAS_ELEVENLABS:
            try:
                api_key = config.get_api_key("elevenlabs_api")
                if api_key:
                    self._eleven_client = AsyncElevenLabs(api_key=api_key)
                    self._tts_engine = "elevenlabs"
                    logger.info("TTS: ElevenLabs inicializado")
                    return
            except Exception as e:
                logger.warning(f"ElevenLabs no disponible: {e}")

        google_tts_models = ["gemini-2.5-pro-tts", "gemini-2.5-flash-tts", "gemini-2.5-flash-lite-preview-tts", "chirp_3", "chirp_2"]
        if (preference in google_tts_models or self._tts_engine == "none"):
            try:
                api_key = config.get_api_key("google_api")
                if api_key:
                    from google import genai
                    self._google_client = genai.Client(api_key=api_key)
                    self._tts_engine = preference if preference in google_tts_models else "gemini-2.5-flash-tts"
                    logger.info(f"TTS: Google TTS inicializado ({self._tts_engine})")
                    return
            except Exception as e:
                logger.warning(f"Google TTS no disponible: {e}")

        logger.info("TTS: No hay motor disponible")

    async def _init_stt(self) -> None:
        """Inicializa Faster-Whisper para STT."""
        _lazy_load_whisper()
        if not HAS_WHISPER:
            logger.info("STT: faster-whisper no disponible")
            return

        try:
            model_size = config.get("voice", "whisper_model", default="base")
            device = config.get("voice", "whisper_device", default="cpu")
            compute_type = config.get("voice", "whisper_compute", default="int8")

            loop = asyncio.get_running_loop()
            self._stt_model = await loop.run_in_executor(
                None,
                lambda: _WhisperModel(model_size, device=device, compute_type=compute_type),
            )
            logger.info(f"STT: Whisper ({model_size}) inicializado en {device}")
        except Exception as e:
            logger.warning(f"STT Whisper no disponible: {e}")

    # ── TTS ───────────────────────────────────────────────

    async def synthesize(
        self,
        text: str,
        voice_id: str | None = None,
        speed: float = 1.0,
    ) -> bytes | None:
        """
        Sintetiza texto a audio WAV. Usa cache en memoria para frases repetidas.
        Retorna bytes del audio o None.
        """
        import hashlib
        cache_key = hashlib.md5(f"{text}|{self._tts_engine}|{voice_id}|{speed}".encode()).hexdigest()

        # Check cache
        if cache_key in self._tts_cache:
            logger.debug(f"TTS cache hit: {text[:40]}...")
            return self._tts_cache[cache_key]

        # Generate
        result: bytes | None = None
        if self._tts_engine == "melotts":
            result = await self._tts_melo(text, speed)
        elif self._tts_engine == "elevenlabs":
            result = await self._tts_elevenlabs(text, voice_id)
        elif self._tts_engine in ["gemini-2.5-pro-tts", "gemini-2.5-flash-tts", "gemini-2.5-flash-lite-preview-tts", "chirp_3", "chirp_2"]:
            result = await self._tts_google(text, voice_id)
        else:
            logger.warning("No hay motor TTS disponible")
            return None

        # Store in cache (LRU-like: evict oldest if full)
        if result and len(result) < 5_000_000:  # Don't cache >5MB
            if len(self._tts_cache) >= self._TTS_CACHE_MAX:
                oldest_key = next(iter(self._tts_cache))
                del self._tts_cache[oldest_key]
            self._tts_cache[cache_key] = result

        return result

    async def _tts_melo(self, text: str, speed: float = 1.0) -> bytes | None:
        """TTS con MeloTTS (offline)."""
        try:
            loop = asyncio.get_running_loop()

            def _generate():
                import tempfile
                import os
                # Seleccionar speaker_id según idioma configurado
                speaker_id = self._melo_speaker_ids.get(
                    self._melo_language,
                    next(iter(self._melo_speaker_ids.values()))
                )
                # MeloTTS genera archivo WAV
                tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                tmp_path = tmp.name
                tmp.close()
                try:
                    self._melo_model.tts_to_file(text, speaker_id, tmp_path, speed=speed)
                    with open(tmp_path, "rb") as f:
                        return f.read()
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

            return await loop.run_in_executor(None, _generate)
        except Exception as e:
            logger.error(f"MeloTTS error: {e}")
            return None

    async def _tts_elevenlabs(self, text: str, voice_id: str | None = None) -> bytes | None:
        """TTS con ElevenLabs (online)."""
        try:
            if voice_id is None:
                voice_id = config.get("voice", "elevenlabs_voice_id", default="21m00Tcm4TlvDq8ikWAM")

            audio = await self._eleven_client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id="eleven_multilingual_v2",
            )

            # Recoger chunks
            chunks = []
            async for chunk in audio:
                chunks.append(chunk)
            return b"".join(chunks)

        except Exception as e:
            logger.error(f"ElevenLabs error: {e}")
            return None

    async def _tts_google(self, text: str, voice_id: str | None = None) -> bytes | None:
        """TTS con Google Gemini (online)."""
        try:
            from google.genai import types
            
            # Asignar voz por defecto si no se da una
            v_id = voice_id or "Kore"

            response = await asyncio.to_thread(
                self._google_client.models.generate_content,
                model=self._tts_engine,
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=v_id,
                            )
                        )
                    )
                )
            )

            # Extraer bytes
            data = response.candidates[0].content.parts[0].inline_data.data
            return data

        except Exception as e:
            logger.error(f"Google TTS error: {e}")
            return None

    async def synthesize_stream(
        self,
        text: str,
    ) -> AsyncGenerator[bytes, None]:
        """TTS streaming — genera chunks de audio progresivamente."""
        if self._tts_engine == "elevenlabs" and self._eleven_client:
            try:
                voice_id = config.get("voice", "elevenlabs_voice_id", default="21m00Tcm4TlvDq8ikWAM")
                audio = await self._eleven_client.text_to_speech.convert(
                    voice_id=voice_id,
                    text=text,
                    model_id="eleven_multilingual_v2",
                )
                async for chunk in audio:
                    yield chunk
            except Exception as e:
                logger.error(f"ElevenLabs streaming error: {e}")
        else:
            # Para MeloTTS y Google TTS, generar todo de una vez
            audio = await self.synthesize(text)
            if audio:
                yield audio

    # ── STT ───────────────────────────────────────────────

    async def transcribe(self, audio_bytes: bytes) -> str:
        """
        Transcribe audio a texto.
        Acepta audio WAV/MP3/OGG bytes.
        """
        if not self._stt_model:
            logger.warning("STT no disponible")
            return ""

        try:
            loop = asyncio.get_running_loop()

            def _transcribe():
                buf = io.BytesIO(audio_bytes)
                segments, info = self._stt_model.transcribe(
                    buf,
                    language="es",
                    beam_size=5,
                    vad_filter=True,
                )
                return " ".join([s.text.strip() for s in segments])

            text = await loop.run_in_executor(None, _transcribe)
            logger.debug(f"STT resultado: {text[:80]}...")
            return text

        except Exception as e:
            logger.error(f"STT error: {e}")
            return ""

    # ── Lipsync Data ──────────────────────────────────────

    def generate_lipsync_data(self, audio_bytes: bytes) -> list[dict]:
        """
        Genera datos de lipsync para animación del personaje.
        Usa análisis RMS del audio para detectar energía vocal real.
        Mapea amplitud a visemas basándose en intensidad.
        """
        import struct
        import math

        sample_rate = 22050
        bytes_per_sample = 2  # 16-bit PCM
        frame_duration = 0.06  # 60ms per frame (~16 FPS)
        samples_per_frame = int(sample_rate * frame_duration)
        bytes_per_frame = samples_per_frame * bytes_per_sample

        # Strip WAV header if present (44 bytes)
        raw = audio_bytes
        if len(raw) > 44 and raw[:4] == b'RIFF':
            raw = raw[44:]

        total_frames = max(1, len(raw) // bytes_per_frame)
        visemes: list[dict] = []

        # Viseme mapping by energy level (low→high)
        energy_visemes = ["rest", "A", "E", "O", "I", "U"]
        # Track max RMS for normalization
        rms_values: list[float] = []

        for frame_idx in range(total_frames):
            offset = frame_idx * bytes_per_frame
            chunk = raw[offset:offset + bytes_per_frame]
            if len(chunk) < bytes_per_sample:
                break

            # Calculate RMS energy for this frame
            num_samples = len(chunk) // bytes_per_sample
            samples = struct.unpack(f"<{num_samples}h", chunk[:num_samples * bytes_per_sample])
            sum_sq = sum(s * s for s in samples)
            rms = math.sqrt(sum_sq / num_samples) if num_samples > 0 else 0.0
            rms_values.append(rms)

        if not rms_values:
            return [{"time": 0.0, "viseme": "rest", "weight": 0.0}]

        # Normalize RMS values against peak
        max_rms = max(rms_values) if max(rms_values) > 0 else 1.0
        silence_threshold = 0.05  # Below 5% of peak = silence

        for frame_idx, rms in enumerate(rms_values):
            t = round(frame_idx * frame_duration, 3)
            normalized = rms / max_rms

            if normalized < silence_threshold:
                viseme = "rest"
                weight = 0.0
            else:
                # Map normalized energy (0-1) to viseme index
                idx = min(int(normalized * (len(energy_visemes) - 1)), len(energy_visemes) - 1)
                viseme = energy_visemes[idx]
                weight = round(min(normalized * 1.2, 1.0), 2)

            visemes.append({
                "time": t,
                "viseme": viseme,
                "weight": weight,
            })

        return visemes

    # ── Properties ────────────────────────────────────────

    @property
    def tts_available(self) -> bool:
        return self._tts_engine != "none"

    @property
    def stt_available(self) -> bool:
        return self._stt_model is not None

    @property
    def tts_engine_name(self) -> str:
        return self._tts_engine
