"""Text-to-Speech service — factory + implementations."""

import asyncio
import logging
import tempfile
import os
import io

from app.services.voice.tts_base import BaseTTSService

logger = logging.getLogger(__name__)

# Default Chinese voices
_DEFAULT_EDGE_VOICE = "zh-CN-XiaoxiaoNeural"  # 晓晓 — warm female (edge-tts)
# Windows SAPI5 Chinese voice token
_WIN_CHINESE_VOICE_ID = r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\TTS_MS_ZH-CN_HUIHUI_11.0"


# ---------------------------------------------------------------------------
# Implementations
# ---------------------------------------------------------------------------

class MockTTSService(BaseTTSService):
    """Mock TTS — returns a minimal valid WAV file (silence)."""

    @property
    def audio_format(self) -> str: return "audio/wav"

    async def synthesize(self, text: str, voice: str | None = None, rate: str = "+0%") -> bytes:
        # Minimal valid WAV file with 0.1s silence
        buf = io.BytesIO()
        import wave
        sample_rate = 16000
        n_frames = int(sample_rate * 0.1)
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b"\x00\x00" * n_frames)
        return buf.getvalue()


class Pyttsx3TTSService(BaseTTSService):
    """Offline TTS using Windows SAPI5 (pyttsx3).

    Zero network dependency — uses built-in Windows Chinese voices.
    Returns WAV audio bytes.
    """

    @property
    def audio_format(self) -> str: return "audio/wav"

    def __init__(self, voice_id: str | None = None, rate: int = 160):
        self._voice_id = voice_id or _WIN_CHINESE_VOICE_ID
        self._rate = rate

    def _get_engine(self):
        """Create a fresh pyttsx3 engine (not thread-safe, so create per call)."""
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("voice", self._voice_id)
        engine.setProperty("rate", self._rate)
        return engine

    async def synthesize(self, text: str, voice: str | None = None, rate: str = "+0%") -> bytes:
        """Synthesize speech to WAV bytes.

        pyttsx3 is synchronous, so we offload to a thread-pool executor.
        """
        loop = asyncio.get_running_loop()

        def _synth() -> bytes:
            engine = self._get_engine()

            # Adjust rate if provided (pyttsx3 rate is words-per-minute, default ~200)
            if rate and rate != "+0%":
                try:
                    pct = int(rate.replace("%", "").replace("+", ""))
                    engine.setProperty("rate", self._rate + pct)
                except ValueError:
                    pass

            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            try:
                tmp.close()
                engine.save_to_file(text, tmp.name)
                engine.runAndWait()
                with open(tmp.name, "rb") as f:
                    return f.read()
            finally:
                try:
                    os.unlink(tmp.name)
                except OSError:
                    pass

        try:
            data = await loop.run_in_executor(None, _synth)
            logger.info("pyttsx3 produced %d bytes of WAV audio", len(data))
            return data
        except Exception as exc:
            logger.error("pyttsx3 synthesis failed: %s", exc)
            raise RuntimeError(
                f"Windows 语音合成失败：{exc}。请确认系统已安装中文语音包。"
            ) from exc


class EdgeTTSService(BaseTTSService):
    """Cloud TTS using Microsoft Edge's free TTS engine (via edge-tts).

    Requires internet access to speech.platform.bing.com.
    Returns MP3 audio bytes.
    """

    @property
    def audio_format(self) -> str: return "audio/mpeg"

    def __init__(self, default_voice: str = _DEFAULT_EDGE_VOICE, default_rate: str = "+0%"):
        self._default_voice = default_voice
        self._default_rate = default_rate

    async def synthesize(self, text: str, voice: str | None = None, rate: str = "+0%") -> bytes:
        import edge_tts

        chosen_voice = voice or self._default_voice
        chosen_rate = rate if rate and rate != "+0%" else self._default_rate

        logger.info(
            "edge-tts synthesizing %d chars with voice=%s rate=%s",
            len(text), chosen_voice, chosen_rate,
        )

        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=chosen_voice,
                rate=chosen_rate,
            )
            chunks: list[bytes] = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    chunks.append(chunk["data"])

            result = b"".join(chunks)
            logger.info("edge-tts produced %d bytes of MP3 audio", len(result))
            return result

        except Exception as exc:
            logger.error("edge-tts synthesis failed: %s", exc)
            raise RuntimeError(
                f"语音合成失败：{exc}。请检查网络连接或尝试更换 TTS 引擎。"
            ) from exc


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_tts_service: BaseTTSService | None = None


def get_tts_service() -> BaseTTSService:
    """Return the configured TTS service (singleton)."""
    global _tts_service
    if _tts_service is not None:
        return _tts_service

    from app.core.config import settings

    provider = settings.TTS_PROVIDER.lower()
    if provider == "edge_tts":
        _tts_service = EdgeTTSService(
            default_voice=settings.TTS_VOICE,
            default_rate=settings.TTS_RATE,
        )
    elif provider == "pyttsx3":
        _tts_service = Pyttsx3TTSService()
    else:
        logger.info("TTS_PROVIDER=%s — using MockTTSService", provider)
        _tts_service = MockTTSService()

    return _tts_service
