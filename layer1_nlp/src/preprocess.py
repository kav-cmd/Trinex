"""
src/preprocess.py
Text cleaning, deduplication, and saving the processed dataset.
"""

import re
import pandas as pd


def clean_text(text) -> str:
    """Normalize whitespace and strip."""
    if not isinstance(text, str):
        return ""
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def preprocess(df: pd.DataFrame, save_path: str = None) -> pd.DataFrame:
    """Clean text, cast labels, drop short/duplicate rows."""
    df = df.copy()
    df["text"] = df["text"].apply(clean_text)
    df["label"] = df["label"].astype(int)

    # Drop very short texts
    df = df[df["text"].str.len() > 5].reset_index(drop=True)

    # Deduplicate
    before = len(df)
    df = df.drop_duplicates(subset="text").reset_index(drop=True)
    print(f"Removed {before - len(df)} duplicates. Remaining: {len(df)}")
    print(f"\nFinal label distribution:\n{df['label'].value_counts()}")
    if save_path:
        df.to_csv(save_path, index=False)
        print(f"[SUCCESS] Saved to {save_path}")

    return df
