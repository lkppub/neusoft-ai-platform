"""Speech-to-Text service — factory + implementations."""

import asyncio
import logging
import os
import shutil
import tempfile
from pathlib import Path

from app.services.voice.stt_base import BaseSTTService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Locate ffmpeg (needed by whisper for audio decoding) and add to PATH.
# ---------------------------------------------------------------------------


def _ensure_ffmpeg_in_path() -> None:
    """Search for ffmpeg.exe and prepend its directory to os.environ['PATH']."""
    if shutil.which("ffmpeg"):
        return  # Already in PATH

    candidates = [
        Path.home() / "bin" / "ffmpeg.exe",
        Path.home() / "tools" / "ffmpeg" / "ffmpeg-8.1.2-essentials_build" / "bin" / "ffmpeg.exe",
        Path.home() / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe",
    ]
    for p in candidates:
        if p.is_file():
            bin_dir = str(p.parent)
            os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
            logger.info("ffmpeg added to PATH from %s", bin_dir)
            return

    logger.warning("ffmpeg not found — STT will fail. Download: https://ffmpeg.org/")


_ensure_ffmpeg_in_path()

# ---------------------------------------------------------------------------
# Lazy-loaded whisper model singleton
# ---------------------------------------------------------------------------
_whisper_model = None
_whisper_model_name: str | None = None


def _get_whisper_model(model_name: str):
    """Lazy-load a whisper model (singleton per model name)."""
    global _whisper_model, _whisper_model_name
    if _whisper_model is not None and _whisper_model_name == model_name:
        return _whisper_model

    logger.info("Loading Whisper model: %s ...", model_name)
    import whisper
    _whisper_model = whisper.load_model(model_name)
    _whisper_model_name = model_name
    logger.info("Whisper model loaded: %s", model_name)
    return _whisper_model


# ---------------------------------------------------------------------------
# Implementations
# ---------------------------------------------------------------------------

class MockSTTService(BaseSTTService):
    """Mock STT — returns a hardcoded placeholder string."""

    async def transcribe(self, audio_data: bytes) -> str:
        return "（模拟语音识别结果）这是一个关于产品咨询的语音输入。"


class WhisperSTTService(BaseSTTService):
    """Real STT using OpenAI Whisper running locally.

    The base model (~140 MB) is downloaded once and reused.
    Audio is written to a temp file because whisper expects a file path.
    """

    def __init__(self, model_name: str = "base"):
        self._model_name = model_name

    @property
    def model(self):
        return _get_whisper_model(self._model_name)

    async def transcribe(self, audio_data: bytes) -> str:
        # Detect format from header for correct file extension
        suffix = ".wav" if audio_data[:4] == b"RIFF" else ".webm"

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        try:
            tmp.write(audio_data)
            tmp.close()

            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.model.transcribe(
                    tmp.name,
                    language="zh",
                    fp16=False,
                    verbose=False,
                ),
            )
            text = result.get("text", "").strip()
            logger.info("Whisper transcribed %d chars: %s", len(text), text[:100])
            return text
        except Exception as exc:
            logger.error("Whisper transcription failed: %s", exc)
            msg = str(exc)
            if "WinError 2" in msg or "ffmpeg" in msg.lower():
                raise RuntimeError(
                    "音频解码失败：未找到 ffmpeg。请安装 ffmpeg 并加入 PATH。\n"
                    "下载: https://ffmpeg.org/download.html"
                ) from exc
            raise RuntimeError(f"语音识别失败: {exc}") from exc
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_stt_service: BaseSTTService | None = None


def get_stt_service() -> BaseSTTService:
    """Return the configured STT service (singleton)."""
    global _stt_service
    if _stt_service is not None:
        return _stt_service

    from app.core.config import settings

    provider = settings.STT_PROVIDER.lower()
    if provider == "whisper":
        _stt_service = WhisperSTTService(model_name=settings.WHISPER_MODEL)
    else:
        logger.info("STT_PROVIDER=%s — using MockSTTService", provider)
        _stt_service = MockSTTService()

    return _stt_service
