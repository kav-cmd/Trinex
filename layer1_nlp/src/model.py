"""
src/model.py
DistilBERT tokenizer, model factory, and compute_metrics for HuggingFace Trainer.
"""

import numpy as np
from datasets import Dataset
from transformers import (
    DistilBertForSequenceClassification,
    DistilBertTokenizerFast,
)
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
)

MODEL_NAME = "distilbert-base-uncased"
MAX_LENGTH = 128

tokenizer = DistilBertTokenizerFast.from_pretrained(MODEL_NAME)


def tokenize_df(df_slice) -> Dataset:
    """Convert a pandas DataFrame slice into a tokenized HuggingFace Dataset."""
    ds = Dataset.from_pandas(df_slice[["text", "label"]].reset_index(drop=True))
    ds = ds.map(
        lambda batch: tokenizer(
            batch["text"],
            truncation=True,
            padding="max_length",
            max_length=MAX_LENGTH,
        ),
        batched=True,
    )
    ds = ds.rename_column("label", "labels")
    ds.set_format("torch", columns=["input_ids", "attention_mask", "labels"])
    return ds


def build_model() -> DistilBertForSequenceClassification:
    """Fresh DistilBERT head for binary classification."""
    return DistilBertForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=2,
        id2label={0: "HAM", 1: "FRAUD"},
        label2id={"HAM": 0, "FRAUD": 1},
    )


def compute_metrics(eval_pred) -> dict:
    """Metrics callback for HuggingFace Trainer."""
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {
        "accuracy": accuracy_score(labels, preds),
        "f1": f1_score(labels, preds, average="binary"),
        "precision": precision_score(labels, preds, average="binary", zero_division=0),
        "recall": recall_score(labels, preds, average="binary"),
    }
