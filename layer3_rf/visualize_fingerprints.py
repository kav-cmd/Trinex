"""
TRINEX — fingerprint visualization
Generates three plots showing the fingerprinting layer at work.
"""

import numpy as np
import matplotlib.pyplot as plt
from fingerprinter import fingerprint_from_signal
from transmitter_profiles import load_profile

plt.rcParams.update({"font.size": 11, "figure.dpi": 120})

TRANSMITTERS = ["sbi_tower_profile", "hdfc_tower_profile", "rogue_transmitter"]
LABELS = ["SBI Tower", "HDFC Tower", "Rogue Transmitter"]
COLORS = ["#1f77b4", "#ff7f0e", "#d62728"]


# ── Plot 1: Original 16-tap profiles vs recovered 8-tap CIRs ──
fig, axes = plt.subplots(2, 3, figsize=(13, 6.5))
fig.suptitle("Transmitter Profiles — Original vs Recovered from Noisy Signal",
             fontsize=14, fontweight="bold", y=1.00)

for col, (tx, label, color) in enumerate(zip(TRANSMITTERS, LABELS, COLORS)):
    # Top row: original 16-tap CIR
    original = load_profile(tx)
    axes[0, col].stem(np.abs(original), linefmt=color, markerfmt="o", basefmt=" ")
    axes[0, col].set_title(f"{label}\n(Original 16-tap profile)", fontsize=11)
    axes[0, col].set_xlabel("Tap index (delay)")
    axes[0, col].set_ylabel("|h|")
    axes[0, col].set_ylim(0, 1.0)
    axes[0, col].grid(True, alpha=0.3)

    # Bottom row: recovered 8-point CIR at SNR=20 dB
    fp = fingerprint_from_signal(tx, snr_db=20, n_symbols=1, seed=42)
    recovered = np.abs(fp["cir"][0])
    axes[1, col].stem(recovered, linefmt=color, markerfmt="o", basefmt=" ")
    axes[1, col].set_title(f"Recovered 8-point CIR at SNR=20 dB", fontsize=11)
    axes[1, col].set_xlabel("Effective tap index")
    axes[1, col].set_ylabel("|h|")
    axes[1, col].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("docs/images/fingerprint_profiles.png", dpi=150, bbox_inches="tight")
print("Saved: docs/images/fingerprint_profiles.png")


# ── Plot 2: Feature vector overlay — the 'fingerprint' view ──
fig, ax = plt.subplots(figsize=(11, 5.5))

# Average 30 samples per transmitter for smooth profiles
for tx, label, color in zip(TRANSMITTERS, LABELS, COLORS):
    feats = []
    for s in range(30):
        fp = fingerprint_from_signal(tx, snr_db=20, n_symbols=1, seed=s)
        feats.append(fp["features"][0])
    mean_feat = np.mean(feats, axis=0)
    std_feat = np.std(feats, axis=0)

    x = np.arange(len(mean_feat))
    ax.plot(x, mean_feat, "o-", color=color, label=label, linewidth=2, markersize=7)
    ax.fill_between(x, mean_feat - std_feat, mean_feat + std_feat,
                     color=color, alpha=0.15)

# Annotate feature groups
ax.axvspan(-0.5, 7.5, alpha=0.05, color="blue")
ax.axvspan(7.5, 11.5, alpha=0.05, color="green")
ax.text(3.5, ax.get_ylim()[1]*0.92, "Magnitude profile (bins 0–7)",
        ha="center", fontsize=10, style="italic")
ax.text(9.5, ax.get_ylim()[1]*0.92, "Summary statistics",
        ha="center", fontsize=10, style="italic")

ax.set_xlabel("Feature index", fontsize=11)
ax.set_ylabel("Feature value", fontsize=11)
ax.set_title("Transmitter Fingerprints — 12-Dimensional Feature Vectors at SNR=20 dB\n"
             "(Shaded bands show ±1 std over 30 noisy samples)",
             fontsize=12, fontweight="bold")
ax.legend(loc="upper right", fontsize=10)
ax.grid(True, alpha=0.3)
ax.set_xticks(x)
feat_labels = [f"bin{i}" for i in range(8)] + ["peak", "pwr", "spr", "Nsig"]
ax.set_xticklabels(feat_labels, rotation=45, fontsize=9)

plt.tight_layout()
plt.savefig("docs/images/fingerprint_features.png", dpi=150, bbox_inches="tight")
print("Saved: docs/images/fingerprint_features.png")


# ── Plot 3: Pairwise distance matrix (heatmap) ──────────────
mean_features = {}
for tx in TRANSMITTERS:
    feats = []
    for s in range(30):
        fp = fingerprint_from_signal(tx, snr_db=20, n_symbols=1, seed=s)
        feats.append(fp["features"][0])
    mean_features[tx] = np.mean(feats, axis=0)

dist_matrix = np.zeros((3, 3))
for i, a in enumerate(TRANSMITTERS):
    for j, b in enumerate(TRANSMITTERS):
        dist_matrix[i, j] = np.linalg.norm(mean_features[a] - mean_features[b])

fig, ax = plt.subplots(figsize=(6.5, 5.5))
im = ax.imshow(dist_matrix, cmap="YlOrRd", vmin=0)
ax.set_xticks(range(3))
ax.set_yticks(range(3))
ax.set_xticklabels(LABELS, rotation=30, ha="right")
ax.set_yticklabels(LABELS)

for i in range(3):
    for j in range(3):
        color = "white" if dist_matrix[i, j] > dist_matrix.max() * 0.5 else "black"
        ax.text(j, i, f"{dist_matrix[i, j]:.2f}",
                ha="center", va="center", color=color, fontsize=13, fontweight="bold")

ax.set_title("Pairwise Fingerprint Distance Matrix\n(Euclidean distance, SNR=20 dB)",
             fontsize=12, fontweight="bold")
plt.colorbar(im, ax=ax, label="Distance")
plt.tight_layout()
plt.savefig("docs/images/fingerprint_distance_matrix.png", dpi=150, bbox_inches="tight")
print("Saved: docs/images/fingerprint_distance_matrix.png")

print("\nAll three plots generated. Check the layer3_rf folder for PNGs.")
plt.show()