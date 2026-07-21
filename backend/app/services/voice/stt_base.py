"""Speech-to-Text abstract base class."""

from abc import ABC, abstractmethod


class BaseSTTService(ABC):
    """Abstract interface for speech-to-text engines."""

    @abstractmethod
    async def transcribe(self, audio_data: bytes) -> str:
        """Transcribe audio bytes into text.

        Args:
            audio_data: Raw audio file bytes (any format that ffmpeg can decode).

        Returns:
            Transcribed text string.
        """
        ...

    async def health_check(self) -> bool:
        """Check whether the STT engine is ready to transcribe."""
        return True
