"""
TRINEX — Layer 3: RF Fingerprinting
File: evaluate_rf.py

Purpose:
Generate the final evaluation plots and metrics for the RF
fingerprinting module. Produces publication-quality figures
saved to results/rf_results/ and a CSV summary file.

Outputs:
    1. confusion_matrix.png       — 3x3 classification matrix
    2. accuracy_vs_snr.png        — accuracy curves across SNR
    3. distance_distributions.png — legit vs rogue distance hist
    4. attack_summary.png         — combined attack robustness
    5. evaluation_results.csv     — all numbers in CSV form
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import csv
import os
from sklearn.metrics import confusion_matrix

from fingerprinter import (
    fingerprint_from_signal,
    _get_or_train_classifier,
    classify_fingerprint,
    REGISTERED_TRANSMITTERS,
    ROGUE_DISTANCE_THRESHOLD,
)
from attack_injector import (
    simulate_jamming_attack,
    simulate_replay_attack,
    simulate_rogue_spoofing,
)

# ── Config ──────────────────────────────────────────────────
RESULTS_DIR = os.path.join(os.path.dirname(__file__),
                           "..", "results", "rf_results")
os.makedirs(RESULTS_DIR, exist_ok=True)

ALL_TRANSMITTERS = ["sbi_tower_profile", "hdfc_tower_profile",
                    "rogue_transmitter"]
LABELS = {
    "sbi_tower_profile":   "SBI Tower",
    "hdfc_tower_profile":  "HDFC Tower",
    "rogue_transmitter":   "Rogue",
    "unknown_transmitter": "Unknown"
}

plt.rcParams.update({"font.size": 11, "figure.dpi": 120})


# ══════════════════════════════════════════════════════════════
# DATA COLLECTION — RUN MANY CLASSIFICATION TRIALS
# ══════════════════════════════════════════════════════════════

def collect_classification_data(n_per_transmitter=200, snr_db=20,
                                channel_drift=0.20):
    """Test trials WITH realistic channel drift."""
    clf = _get_or_train_classifier()
    y_true, y_pred, distances = [], [], []

    for tx in ALL_TRANSMITTERS:
        for s in range(n_per_transmitter):
            seed = 50000 + hash(tx) % 1000 + s
            fp = fingerprint_from_signal(tx, snr_db=snr_db,
                                         n_symbols=1, seed=seed,
                                         channel_drift=channel_drift)
            result = classify_fingerprint(clf, fp["features"][0])
            y_true.append(tx)
            y_pred.append(result["predicted_label"])
            distances.append(result["min_distance"])

    return np.array(y_true), np.array(y_pred), np.array(distances)


def collect_accuracy_curves(n_per_point=50,
                            snr_range=(-5, 30, 5),
                            channel_drift=0.20):
    """SNR sweep WITH realistic channel drift."""
    clf = _get_or_train_classifier()
    snr_values = list(range(snr_range[0], snr_range[1] + 1, snr_range[2]))
    accuracy_by_tx = {tx: [] for tx in ALL_TRANSMITTERS}

    for snr in snr_values:
        for tx in ALL_TRANSMITTERS:
            correct = 0
            for s in range(n_per_point):
                seed = 60000 + hash(tx) % 1000 + s + snr * 17
                fp = fingerprint_from_signal(tx, snr_db=snr,
                                             n_symbols=1, seed=seed,
                                             channel_drift=channel_drift)
                result = classify_fingerprint(clf, fp["features"][0])
                if tx == "rogue_transmitter":
                    if result["predicted_label"] == "unknown_transmitter":
                        correct += 1
                else:
                    if result["predicted_label"] == tx:
                        correct += 1
            accuracy_by_tx[tx].append(correct / n_per_point)

    return snr_values, accuracy_by_tx


def collect_accuracy_curves(n_per_point=50,
                            snr_range=(-5, 30, 5)):
    """
    Sweep SNR and measure per-class accuracy at each SNR level.
    Returns dict: {transmitter: [accuracy at each SNR]}.
    """
    clf = _get_or_train_classifier()
    snr_values = list(range(snr_range[0], snr_range[1] + 1, snr_range[2]))

    accuracy_by_tx = {tx: [] for tx in ALL_TRANSMITTERS}

    for snr in snr_values:
        for tx in ALL_TRANSMITTERS:
            correct = 0
            for s in range(n_per_point):
                seed = 60000 + hash(tx) % 1000 + s + snr * 17
                fp = fingerprint_from_signal(tx, snr_db=snr,
                                             n_symbols=1, seed=seed)
                result = classify_fingerprint(clf, fp["features"][0])

                # Counted as correct if:
                # - registered tx and predicted matches OR
                # - rogue tx and predicted is "unknown_transmitter"
                if tx == "rogue_transmitter":
                    if result["predicted_label"] == "unknown_transmitter":
                        correct += 1
                else:
                    if result["predicted_label"] == tx:
                        correct += 1
            accuracy_by_tx[tx].append(correct / n_per_point)

    return snr_values, accuracy_by_tx


# ══════════════════════════════════════════════════════════════
# PLOT 1 — CONFUSION MATRIX
# ══════════════════════════════════════════════════════════════

def plot_confusion_matrix(y_true, y_pred, snr_db, save_path):
    """3x3 confusion matrix showing class-by-class predictions."""
    # Map predictions to display labels
    display_labels = ["SBI Tower", "HDFC Tower", "Rogue"]

    # Build the matrix manually for clarity
    cm = np.zeros((3, 3), dtype=int)
    tx_to_idx = {
        "sbi_tower_profile": 0,
        "hdfc_tower_profile": 1,
        "rogue_transmitter": 2
    }
    pred_to_idx = {
        "sbi_tower_profile": 0,
        "hdfc_tower_profile": 1,
        "rogue_transmitter": 2,         # if predicted as rogue (rare)
        "unknown_transmitter": 2,        # rogue-correct prediction
    }

    for true_lbl, pred_lbl in zip(y_true, y_pred):
        i = tx_to_idx[true_lbl]
        j = pred_to_idx.get(pred_lbl, 2)
        cm[i, j] += 1

    # Normalise per row to get percentages
    cm_pct = cm / cm.sum(axis=1, keepdims=True) * 100

    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(cm_pct, cmap="Greens", vmin=0, vmax=100,
                   aspect="auto")

    ax.set_xticks(range(3))
    ax.set_yticks(range(3))
    ax.set_xticklabels(display_labels, fontsize=11)
    ax.set_yticklabels(display_labels, fontsize=11)
    ax.set_xlabel("Predicted Class", fontsize=12, fontweight="bold")
    ax.set_ylabel("True Class", fontsize=12, fontweight="bold")
    ax.set_title(
        f"Classification Confusion Matrix at SNR = {snr_db} dB\n"
        f"({y_true.shape[0]} total trials, "
        f"{y_true.shape[0]//3} per class)",
        fontsize=12, fontweight="bold"
    )

    # Annotate each cell with both percentage and raw count
    for i in range(3):
        for j in range(3):
            val_pct = cm_pct[i, j]
            val_raw = cm[i, j]
            color = "white" if val_pct > 50 else "black"
            ax.text(j, i, f"{val_pct:.1f}%\n({val_raw})",
                    ha="center", va="center",
                    color=color, fontsize=12, fontweight="bold")

    cbar = plt.colorbar(im, ax=ax, label="Percentage (%)")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {os.path.basename(save_path)}")
    return cm, cm_pct


# ══════════════════════════════════════════════════════════════
# PLOT 2 — ACCURACY VS SNR
# ══════════════════════════════════════════════════════════════

def plot_accuracy_vs_snr(snr_values, accuracy_by_tx, save_path):
    """Three accuracy curves (one per transmitter) vs SNR."""
    fig, ax = plt.subplots(figsize=(9, 5.5))

    colors = {
        "sbi_tower_profile":  "#1f77b4",
        "hdfc_tower_profile": "#ff7f0e",
        "rogue_transmitter":  "#d62728"
    }
    markers = {
        "sbi_tower_profile":  "o",
        "hdfc_tower_profile": "s",
        "rogue_transmitter":  "^"
    }
    nice_labels = {
        "sbi_tower_profile":  "SBI Tower (correct ID)",
        "hdfc_tower_profile": "HDFC Tower (correct ID)",
        "rogue_transmitter":  "Rogue (correctly flagged)"
    }

    for tx in ALL_TRANSMITTERS:
        ax.plot(snr_values,
                [a * 100 for a in accuracy_by_tx[tx]],
                marker=markers[tx], color=colors[tx],
                label=nice_labels[tx],
                linewidth=2.2, markersize=8)

    ax.set_xlabel("SNR (dB)", fontsize=12, fontweight="bold")
    ax.set_ylabel("Classification Accuracy (%)",
                  fontsize=12, fontweight="bold")
    ax.set_title("Classification Accuracy vs SNR",
                 fontsize=13, fontweight="bold")
    ax.legend(loc="lower right", fontsize=10, framealpha=0.95)
    ax.grid(True, alpha=0.35)
    ax.set_ylim(-3, 105)
    ax.set_xticks(snr_values)
    ax.axhline(y=95, color="green", linestyle=":", alpha=0.5,
               linewidth=1.2)
    ax.text(snr_values[0], 96, "95% target",
            fontsize=9, color="green", style="italic")

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {os.path.basename(save_path)}")


# ══════════════════════════════════════════════════════════════
# PLOT 3 — DISTANCE DISTRIBUTION (justifies threshold choice)
# ══════════════════════════════════════════════════════════════

def plot_distance_distributions(y_true, distances, save_path):
    """Histogram of nearest-neighbor distances for legit vs rogue."""
    fig, ax = plt.subplots(figsize=(9, 5.5))

    legit_mask = (y_true == "sbi_tower_profile") | \
                 (y_true == "hdfc_tower_profile")
    legit_dist = distances[legit_mask]
    rogue_dist = distances[~legit_mask]

    bins = np.linspace(0, max(distances.max(), 6) + 0.5, 30)
    ax.hist(legit_dist, bins=bins, alpha=0.65, color="#1f77b4",
            label=f"Legitimate signals (n={len(legit_dist)})",
            edgecolor="white")
    ax.hist(rogue_dist, bins=bins, alpha=0.65, color="#d62728",
            label=f"Rogue signals (n={len(rogue_dist)})",
            edgecolor="white")

    ax.axvline(x=ROGUE_DISTANCE_THRESHOLD, color="black",
               linestyle="--", linewidth=2,
               label=f"Decision threshold = {ROGUE_DISTANCE_THRESHOLD}")

    ax.set_xlabel("Distance to nearest training sample",
                  fontsize=12, fontweight="bold")
    ax.set_ylabel("Number of trials",
                  fontsize=12, fontweight="bold")
    ax.set_title(
        "Nearest-Neighbor Distance Distributions\n"
        "(why the threshold separates legitimate from rogue)",
        fontsize=12, fontweight="bold"
    )
    ax.legend(loc="upper right", fontsize=10, framealpha=0.95)
    ax.grid(True, alpha=0.35)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {os.path.basename(save_path)}")


# ══════════════════════════════════════════════════════════════
# PLOT 4 — ATTACK SUMMARY (combined)
# ══════════════════════════════════════════════════════════════

def plot_attack_summary(jam_results, replay_results,
                         rogue_result, save_path):
    """Single-figure summary of all three attack performance metrics."""
    fig, ax = plt.subplots(figsize=(10, 6))

    # Pick representative attack outcomes
    jam_at_0db   = next(r for r in jam_results if r["jam_db"] == 0)
    jam_at_10db  = next(r for r in jam_results if r["jam_db"] == 10)
    replay_low   = replay_results[1]   # perturb 0.05
    replay_high  = replay_results[-2]  # perturb 0.30

    categories = [
        "Jamming\n(0 dB)",
        "Jamming\n(10 dB)",
        "Replay\n(low perturb)",
        "Replay\n(high perturb)",
        "Rogue\nspoofing",
    ]
    detection_rates = [
        jam_at_0db["flagged_unknown"] * 100,
        jam_at_10db["flagged_unknown"] * 100,
        replay_low["total_detection"] * 100,
        replay_high["total_detection"] * 100,
        rogue_result["detection_rate"] * 100,
    ]
    colors = ["#ff7f0e", "#d62728", "#9467bd",
              "#9467bd", "#2ca02c"]

    bars = ax.bar(categories, detection_rates,
                  color=colors, edgecolor="white",
                  linewidth=1.5, width=0.6)
    for bar, val in zip(bars, detection_rates):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 1.5,
                f"{val:.1f}%", ha="center",
                fontsize=11, fontweight="bold")

    ax.set_ylabel("Attack Detection Rate (%)",
                  fontsize=12, fontweight="bold")
    ax.set_title("RF Fingerprinting — Attack Detection Summary",
                 fontsize=13, fontweight="bold")
    ax.set_ylim(0, 115)
    ax.grid(True, alpha=0.35, axis="y")
    ax.axhline(y=95, color="green", linestyle=":",
               alpha=0.5, linewidth=1.2)
    ax.text(-0.3, 96, "95% target",
            fontsize=9, color="green", style="italic")

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {os.path.basename(save_path)}")


# ══════════════════════════════════════════════════════════════
# CSV EXPORT
# ══════════════════════════════════════════════════════════════

def export_results_csv(snr_values, accuracy_by_tx,
                       cm, jam_results,
                       replay_results, rogue_result, save_path):
    """Export all numerical results to a single CSV file."""
    with open(save_path, "w", newline="") as f:
        w = csv.writer(f)

        w.writerow(["TRINEX RF Fingerprinting — Evaluation Results"])
        w.writerow([])

        # Confusion matrix
        w.writerow(["Confusion Matrix (counts)"])
        w.writerow(["", "Pred SBI", "Pred HDFC", "Pred Unknown/Rogue"])
        for i, name in enumerate(["True SBI", "True HDFC",
                                  "True Rogue"]):
            w.writerow([name] + list(cm[i]))
        w.writerow([])

        # Accuracy curves
        w.writerow(["Accuracy vs SNR"])
        w.writerow(["SNR (dB)"] + [LABELS[tx]
                                    for tx in ALL_TRANSMITTERS])
        for i, snr in enumerate(snr_values):
            w.writerow([snr] + [f"{accuracy_by_tx[tx][i]:.4f}"
                                for tx in ALL_TRANSMITTERS])
        w.writerow([])

        # Jamming results
        w.writerow(["Jamming Attack Results"])
        w.writerow(["Jam (dB)", "Correct ID",
                    "Flagged Unknown", "Misclassified"])
        for r in jam_results:
            w.writerow([r["jam_db"],
                        f"{r['accuracy']:.4f}",
                        f"{r['flagged_unknown']:.4f}",
                        f"{r['misclassified']:.4f}"])
        w.writerow([])

        # Replay results
        w.writerow(["Replay Attack Results"])
        w.writerow(["Perturbation", "CIR Detection",
                    "TS Detection", "Both Detection",
                    "Total Detection", "Acceptance Rate"])
        for r in replay_results:
            w.writerow([f"{r['perturbation']:.2f}",
                        f"{r['cir_detection']:.4f}",
                        f"{r['ts_detection']:.4f}",
                        f"{r['both_detection']:.4f}",
                        f"{r['total_detection']:.4f}",
                        f"{r['acceptance_rate']:.4f}"])
        w.writerow([])

        # Rogue spoofing results
        w.writerow(["Rogue Spoofing Results"])
        w.writerow(["Trials", "Flagged",
                    "Accepted", "Detection Rate"])
        w.writerow([rogue_result["n_trials"],
                    rogue_result["flagged"],
                    rogue_result["accepted"],
                    f"{rogue_result['detection_rate']:.4f}"])

    print(f"  Saved: {os.path.basename(save_path)}")


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("TRINEX — RF Fingerprinting Final Evaluation")
    print("=" * 70)

    # ── Step 1: Classification trials at SNR=20 dB ──
    print("\n[1] Running 600 classification trials (200 per transmitter)"
          " at SNR=20 dB")
    y_true, y_pred, distances = collect_classification_data(
        n_per_transmitter=200, snr_db=20
    )
    print(f"    Total trials: {len(y_true)}")
    correct = np.sum(
        [(t == p) or
         (t == "rogue_transmitter" and p == "unknown_transmitter")
         for t, p in zip(y_true, y_pred)])
    print(f"    Overall accuracy: "
          f"{correct/len(y_true):.2%} ({correct}/{len(y_true)})")

    # ── Step 2: Accuracy vs SNR sweep ──
    print("\n[2] Sweeping SNR from -5 dB to 30 dB "
          "(50 trials per point per class)")
    snr_values, accuracy_by_tx = collect_accuracy_curves(
        n_per_point=50, snr_range=(-5, 30, 5)
    )
    print(f"    SNR points evaluated: {len(snr_values)}")

    # ── Step 3: Re-run attack scenarios for summary ──
    print("\n[3] Re-running attack scenarios for summary plot")
    print("    (jamming, replay, rogue — 100 trials each)")
    jam_results = simulate_jamming_attack(
        transmitter="sbi_tower_profile",
        base_snr=20, n_trials=100
    )
    replay_results = simulate_replay_attack(
        claimed_sender="sbi_tower_profile",
        replay_snr=20, n_trials=100
    )
    rogue_result = simulate_rogue_spoofing(
        claimed_sender="sbi_tower_profile",
        snr=20, n_trials=100
    )
    print("    All attack simulations complete")

    # ── Step 4: Generate the four plots ──
    print("\n[4] Generating publication-quality plots")
    cm, cm_pct = plot_confusion_matrix(
        y_true, y_pred, snr_db=20,
        save_path=os.path.join(RESULTS_DIR, "confusion_matrix.png")
    )
    plot_accuracy_vs_snr(
        snr_values, accuracy_by_tx,
        save_path=os.path.join(RESULTS_DIR, "accuracy_vs_snr.png")
    )
    plot_distance_distributions(
        y_true, distances,
        save_path=os.path.join(RESULTS_DIR,
                               "distance_distributions.png")
    )
    plot_attack_summary(
        jam_results, replay_results, rogue_result,
        save_path=os.path.join(RESULTS_DIR, "attack_summary.png")
    )

    # ── Step 5: Export CSV ──
    print("\n[5] Exporting numerical results to CSV")
    export_results_csv(
        snr_values, accuracy_by_tx, cm,
        jam_results, replay_results, rogue_result,
        save_path=os.path.join(RESULTS_DIR, "evaluation_results.csv")
    )

    # ── Step 6: Final summary ──
    print("\n[6] Final Performance Summary")
    print(f"    {'Metric':<45} | {'Value':>15}")
    print(f"    {'-'*45}-+-{'-'*15}")
    print(f"    {'Overall classification accuracy (20 dB)':<45} | "
          f"{correct/len(y_true):>14.2%}")
    print(f"    {'Accuracy at 25 dB (SBI tower)':<45} | "
          f"{accuracy_by_tx['sbi_tower_profile'][snr_values.index(25)]:>14.2%}")
    print(f"    {'Accuracy at 10 dB (SBI tower)':<45} | "
          f"{accuracy_by_tx['sbi_tower_profile'][snr_values.index(10)]:>14.2%}")
    print(f"    {'Rogue detection rate (20 dB)':<45} | "
          f"{rogue_result['detection_rate']:>14.2%}")
    print(f"    {'Replay (high-perturb combined detection)':<45} | "
          f"{replay_results[-1]['total_detection']:>14.2%}")

    print("\nEvaluation complete — all artifacts saved to:")
    print(f"  {os.path.abspath(RESULTS_DIR)}")
    print("=" * 70)