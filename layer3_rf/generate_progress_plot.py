"""
Quick plot generator for progress report.
Produces a BER vs SNR curve showing the simulation is physically realistic.
"""

import numpy as np
import matplotlib.pyplot as plt
from ofdm_simulator import run_end_to_end

# SNR range to sweep
snr_values = [-5, 0, 5, 10, 15, 20, 25, 30]

# Collect BER for each transmitter across all SNRs
transmitters = ["sbi_tower_profile", "hdfc_tower_profile", "rogue_transmitter"]
colors = ["tab:blue", "tab:orange", "tab:red"]
labels = ["SBI tower", "HDFC tower", "Rogue transmitter"]

plt.figure(figsize=(8, 5))

for tx, color, label in zip(transmitters, colors, labels):
    bers = []
    for snr in snr_values:
        # Average over 3 runs to smooth out noise variation
        runs = [run_end_to_end(tx, snr_db=snr, n_symbols=50, seed=s)["ber"]
                for s in [42, 43, 44]]
        bers.append(np.mean(runs))
    plt.semilogy(snr_values, bers, "o-", color=color, label=label, linewidth=2)

plt.xlabel("SNR (dB)", fontsize=12)
plt.ylabel("Bit Error Rate (BER)", fontsize=12)
plt.title("RF Fingerprinting — OFDM BER vs SNR across transmitter profiles",
          fontsize=13, fontweight="bold")
plt.grid(True, which="both", alpha=0.3)
plt.legend(fontsize=11)
plt.tight_layout()
plt.savefig("ber_vs_snr_progress.png", dpi=150)
plt.show()
print("Saved: ber_vs_snr_progress.png")