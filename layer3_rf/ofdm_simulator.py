"""
TRINEX — Layer 3: RF Fingerprinting
File: ofdm_simulator.py
"""

import numpy as np
from transmitter_profiles import load_profile


# ── OFDM System Parameters ────────────────────────────────────
N_SUBCARRIERS = 64
N_PILOTS = 8
N_DATA = N_SUBCARRIERS - N_PILOTS
CP_LENGTH = 16           # must be >= CIR effective length

PILOT_INDICES = np.arange(0, N_SUBCARRIERS, N_SUBCARRIERS // N_PILOTS)
DATA_INDICES = np.array([i for i in range(N_SUBCARRIERS) if i not in PILOT_INDICES])
PILOT_VALUE = 1 + 0j


# ══════════════════════════════════════════════════════════════
# TRANSMITTER
# ══════════════════════════════════════════════════════════════

def bits_to_qpsk(bits):
    bits = np.array(bits).reshape(-1, 2)
    I = 1 - 2 * bits[:, 0]
    Q = 1 - 2 * bits[:, 1]
    return (I + 1j * Q) / np.sqrt(2)


def qpsk_to_bits(symbols):
    bit0 = (np.real(symbols) < 0).astype(int)
    bit1 = (np.imag(symbols) < 0).astype(int)
    return np.column_stack([bit0, bit1]).flatten()


def map_to_subcarriers(data_symbols):
    ofdm_symbol = np.zeros(N_SUBCARRIERS, dtype=complex)
    ofdm_symbol[DATA_INDICES] = data_symbols
    ofdm_symbol[PILOT_INDICES] = PILOT_VALUE
    return ofdm_symbol


def apply_ifft(ofdm_symbol):
    return np.fft.ifft(ofdm_symbol) * np.sqrt(N_SUBCARRIERS)


def add_cyclic_prefix(time_signal):
    return np.concatenate([time_signal[-CP_LENGTH:], time_signal])


def ofdm_transmit(n_symbols=1, seed=None):
    rng = np.random.default_rng(seed)
    all_blocks, all_bits = [], []
    for _ in range(n_symbols):
        bits = rng.integers(0, 2, size=N_DATA * 2)
        all_bits.append(bits)
        qpsk = bits_to_qpsk(bits)
        freq_symbol = map_to_subcarriers(qpsk)
        time_symbol = apply_ifft(freq_symbol)
        all_blocks.append(add_cyclic_prefix(time_symbol))
    return np.concatenate(all_blocks), np.concatenate(all_bits)


# ══════════════════════════════════════════════════════════════
# CHANNEL
# ══════════════════════════════════════════════════════════════

def apply_channel(tx_signal, cir, snr_db, rng=None,
                  channel_drift=0.0):
    """
    Apply multipath channel + AWGN to the OFDM signal.

    The `channel_drift` parameter controls realistic channel
    variability. Set to 0.0 for ideal training conditions,
    or 0.15+ to model real-world channel time-variation.

    Real-world drift sources: moving vehicles, antenna
    micro-movements, atmospheric changes, foliage motion.
    """
    if rng is None:
        rng = np.random.default_rng()

    # Channel variability — perturb each tap if drift > 0
    if channel_drift > 0:
        tap_drift = channel_drift * np.abs(cir) * (
            rng.standard_normal(len(cir)) +
            1j * rng.standard_normal(len(cir))
        )
        perturbed_cir = cir + tap_drift
        total_power = np.sum(np.abs(perturbed_cir) ** 2)
        if total_power > 1e-12:
            perturbed_cir = perturbed_cir / np.sqrt(total_power)
        else:
            perturbed_cir = cir
    else:
        perturbed_cir = cir

    # Linear convolution
    full = np.convolve(tx_signal, perturbed_cir, mode="full")
    faded = full[: len(tx_signal)]

    # AWGN
    signal_power = np.mean(np.abs(faded) ** 2)
    noise_power = signal_power / (10 ** (snr_db / 10))
    noise = np.sqrt(noise_power / 2) * (
        rng.standard_normal(len(faded)) + 1j * rng.standard_normal(len(faded))
    )
    return faded + noise

# ══════════════════════════════════════════════════════════════
# RECEIVER
# ══════════════════════════════════════════════════════════════

def remove_cyclic_prefix(rx_signal):
    symbol_len = N_SUBCARRIERS + CP_LENGTH
    n_symbols = len(rx_signal) // symbol_len
    return [
        rx_signal[i * symbol_len + CP_LENGTH : i * symbol_len + symbol_len]
        for i in range(n_symbols)
    ]


def apply_fft(time_symbol):
    return np.fft.fft(time_symbol) / np.sqrt(N_SUBCARRIERS)


def estimate_channel(received_freq):
    """
    LS channel estimation at pilot subcarriers, then interpolate
    across all 64 subcarriers in the complex domain directly.
    """
    received_pilots = received_freq[PILOT_INDICES]
    H_at_pilots = received_pilots / PILOT_VALUE

    # Interpolate real and imaginary parts separately across all subcarriers
    all_indices = np.arange(N_SUBCARRIERS)
    H_real = np.interp(all_indices, PILOT_INDICES, H_at_pilots.real)
    H_imag = np.interp(all_indices, PILOT_INDICES, H_at_pilots.imag)
    H_full = H_real + 1j * H_imag
    return H_full, received_pilots


def equalize(received_freq, H_full):
    """Zero-forcing: X_hat = Y / H"""
    # Avoid division by zero at deep fades
    H_safe = np.where(np.abs(H_full) < 1e-10, 1e-10, H_full)
    return received_freq / H_safe


def ofdm_receive(rx_signal, true_cir=None):
    """
    RX chain. If true_cir is provided, use the exact channel for
    equalization (clean data recovery). The LS pilot estimate is
    still computed and returned — it's what the fingerprinter uses.
    """
    time_symbols = remove_cyclic_prefix(rx_signal)
    all_bits, all_pilots, all_H_ls = [], [], []

    # Compute the true frequency response from the known CIR
    if true_cir is not None:
        # Zero-pad CIR to N_SUBCARRIERS then FFT
        cir_padded = np.zeros(N_SUBCARRIERS, dtype=complex)
        cir_padded[: len(true_cir)] = true_cir
        H_true = np.fft.fft(cir_padded)
    else:
        H_true = None

    for ts in time_symbols:
        freq = apply_fft(ts)

        # LS estimate at pilots (this is the fingerprint source)
        H_ls, rx_pilots = estimate_channel(freq)
        all_pilots.append(rx_pilots)
        all_H_ls.append(H_ls)

        # Equalize using true channel if available, else LS estimate
        H_for_eq = H_true if H_true is not None else H_ls
        equalized = equalize(freq, H_for_eq)

        # QPSK demod on data subcarriers — but we need to account for
        # the sqrt(N) scaling introduced by IFFT+FFT round trip
        data = equalized[DATA_INDICES]
        all_bits.append(qpsk_to_bits(data))

    return np.concatenate(all_bits), np.array(all_pilots), np.array(all_H_ls)


# ══════════════════════════════════════════════════════════════
# END-TO-END
# ══════════════════════════════════════════════════════════════
def run_end_to_end(transmitter_name, snr_db, n_symbols=5,
                   seed=42, channel_drift=0.0):
    """End-to-end OFDM pipeline test with optional channel drift."""
    rng = np.random.default_rng(seed)
    cir = load_profile(transmitter_name)
    tx_signal, tx_bits = ofdm_transmit(n_symbols=n_symbols, seed=seed)
    rx_signal = apply_channel(tx_signal, cir, snr_db, rng=rng,
                              channel_drift=channel_drift)
    rx_bits, rx_pilots, H_est = ofdm_receive(rx_signal, true_cir=cir)

    min_len = min(len(tx_bits), len(rx_bits))
    n_errors = np.sum(tx_bits[:min_len] != rx_bits[:min_len])
    return {
        "transmitter": transmitter_name,
        "snr_db": snr_db,
        "n_bits": min_len,
        "n_errors": int(n_errors),
        "ber": n_errors / min_len,
        "rx_pilots": rx_pilots,
        "H_est": H_est,
    }


# ══════════════════════════════════════════════════════════════
# TEST
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("TRINEX — Full OFDM Chain (Day 3 — corrected)")
    print("=" * 60)

    print("\n[0] Sanity: no channel, no noise (ideal loopback)")
    tx_signal, tx_bits = ofdm_transmit(n_symbols=5, seed=42)
    # "ideal" channel = just a single unit tap, no convolution distortion
    ideal_cir = np.array([1.0 + 0j])
    rx_signal = apply_channel(tx_signal, ideal_cir, snr_db=100,
                              rng=np.random.default_rng(0))
    rx_bits, _, _ = ofdm_receive(rx_signal)
    min_len = min(len(tx_bits), len(rx_bits))
    err = np.sum(tx_bits[:min_len] != rx_bits[:min_len])
    print(f"    Ideal loopback BER: {err/min_len:.6f}  (must be 0.000000)")

    print("\n[1] SBI tower across SNR sweep:")
    print(f"    {'SNR (dB)':>10} | {'BER':>10} | {'Errors/Bits':>15}")
    print(f"    {'-'*10}-+-{'-'*10}-+-{'-'*15}")
    for snr in [30, 20, 15, 10, 5, 0, -5]:
        r = run_end_to_end("sbi_tower_profile", snr_db=snr, n_symbols=50, seed=42)
        print(f"    {snr:>10} | {r['ber']:>10.4f} | {r['n_errors']:>6}/{r['n_bits']:<6}")

    print("\n[2] All three transmitters at SNR=25 dB")
    for name in ["sbi_tower_profile", "hdfc_tower_profile", "rogue_transmitter"]:
        r = run_end_to_end(name, snr_db=25, n_symbols=50, seed=42)
        print(f"    {name:22s} → BER = {r['ber']:.4f}")

    print("\n[3] Pilot handoff for Day 4:")
    r = run_end_to_end("sbi_tower_profile", snr_db=20, n_symbols=1, seed=42)
    print(f"    rx_pilots shape: {r['rx_pilots'].shape}")
    print(f"    H_est shape:     {r['H_est'].shape}")

    print("\n[4] Done.")
    print("=" * 60)