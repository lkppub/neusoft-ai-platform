"""Text-to-Speech abstract base class."""

from abc import ABC, abstractmethod


class BaseTTSService(ABC):
    """Abstract interface for text-to-speech engines."""

    @abstractmethod
    async def synthesize(self, text: str, voice: str | None = None, rate: str = "+0%") -> bytes:
        """Convert text to speech audio.

        Args:
            text: The text to synthesize.
            voice: Voice identifier (provider-specific). Uses engine default if None.
            rate: Speech rate adjustment, e.g. "+10%" or "-20%".

        Returns:
            MP3 audio bytes.
        """
        ...
