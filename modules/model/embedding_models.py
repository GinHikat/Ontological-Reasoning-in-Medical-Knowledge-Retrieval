import numpy as np
import torch
import torch.nn.functional as F
from tqdm import tqdm
from transformers import AutoModel, AutoTokenizer


class EmbeddingModels:
    """Thin wrapper around Hugging Face encoder models used for SapBERT retrieval."""

    def __init__(self, model_choice: str):
        self.model_choice = model_choice
        self.tokenizer = AutoTokenizer.from_pretrained(model_choice)
        self.model = AutoModel.from_pretrained(model_choice)
        self.device = self._select_device()
        self.model.to(self.device)
        self.model.eval()

    @staticmethod
    def _select_device() -> torch.device:
        if torch.cuda.is_available():
            return torch.device("cuda")
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")

    @staticmethod
    def _mean_pool(
        last_hidden_state: torch.Tensor, attention_mask: torch.Tensor
    ) -> torch.Tensor:
        mask = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
        summed = torch.sum(last_hidden_state * mask, dim=1)
        counts = torch.clamp(mask.sum(dim=1), min=1e-9)
        return summed / counts

    def encode_text(
        self, texts, batch_size: int = 32, show_progress: bool = False
    ) -> np.ndarray:
        if isinstance(texts, str):
            texts = [texts]
        texts = list(texts)
        if not texts:
            return np.empty((0, self.model.config.hidden_size), dtype=np.float32)

        embeddings = []
        iterator = range(0, len(texts), batch_size)
        if show_progress:
            iterator = tqdm(
                iterator,
                total=(len(texts) + batch_size - 1) // batch_size,
                desc="Encoding",
            )

        with torch.no_grad():
            for start in iterator:
                batch = texts[start : start + batch_size]
                encoded = self.tokenizer(
                    batch,
                    padding=True,
                    truncation=True,
                    max_length=128,
                    return_tensors="pt",
                )
                encoded = {key: value.to(self.device) for key, value in encoded.items()}
                outputs = self.model(**encoded)
                pooled = self._mean_pool(
                    outputs.last_hidden_state, encoded["attention_mask"]
                )
                pooled = F.normalize(pooled, p=2, dim=1)
                embeddings.append(pooled.cpu().numpy())

        return np.vstack(embeddings).astype(np.float32)
