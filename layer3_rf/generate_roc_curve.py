"""
TRINEX — Layer 3: RF Fingerprinting
File: generate_roc_curve.py

Purpose:
Generate the ROC (Receiver Operating Characteristic) curve for the
RF fingerprinting system. Shows the trade-off between legitimate
signal acceptance rate and rogue signal rejection rate across all
possible threshold values. Directly justifies the threshold=1.5
choice with data.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os

from fingerprinter import (
    fingerprint_from_signal,
    _get_or_train_classifier,
    classify_fingerprint,
)

RESULTS_DIR = os.path.join(os.path.dirname(__file__),
                           "..", "results", "rf_results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def collect_distances(n_per_class=300, snr_db=20,
                      channel_drift=0.20):
    """
    Collect nearest-neighbor distances for legitimate and rogue
    signals. Uses threshold=999 so every signal gets a distance
    regardless of whether it would normally be flagged.
    """
    clf = _get_or_train_classifier()
    legit_distances = []
    rogue_distances = []

    for tx in ["sbi_tower_profile", "hdfc_tower_profile"]:
        for s in range(n_per_class):
            seed = 70000 + hash(tx) % 1000 + s
            fp = fingerprint_from_signal(
                tx, snr_db=snr_db, n_symbols=1,
                seed=seed, channel_drift=channel_drift
            )
            result = classify_fingerprint(
                clf, fp["features"][0], threshold=999
            )
            legit_distances.append(result["min_distance"])

    for s in range(n_per_class * 2):
        seed = 80000 + s
        fp = fingerprint_from_signal(
            "rogue_transmitter", snr_db=snr_db,
            n_symbols=1, seed=seed,
            channel_drift=channel_drift
        )
        result = classify_fingerprint(
            clf, fp["features"][0], threshold=999
        )
        rogue_distances.append(result["min_distance"])

    return np.array(legit_distances), np.array(rogue_distances)


def compute_roc(legit_distances, rogue_distances):
    """
    Sweep threshold from 0 to max distance and compute TPR and FPR.
    Positive class = rogue signal (what we want to detect).
    Negative class = legitimate signal (what we want to accept).
    """
    all_distances = np.concatenate([legit_distances, rogue_distances])
    thresholds = np.linspace(0, all_distances.max() + 0.5, 500)

    tpr_list = []
    fpr_list = []

    for thresh in thresholds:
        tpr = np.mean(rogue_distances >= thresh)
        fpr = np.mean(legit_distances >= thresh)
        tpr_list.append(tpr)
        fpr_list.append(fpr)

    tpr = np.array(tpr_list)
    fpr = np.array(fpr_list)

    sort_idx = np.argsort(fpr)
    try:
        auc = np.trapezoid(tpr[sort_idx], fpr[sort_idx])
    except AttributeError:
        auc = np.trapz(tpr[sort_idx], fpr[sort_idx])

    return fpr, tpr, thresholds, abs(auc)


def find_operating_point(legit_distances, rogue_distances,
                         chosen_threshold=1.5):
    """Find TPR and FPR at the chosen threshold."""
    tpr = np.mean(rogue_distances >= chosen_threshold)
    fpr = np.mean(legit_distances >= chosen_threshold)
    return tpr, fpr


def plot_roc_curve(fpr, tpr, thresholds, auc,
                   op_fpr, op_tpr, save_path):
    """Generate the two-panel ROC curve figure."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    fig.suptitle("RF Fingerprinting — ROC Analysis",
                 fontsize=14, fontweight="bold")

    # ── Left: ROC curve ──────────────────────────────────────
    ax = axes[0]
    ax.plot(fpr, tpr, color="#1f77b4", linewidth=2.5,
            label=f"RF Fingerprinter (AUC = {auc:.4f})")
    ax.plot([0, 1], [0, 1], color="gray", linestyle="--",
            linewidth=1.2, label="Random classifier (AUC = 0.5)")
    ax.scatter([op_fpr], [op_tpr], color="#d62728",
               s=120, zorder=5,
               label=f"Operating point (threshold=1.5)\n"
                     f"TPR={op_tpr:.3f}, FPR={op_fpr:.3f}")
    ax.annotate(
        f"  threshold=1.5\n"
        f"  TPR={op_tpr:.2%}\n"
        f"  FPR={op_fpr:.2%}",
        xy=(op_fpr, op_tpr),
        xytext=(op_fpr + 0.08, op_tpr - 0.12),
        fontsize=9, color="#d62728",
        arrowprops=dict(arrowstyle="->",
                        color="#d62728", lw=1.2)
    )
    ax.set_xlabel(
        "False Positive Rate\n(legitimate signals wrongly flagged)",
        fontsize=11, fontweight="bold"
    )
    ax.set_ylabel(
        "True Positive Rate\n(rogue signals correctly detected)",
        fontsize=11, fontweight="bold"
    )
    ax.set_title("ROC Curve — Rogue Detection",
                 fontsize=12, fontweight="bold")
    ax.legend(loc="lower right", fontsize=9, framealpha=0.95)
    ax.grid(True, alpha=0.35)
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)

    # ── Right: TPR and FPR vs threshold ──────────────────────
    ax2 = axes[1]
    ax2.plot(thresholds, tpr, color="#2ca02c", linewidth=2.2,
             label="TPR — Rogue detection rate")
    ax2.plot(thresholds, fpr, color="#d62728", linewidth=2.2,
             label="FPR — Legitimate false-flag rate")
    ax2.axvline(x=1.5, color="black", linestyle="--",
                linewidth=1.8, label="Chosen threshold = 1.5")
    ax2.axhline(y=op_tpr, color="#2ca02c", linestyle=":",
                alpha=0.5, linewidth=1.2)
    ax2.axhline(y=op_fpr, color="#d62728", linestyle=":",
                alpha=0.5, linewidth=1.2)
    ax2.set_xlabel("Decision Threshold",
                   fontsize=11, fontweight="bold")
    ax2.set_ylabel("Rate", fontsize=11, fontweight="bold")
    ax2.set_title(
        "TPR and FPR vs Threshold\n(justifies threshold selection)",
        fontsize=12, fontweight="bold"
    )
    ax2.legend(loc="center right", fontsize=9, framealpha=0.95)
    ax2.grid(True, alpha=0.35)
    ax2.set_xlim(0, thresholds.max())
    ax2.set_ylim(-0.02, 1.05)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {os.path.basename(save_path)}")


if __name__ == "__main__":
    print("=" * 65)
    print("TRINEX — RF Fingerprinting ROC Curve Generation")
    print("=" * 65)

    print("\n[1] Collecting distances for legitimate and rogue signals")
    print("    (300 samples per class, SNR=20 dB, drift=0.20)")
    legit_dist, rogue_dist = collect_distances(
        n_per_class=300, snr_db=20, channel_drift=0.20
    )
    print(f"    Legitimate samples : {len(legit_dist)}")
    print(f"    Rogue samples      : {len(rogue_dist)}")
    print(f"    Legit dist range   : "
          f"{legit_dist.min():.3f} — {legit_dist.max():.3f}")
    print(f"    Rogue dist range   : "
          f"{rogue_dist.min():.3f} — {rogue_dist.max():.3f}")

    print("\n[2] Computing ROC curve across all threshold values")
    fpr, tpr, thresholds, auc = compute_roc(legit_dist, rogue_dist)
    print(f"    AUC = {auc:.4f}  (1.0 = perfect, 0.5 = random)")

    print("\n[3] Operating point at threshold = 1.5")
    op_tpr, op_fpr = find_operating_point(
        legit_dist, rogue_dist, chosen_threshold=1.5
    )
    print(f"    True Positive Rate  : {op_tpr:.2%}  "
          f"(rogue signals detected)")
    print(f"    False Positive Rate : {op_fpr:.2%}  "
          f"(legitimate signals wrongly flagged)")

    print("\n[4] Generating ROC plot")
    plot_roc_curve(
        fpr, tpr, thresholds, auc, op_fpr, op_tpr,
        save_path=os.path.join(RESULTS_DIR, "roc_curve.png")
    )

    print("\n[5] ROC Summary")
    print(f"    {'Metric':<35} | {'Value':>10}")
    print(f"    {'-'*35}-+-{'-'*10}")
    print(f"    {'AUC (Area Under Curve)':<35} | {auc:>10.4f}")
    print(f"    {'TPR at threshold=1.5':<35} | {op_tpr:>10.2%}")
    print(f"    {'FPR at threshold=1.5':<35} | {op_fpr:>10.2%}")
    print(f"    {'Legit dist max':<35} | "
          f"{legit_dist.max():>10.3f}")
    print(f"    {'Rogue dist min':<35} | "
          f"{rogue_dist.min():>10.3f}")
    print(f"    {'Gap (min rogue - max legit)':<35} | "
          f"{rogue_dist.min() - legit_dist.max():>10.3f}")

    print("\nROC curve saved to results/rf_results/roc_curve.png")
    print("=" * 65)