"""
src/train.py
5-Fold Stratified Cross-Validation training loop for TRINEX DistilBERT.
"""

import os
import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from transformers import Trainer, TrainingArguments

from src.augment import augment_dataframe
from src.model import build_model, compute_metrics, tokenize_df, tokenizer

MODEL_OUTPUT = "models/distilbert_finetuned"


def run_cv(df: pd.DataFrame, n_splits: int = 5, output_dir: str = MODEL_OUTPUT):
    """
    Run stratified k-fold cross-validation.
    Saves the best-F1 model to `output_dir`.
    Returns fold_metrics list and all_cms list.
    """
    os.makedirs(output_dir, exist_ok=True)

    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    X, y = df["text"].values, df["label"].values

    fold_metrics = []
    all_cms = []
    best_f1 = -1

    for fold, (train_idx, val_idx) in enumerate(skf.split(X, y)):
        print(f"\n{'='*55}")
        print(f"  FOLD {fold + 1} / {n_splits}")
        print(f"{'='*55}")

        train_fold = df.iloc[train_idx].reset_index(drop=True)
        val_fold = df.iloc[val_idx].reset_index(drop=True)

        # Augment ONLY the training fold — validation stays clean
        train_fold = augment_dataframe(train_fold, target_label=1, multiplier=2)
        print(f"  Train (post-aug): {len(train_fold)} | Val: {len(val_fold)}")

        train_ds = tokenize_df(train_fold)
        val_ds = tokenize_df(val_fold)

        model = build_model()

        fold_output = f"/tmp/fold_{fold + 1}"
        training_args = TrainingArguments(
            output_dir=fold_output,
            num_train_epochs=3,
            per_device_train_batch_size=16,
            per_device_eval_batch_size=16,
            eval_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            metric_for_best_model="f1",
            greater_is_better=True,
            logging_steps=30,
            report_to="none",
            fp16=torch.cuda.is_available(),
            seed=42,
            weight_decay=0.01,
            warmup_ratio=0.1,
            learning_rate=2e-5,
        )

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_ds,
            eval_dataset=val_ds,
            compute_metrics=compute_metrics,
        )

        trainer.train()

        preds_out = trainer.predict(val_ds)
        preds = np.argmax(preds_out.predictions, axis=-1)
        labels = preds_out.label_ids

        acc = accuracy_score(labels, preds)
        f1 = f1_score(labels, preds, average="binary")
        prec = precision_score(labels, preds, average="binary", zero_division=0)
        rec = recall_score(labels, preds, average="binary")
        cm = confusion_matrix(labels, preds)

        fold_metrics.append(
            {"fold": fold + 1, "accuracy": acc, "f1": f1, "precision": prec, "recall": rec}
        )
        all_cms.append(cm)

        print(f"\n  Fold {fold+1} → Acc: {acc:.4f} | F1: {f1:.4f} | Prec: {prec:.4f} | Rec: {rec:.4f}")
        print(classification_report(labels, preds, target_names=["HAM", "FRAUD"]))

        if f1 > best_f1:
            best_f1 = f1
            trainer.save_model(output_dir)
            tokenizer.save_pretrained(f"{output_dir}/tokenizer")
            print(f"  ⭐ New best model saved (F1={best_f1:.4f})")

    print("\n✅ Cross-validation complete!")
    return fold_metrics, all_cms, best_f1
