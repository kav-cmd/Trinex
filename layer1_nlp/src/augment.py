"""
src/augment.py
Text augmentation applied PER TRAINING FOLD only — no leakage into validation.
"""

import random
import pandas as pd


def augment_text(text: str, n: int = 1) -> list[str]:
    """Apply random word-level augmentation: swap, delete, or duplicate."""
    words = text.split()
    if len(words) < 4:
        return [text] * n

    augmented = []
    for _ in range(n):
        w = words.copy()
        aug_type = random.choice(["swap", "delete", "duplicate"])

        if aug_type == "swap" and len(w) >= 2:
            i, j = random.sample(range(len(w)), 2)
            w[i], w[j] = w[j], w[i]
        elif aug_type == "delete":
            del w[random.randint(0, len(w) - 1)]
        elif aug_type == "duplicate":
            idx = random.randint(0, len(w) - 1)
            w.insert(idx, w[idx])

        augmented.append(" ".join(w))
    return augmented


def augment_dataframe(
    train_df: pd.DataFrame,
    target_label: int = 1,
    multiplier: int = 2,
) -> pd.DataFrame:
    """
    Oversample the minority class using augmentation.
    Call this INSIDE each CV fold, never on the full dataset.
    """
    minority = train_df[train_df["label"] == target_label]
    aug_rows = []

    for _, row in minority.iterrows():
        for aug_text in augment_text(row["text"], n=multiplier):
            aug_rows.append({"text": aug_text, "label": row["label"]})

    aug_df = pd.DataFrame(aug_rows)
    result = (
        pd.concat([train_df, aug_df], ignore_index=True)
        .sample(frac=1, random_state=42)
        .reset_index(drop=True)
    )
    return result
