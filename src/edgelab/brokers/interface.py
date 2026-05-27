"""Abstract broker interface placeholders."""

from abc import ABC, abstractmethod
from typing import Any


class BrokerAdapter(ABC):
    """Abstract broker adapter placeholder."""

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Return adapter status without placing orders."""
