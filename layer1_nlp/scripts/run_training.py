"""
scripts/run_training.py
End-to-end training entrypoint for TRINEX.

Run:
    python scripts/run_training.py
"""

import os
import sys
import pandas as pd

# Make src importable from scripts directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_loader import load_all
from src.preprocess import preprocess
from src.train import run_cv
from src.evaluate import print_cv_summary, plot_cv_results
from src.adversarial import run_adversarial_tests

RAW_DIR       = "data/dataset/raw"
PROCESSED_DIR = "data/dataset/processed"
MODEL_OUTPUT  = "models/distilbert_finetuned"
PLOTS_DIR     = "models"

os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(PLOTS_DIR, exist_ok=True)


def main():
    # 1. Load & merge datasets
    df_raw = load_all(raw_dir=RAW_DIR)

    # 2. Clean & preprocess
    df = preprocess(df_raw, save_path=os.path.join(PROCESSED_DIR, "final_dataset.csv"))

    # 3. Train with 5-fold CV
    fold_metrics, all_cms, best_f1 = run_cv(df, n_splits=5, output_dir=MODEL_OUTPUT)

    # 4. Summarise & plot
    metrics_df = print_cv_summary(fold_metrics)
    metrics_df.to_csv(os.path.join(PLOTS_DIR, "cv_metrics.csv"), index=False)
    plot_cv_results(fold_metrics, all_cms, save_path=os.path.join(PLOTS_DIR, "cv_summary.png"))

    # 5. Adversarial tests on saved model
    run_adversarial_tests(MODEL_OUTPUT)

    print(f"\n🏆 Best model F1: {best_f1:.4f} — saved to {MODEL_OUTPUT}")


if __name__ == "__main__":
    main()
