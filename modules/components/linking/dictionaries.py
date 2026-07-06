from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from modules.core.config import ProjectPaths


@dataclass
class DictionaryBundle:
    diagnoses: pd.DataFrame
    diagnosis_embeddings: np.ndarray
    drugs: pd.DataFrame
    drug_embeddings: np.ndarray
    symptoms: pd.DataFrame
    symptom_embeddings: np.ndarray


class CompetitionDictionaryStore:
    """Lazy loader for the precomputed competition dictionaries and embeddings."""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or ProjectPaths().viettel_base_dir
        self._bundle: DictionaryBundle | None = None

    @staticmethod
    def _read_csv(path: Path) -> pd.DataFrame:
        return pd.read_csv(path) if path.exists() else pd.DataFrame()

    @staticmethod
    def _read_npy(path: Path) -> np.ndarray:
        return np.load(path) if path.exists() else np.array([])

    def load(self) -> DictionaryBundle:
        if self._bundle is None:
            self._bundle = DictionaryBundle(
                diagnoses=self._read_csv(self.base_dir / "short_diagnosis.csv"),
                diagnosis_embeddings=self._read_npy(
                    self.base_dir / "short_diagnosis.npy"
                ),
                drugs=self._read_csv(self.base_dir / "short_drug.csv"),
                drug_embeddings=self._read_npy(self.base_dir / "short_drug.npy"),
                symptoms=self._read_csv(self.base_dir / "short_symptom.csv"),
                symptom_embeddings=self._read_npy(self.base_dir / "short_symptom.npy"),
            )
        return self._bundle
