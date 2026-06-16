"""
src/evaluate.py
Cross-validation summary, F1 bar chart, and averaged confusion matrix plot.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


def print_cv_summary(fold_metrics: list[dict]):
    """Print per-fold and mean ± std metrics."""
    metrics_df = pd.DataFrame(fold_metrics)

    print("\n[Per-Fold Metrics]:")
    print(metrics_df.to_string(index=False))
    print("\n[Mean and Std across folds]:")

    for col in ["accuracy", "f1", "precision", "recall"]:
        mean = metrics_df[col].mean()
        std = metrics_df[col].std()
        flag = ""
        if col == "f1":
            if mean > 0.95:
                flag = "  [WARNING] Very high — verify no leakage"
            elif mean > 0.85:
                flag = "  [OK] Good generalisation"
            else:
                flag = "  [WARNING] Consider more data or epochs"
        print(f"  {col:<12}: {mean:.4f} ± {std:.4f}{flag}")

    return metrics_df


def plot_cv_results(fold_metrics: list[dict], all_cms: list, save_path: str = None):
    """Plot F1 per fold and averaged confusion matrix."""
    metrics_df = pd.DataFrame(fold_metrics)
    avg_cm = np.mean(all_cms, axis=0).astype(int)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # F1 bar chart
    axes[0].bar(
        [f"Fold {m['fold']}" for m in fold_metrics],
        [m["f1"] for m in fold_metrics],
        color="steelblue",
        edgecolor="black",
    )
    axes[0].axhline(
        metrics_df["f1"].mean(),
        color="red",
        linestyle="--",
        label=f"Mean F1 = {metrics_df['f1'].mean():.4f}",
    )
    axes[0].set_ylim(0, 1.05)
    axes[0].set_title("F1 Score per Fold")
    axes[0].set_ylabel("F1 Score")
    axes[0].legend()

    # Averaged confusion matrix
    sns.heatmap(
        avg_cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=["HAM", "FRAUD"],
        yticklabels=["HAM", "FRAUD"],
        ax=axes[1],
    )
    axes[1].set_title("Averaged Confusion Matrix (5 Folds)")
    axes[1].set_ylabel("True Label")
    axes[1].set_xlabel("Predicted Label")

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150)
        print(f"[SUCCESS] Saved: {save_path}")

    plt.show()
