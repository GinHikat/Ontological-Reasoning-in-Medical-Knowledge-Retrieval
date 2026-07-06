from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from modules.core.schemas import FinalEntity


class BaseOutputFormatter(ABC):
    @abstractmethod
    def format(self, entities: list[FinalEntity]) -> list[dict[str, Any]]:
        """Convert final entities into a serializable output schema."""
