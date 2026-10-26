
import json
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer


MODEL_DIR = Path(__file__).resolve().parents[2] / "model"


class ONNXTransactionClassifier:
    """Run transaction classification using a local ONNX model."""

    def __init__(
        self,
        model_path: Path | str | None = None,
        tokenizer_path: Path | str | None = None,
        labels_path: Path | str | None = None,
    ) -> None:
        self.model_path = Path(model_path or MODEL_DIR / "model_quantized.onnx")
        self.tokenizer_path = Path(
            tokenizer_path or MODEL_DIR / "tokenizer.json"
        )
        self.labels_path = Path(
            labels_path or MODEL_DIR / "label_mapping.json"
        )

        for path in (
            self.model_path,
            self.tokenizer_path,
            self.labels_path,
        ):
            if not path.is_file():
                raise FileNotFoundError(f"Required model file not found: {path}")

        with self.labels_path.open("r", encoding="utf-8") as file:
            mapping = json.load(file)

        self.id2label = {
            int(index): label
            for index, label in mapping["id2label"].items()
        }

        self.tokenizer = Tokenizer.from_file(str(self.tokenizer_path))
        self.tokenizer.enable_truncation(max_length=512)
        self.tokenizer.enable_padding(
            pad_id=self.tokenizer.token_to_id("[PAD]") or 0,
            pad_token="[PAD]",
        )

        self.session = ort.InferenceSession(
            str(self.model_path),
            providers=["CPUExecutionProvider"],
        )

        self.input_names = {item.name for item in self.session.get_inputs()}
        required_inputs = {"input_ids", "attention_mask"}

        if not required_inputs.issubset(self.input_names):
            raise ValueError(
                f"Unexpected ONNX inputs: {sorted(self.input_names)}"
            )

        self.output_name = self.session.get_outputs()[0].name

    def predict(self, description: str) -> dict[str, Any]:
        """Return the model's best category and its softmax confidence."""
        text = description.strip()

        if not text:
            raise ValueError("Transaction description cannot be empty.")

        encoded = self.tokenizer.encode(text)

        inputs = {
            "input_ids": np.asarray(
                [encoded.ids], dtype=np.int64
            ),
            "attention_mask": np.asarray(
                [encoded.attention_mask], dtype=np.int64
            ),
        }

        logits = self.session.run(
            [self.output_name],
            inputs,
        )[0][0]

        # Numerically stable softmax.
        shifted = logits - np.max(logits)
        probabilities = np.exp(shifted)
        probabilities /= probabilities.sum()

        predicted_id = int(np.argmax(probabilities))

        return {
            "category": self.id2label[predicted_id],
            "confidence": float(probabilities[predicted_id]),
            "probabilities": {
                self.id2label[index]: float(probability)
                for index, probability in enumerate(probabilities)
                if index in self.id2label
            },
        }
