"""
src/data_loader.py
Loads and merges all datasets: HuggingFace sms_spam + custom Indian fraud + CertIn.
"""

import os
import pandas as pd
from datasets import load_dataset


def load_huggingface_sms() -> pd.DataFrame:
    """Load the UCI SMS Spam dataset from HuggingFace (~5,574 rows)."""
    print("Loading sms_spam from HuggingFace...")
    hf = load_dataset("sms_spam", split="train", trust_remote_code=True)
    df = hf.to_pandas().rename(columns={"sms": "text"})
    df = df[["text", "label"]]
    df["source"] = "uci_hf"
    print(f"  HuggingFace SMS Spam: {len(df)} rows | {df['label'].value_counts().to_dict()}")
    return df


def load_custom_datasets(raw_dir: str) -> list[pd.DataFrame]:
    """Load Indian fraud and CertIn CSVs if present."""
    frames = []

    indian_path = os.path.join(raw_dir, "indian_fraud_collected.csv")
    if os.path.exists(indian_path):
        df = pd.read_csv(indian_path, encoding="latin-1")[["text", "label"]]
        df["source"] = "indian"
        frames.append(df)
        print(f"  Indian Fraud: {len(df)} rows | {df['label'].value_counts().to_dict()}")
    else:
        print("  indian_fraud_collected.csv not found — skipping")

    certin_path = os.path.join(raw_dir, "certIn_advisories.csv")
    if os.path.exists(certin_path):
        df = pd.read_csv(certin_path, encoding="latin-1")[["text", "label"]]
        df["source"] = "certin"
        frames.append(df)
        print(f"  CertIn: {len(df)} rows | {df['label'].value_counts().to_dict()}")
    else:
        print("  certIn_advisories.csv not found — skipping")

    return frames


def load_all(raw_dir: str = "data/raw") -> pd.DataFrame:
    """Merge all sources into one DataFrame."""
    hf_df = load_huggingface_sms()
    custom = load_custom_datasets(raw_dir)

    df = pd.concat([hf_df] + custom, ignore_index=True)
    print(f"\n✅ Total samples (raw): {len(df)}")
    print(f"Label distribution:\n{df['label'].value_counts()}")
    print(f"Source distribution:\n{df['source'].value_counts()}")
    return df
