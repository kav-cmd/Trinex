"""
TRINEX — Layer 3: RF Fingerprinting
File: attack_injector.py

Purpose:
Simulate three physical-layer attack scenarios against the RF
fingerprinting system and measure detection performance under each.

Attacks simulated:
    1. Broadband jamming       — high-power noise corrupts pilots
    2. Replay attack           — legitimate signal retransmitted
    3. Rogue transmitter spoof — fake tower mimics a registered bank
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os
from ofdm_simulator import (
    ofdm_transmit, apply_channel, ofdm_receive,
    N_SUBCARRIERS, CP_LENGTH, PILOT_INDICES, PILOT_VALUE
)
from fingerprinter import (
    extract_cir_from_pilots, extract_features,
    _get_or_train_classifier, classify_fingerprint,
    ROGUE_DISTANCE_THRESHOLD
)
from transmitter_profiles import load_profile

RESULTS_DIR = os.path.join(os.path.dirname(__file__),
                           "..", "results", "rf_results")
os.makedirs(RESULTS_DIR, exist_ok=True)

REGISTERED = ["sbi_tower_profile", "hdfc_tower_profile"]
LABELS = {
    "sbi_tower_profile":  "SBI Tower",
    "hdfc_tower_profile": "HDFC Tower",
    "rogue_transmitter":  "Rogue Transmitter"
}


# ══════════════════════════════════════════════════════════════
# ATTACK 1 — BROADBAND JAMMING
# ══════════════════════════════════════════════════════════════

def apply_jamming(rx_signal, jam_power_db):
    """
    Add broadband Gaussian interference to the received signal.
    High jam_power_db overwhelms the pilot subcarriers, making
    CIR estimation unreliable.
    """
    jam_power = 10 ** (jam_power_db / 10)
    jammer = np.sqrt(jam_power / 2) * (
        np.random.randn(len(rx_signal)) +
        1j * np.random.randn(len(rx_signal))
    )
    return rx_signal + jammer


def simulate_jamming_attack(transmitter="sbi_tower_profile",
                            base_snr=20, n_trials=100):
    """Test fingerprint accuracy as jamming power increases."""
    clf = _get_or_train_classifier()
    cir = load_profile(transmitter)
    jam_levels = [-10, -5, 0, 5, 10, 15, 20]
    results = []

    for jam_db in jam_levels:
        correct = 0
        flagged_unknown = 0

        for seed in range(n_trials):
            rng = np.random.default_rng(seed + 8000)
            tx_signal, _ = ofdm_transmit(n_symbols=1, seed=seed)
            rx_signal = apply_channel(tx_signal, cir, base_snr, rng=rng,
                          channel_drift=0.15)
            rx_jammed = apply_jamming(rx_signal, jam_db)
            _, rx_pilots, _ = ofdm_receive(rx_jammed, true_cir=cir)
            features = extract_features(
                extract_cir_from_pilots(rx_pilots))[0]
            result = classify_fingerprint(clf, features)

            if result["predicted_label"] == transmitter:
                correct += 1
            elif result["predicted_label"] == "unknown_transmitter":
                flagged_unknown += 1

        results.append({
            "jam_db": jam_db,
            "accuracy": correct / n_trials,
            "flagged_unknown": flagged_unknown / n_trials,
            "misclassified": (n_trials - correct - flagged_unknown) / n_trials
        })

    return results


# ══════════════════════════════════════════════════════════════
# ATTACK 2 — REPLAY ATTACK
# ══════════════════════════════════════════════════════════════

def simulate_replay_attack(claimed_sender="sbi_tower_profile",
                           replay_snr=20, n_trials=100):
    """
    Simulate a replay attack with two detection mechanisms:
    1. CIR fingerprint matching (physical layer)
    2. Timestamp freshness check (protocol layer)
    """
    clf = _get_or_train_classifier()
    original_cir = load_profile(claimed_sender)
    perturbation_levels = [0.0, 0.05, 0.10, 0.20, 0.30, 0.50]
    results = []

    for perturb in perturbation_levels:
        cir_detected  = 0
        ts_detected   = 0
        both_detected = 0
        accepted      = 0

        for seed in range(n_trials):
            rng = np.random.default_rng(seed + 9000)

            noise_tap = perturb * (
                rng.standard_normal(len(original_cir)) +
                1j * rng.standard_normal(len(original_cir))
            )
            replay_cir = original_cir + noise_tap
            replay_cir = replay_cir / np.sqrt(
                np.sum(np.abs(replay_cir) ** 2))

            tx_signal, _ = ofdm_transmit(n_symbols=1, seed=seed)
            rx_signal = apply_channel(tx_signal, replay_cir,
                          replay_snr, rng=rng,
                          channel_drift=0.20)
            _, rx_pilots, _ = ofdm_receive(rx_signal,
                                           true_cir=replay_cir)
            features = extract_features(
                extract_cir_from_pilots(rx_pilots))[0]
            result = classify_fingerprint(clf, features)

            cir_caught = (result["predicted_label"] != claimed_sender)
            ts_catch_prob = min(perturb * 2.5, 1.0)
            ts_caught = rng.random() < ts_catch_prob

            if cir_caught and ts_caught:
                both_detected += 1
            elif cir_caught:
                cir_detected += 1
            elif ts_caught:
                ts_detected += 1
            else:
                accepted += 1

        total_detected = cir_detected + ts_detected + both_detected
        results.append({
            "perturbation":   perturb,
            "cir_detection":  cir_detected / n_trials,
            "ts_detection":   ts_detected / n_trials,
            "both_detection": both_detected / n_trials,
            "total_detection": total_detected / n_trials,
            "acceptance_rate": accepted / n_trials,
        })

    return results


# ══════════════════════════════════════════════════════════════
# ATTACK 3 — ROGUE TRANSMITTER SPOOFING
# ══════════════════════════════════════════════════════════════

def simulate_rogue_spoofing(claimed_sender="sbi_tower_profile",
                            snr=20, n_trials=100):
    """
    Rogue transmitter sends signals claiming to be a registered bank.
    Tests whether the classifier correctly flags these as unknown.
    """
    clf = _get_or_train_classifier()
    rogue_cir = load_profile("rogue_transmitter")
    flagged = 0
    accepted = 0

    for seed in range(n_trials):
        rng = np.random.default_rng(seed + 7000)
        tx_signal, _ = ofdm_transmit(n_symbols=1, seed=seed)
        rx_signal = apply_channel(tx_signal, rogue_cir, snr, rng=rng,
                          channel_drift=0.20)
        _, rx_pilots, _ = ofdm_receive(rx_signal, true_cir=rogue_cir)
        features = extract_features(
            extract_cir_from_pilots(rx_pilots))[0]
        result = classify_fingerprint(clf, features)

        if result["predicted_label"] == "unknown_transmitter":
            flagged += 1
        else:
            accepted += 1

    return {
        "n_trials": n_trials,
        "flagged": flagged,
        "accepted": accepted,
        "detection_rate": flagged / n_trials,
        "false_acceptance_rate": accepted / n_trials,
    }


# ══════════════════════════════════════════════════════════════
# RESULT PLOTS
# ══════════════════════════════════════════════════════════════

def plot_attack_results(jam_results, replay_results, rogue_result):
    """Generate attack robustness figure with three subplots."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle(
        "RF Fingerprinting — Attack Robustness Analysis",
        fontsize=14, fontweight="bold"
    )

    # ── Plot 1: Jamming ──
    jam_dbs = [r["jam_db"] for r in jam_results]
    acc = [r["accuracy"] * 100 for r in jam_results]
    unk = [r["flagged_unknown"] * 100 for r in jam_results]
    mis = [r["misclassified"] * 100 for r in jam_results]

    axes[0].plot(jam_dbs, acc, "o-",  color="#1f77b4",
                 label="Correct ID", linewidth=2)
    axes[0].plot(jam_dbs, unk, "s--", color="#ff7f0e",
                 label="Flagged unknown", linewidth=2)
    axes[0].plot(jam_dbs, mis, "^:",  color="#d62728",
                 label="Misclassified", linewidth=2)
    axes[0].set_xlabel("Jammer power (dB)", fontsize=11)
    axes[0].set_ylabel("Rate (%)", fontsize=11)
    axes[0].set_title("Attack 1: Broadband Jamming",
                      fontsize=12, fontweight="bold")
    axes[0].legend(fontsize=9)
    axes[0].grid(True, alpha=0.3)
    axes[0].set_ylim(-5, 105)

    # ── Plot 2: Replay ──
    perturbs = [r["perturbation"] for r in replay_results]
    cir_det  = [(r["cir_detection"] + r["both_detection"]) * 100
                for r in replay_results]
    comb_det = [r["total_detection"] * 100 for r in replay_results]
    acc_rate = [r["acceptance_rate"] * 100 for r in replay_results]

    axes[1].plot(perturbs, cir_det,  "o--", color="#1f77b4",
                 label="CIR detection only", linewidth=2)
    axes[1].plot(perturbs, comb_det, "o-",  color="#2ca02c",
                 label="CIR + Timestamp", linewidth=2)
    axes[1].plot(perturbs, acc_rate, "s:",  color="#d62728",
                 label="Accepted (false)", linewidth=2)
    axes[1].set_xlabel("Channel perturbation", fontsize=11)
    axes[1].set_ylabel("Rate (%)", fontsize=11)
    axes[1].set_title("Attack 2: Replay Attack",
                      fontsize=12, fontweight="bold")
    axes[1].legend(fontsize=9)
    axes[1].grid(True, alpha=0.3)
    axes[1].set_ylim(-5, 105)

    # ── Plot 3: Rogue spoofing ──
    categories = ["Flagged\n(correct)", "Accepted\n(false)"]
    values = [
        rogue_result["detection_rate"] * 100,
        rogue_result["false_acceptance_rate"] * 100
    ]
    colors = ["#2ca02c", "#d62728"]
    bars = axes[2].bar(categories, values, color=colors,
                       width=0.4, edgecolor="white", linewidth=1.5)
    for bar, val in zip(bars, values):
        axes[2].text(bar.get_x() + bar.get_width() / 2,
                     bar.get_height() + 2,
                     f"{val:.1f}%", ha="center",
                     fontsize=12, fontweight="bold")
    axes[2].set_ylabel("Rate (%)", fontsize=11)
    axes[2].set_title("Attack 3: Rogue Transmitter Spoofing",
                      fontsize=12, fontweight="bold")
    axes[2].set_ylim(0, 115)
    axes[2].grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    out_path = os.path.join(RESULTS_DIR, "attack_robustness.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.savefig("attack_robustness.png", dpi=150, bbox_inches="tight")
    print(f"\n  Plot saved: attack_robustness.png")
    plt.close()


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 65)
    print("TRINEX — RF Fingerprinting Attack Robustness Analysis")
    print("=" * 65)

    # ── Attack 1: Jamming ──────────────────────────────────────
    print("\n[1] Broadband Jamming Attack (SBI tower, SNR=20 dB base)")
    print("    Testing as jammer power increases from -10 dB to +20 dB")
    print(f"    {'Jam (dB)':>10} | {'Correct ID':>12} | "
          f"{'Flagged unknown':>16} | {'Misclassified':>14}")
    print(f"    {'-'*10}-+-{'-'*12}-+-{'-'*16}-+-{'-'*14}")

    jam_results = simulate_jamming_attack(
        transmitter="sbi_tower_profile",
        base_snr=20, n_trials=100
    )
    for r in jam_results:
        print(f"    {r['jam_db']:>10} | {r['accuracy']:>12.2%} | "
              f"{r['flagged_unknown']:>16.2%} | "
              f"{r['misclassified']:>14.2%}")

    # ── Attack 2: Replay ──────────────────────────────────────
    print("\n[2] Replay Attack (claiming SBI, SNR=20 dB)")
    print("    CIR-only vs Combined (CIR + timestamp) detection")
    print(f"    {'Perturbation':>14} | {'CIR only':>10} | "
          f"{'Combined':>10} | {'Accepted':>10}")
    print(f"    {'-'*14}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}")

    replay_results = simulate_replay_attack(
        claimed_sender="sbi_tower_profile",
        replay_snr=20, n_trials=100
    )
    for r in replay_results:
        print(f"    {r['perturbation']:>14.2f} | "
              f"{r['cir_detection']+r['both_detection']:>10.2%} | "
              f"{r['total_detection']:>10.2%} | "
              f"{r['acceptance_rate']:>10.2%}")

    # ── Attack 3: Rogue Spoofing ──────────────────────────────
    print("\n[3] Rogue Transmitter Spoofing (claiming SBI, SNR=20 dB)")
    rogue_result = simulate_rogue_spoofing(
        claimed_sender="sbi_tower_profile",
        snr=20, n_trials=100
    )
    print(f"    Trials run          : {rogue_result['n_trials']}")
    print(f"    Correctly flagged   : {rogue_result['flagged']} "
          f"({rogue_result['detection_rate']:.2%})")
    print(f"    Falsely accepted    : {rogue_result['accepted']} "
          f"({rogue_result['false_acceptance_rate']:.2%})")

    # ── Summary ───────────────────────────────────────────────
    print("\n[4] Attack Robustness Summary")
    print(f"    {'Attack Type':<30} | {'System Response':<40}")
    print(f"    {'-'*30}-+-{'-'*40}")

    jam_high = jam_results[-1]
    print(f"    {'Broadband jamming (20 dB)':<30} | "
          f"Correct ID drops to {jam_high['accuracy']:.0%}, "
          f"{jam_high['flagged_unknown']:.0%} flagged unknown")

    replay_zero = replay_results[0]
    replay_high = replay_results[-1]
    print(f"    {'Replay (perfect copy)':<30} | "
          f"Combined detection: {replay_zero['total_detection']:.0%}")
    print(f"    {'Replay (0.5 perturbation)':<30} | "
          f"Combined detection: {replay_high['total_detection']:.0%}")
    print(f"    {'Rogue transmitter spoof':<30} | "
          f"Detection rate: {rogue_result['detection_rate']:.0%}")

    # ── Plot ──────────────────────────────────────────────────
    print("\n[5] Generating attack robustness plot...")
    plot_attack_results(jam_results, replay_results, rogue_result)

    print("\nAnalysis complete.")
    print("=" * 65)