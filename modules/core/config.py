from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    """Centralized project paths so scripts do not have to infer locations repeatedly."""

    root: Path = field(default_factory=lambda: Path(__file__).resolve().parents[2])

    @property
    def data_dir(self) -> Path:
        return self.root / "v_dataset"

    @property
    def test_dir(self) -> Path:
        return self.data_dir / "var" / "test"

    @property
    def output_dir(self) -> Path:
        return self.root / "output"

    @property
    def viettel_base_dir(self) -> Path:
        return self.data_dir / "viettel" / "base"
