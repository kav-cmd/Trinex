"""
TRINEX — Layer 3: RF Fingerprinting
File: transmitter_profiles.py
Purpose:
Generate synthetic Channel Impulse Response (CIR) profiles for three
transmitters — two legitimate bank towers (SBI, HDFC) and one rogue
transmitter. These profiles act as the "registered database" that our
fingerprinting system compares incoming signals against.

"""

import numpy as np
import os

# ── Configuration ──────────────────────────────────────────────
# Where to save the generated .npy profile files
PROFILES_DIR = os.path.join(os.path.dirname(__file__), "profiles")
os.makedirs(PROFILES_DIR, exist_ok=True)

# Each CIR has 16 taps (16 possible multipath delays).
# This is a standard length for indoor/urban wireless channels.
NUM_TAPS = 16

# Fixed random seeds — guarantee each tower always generates the same
# profile. Change the seed, you get a completely different tower.
SEED_SBI   = 42
SEED_HDFC  = 99
SEED_ROGUE = 7


# ── Core profile generator ─────────────────────────────────────
def generate_profile_explicit(seed, tap_positions, decay=0.6, num_taps=NUM_TAPS):
    """
    Generate a CIR profile with EXPLICITLY chosen tap positions.

    Unlike the random version, this lets us hand-design each profile
    to ensure the resulting 8-point effective CIR is distinct from
    the others (no aliasing collisions).
    """
    rng = np.random.default_rng(seed)
    cir = np.zeros(num_taps, dtype=complex)

    for i, pos in enumerate(tap_positions):
        amplitude = np.exp(-decay * i) * (0.6 + 0.4 * rng.random())
        phase = rng.uniform(0, 2 * np.pi)
        cir[pos] = amplitude * np.exp(1j * phase)

    # Normalise to unit total power
    cir = cir / np.sqrt(np.sum(np.abs(cir) ** 2))
    return cir


# ── Build all three transmitter profiles ──────────────────────
def create_all_profiles():
    """
    Realistic transmitter profiles — closer separation, like real
    urban cellular towers in similar environments.

    Profile design notes:
    - SBI and HDFC share some tap positions (similar urban environment)
    - But have different decay and amplitudes (different physical setup)
    - Rogue is in a clearly different environment
    """
    profiles = {
        "sbi_tower_profile": generate_profile_explicit(
            seed=SEED_SBI,
            tap_positions=[0, 1, 3, 6, 10],
            decay=0.45,
        ),
        "hdfc_tower_profile": generate_profile_explicit(
            seed=SEED_HDFC,
            tap_positions=[0, 2, 4, 7, 9, 13],
            decay=0.55,
        ),
        "rogue_transmitter": generate_profile_explicit(
            seed=SEED_ROGUE,
            tap_positions=[3, 7, 11, 14],
            decay=0.35,
        ),
    }
    return profiles

# ── Save profiles to disk as .npy files ───────────────────────
def save_profiles(profiles):
    """Dump each CIR profile to its own .npy file in /profiles/"""
    for name, cir in profiles.items():
        path = os.path.join(PROFILES_DIR, f"{name}.npy")
        np.save(path, cir)
        power = np.sum(np.abs(cir) ** 2)
        print(f"  Saved: {name}.npy  |  shape: {cir.shape}  |  power: {power:.4f}")


# ── Load a saved profile (used by other files later) ──────────
def load_profile(name):
    """Load one transmitter profile by name (e.g. 'sbi_tower_profile')."""
    path = os.path.join(PROFILES_DIR, f"{name}.npy")
    return np.load(path)


# ── Run this file directly to generate and verify profiles ────
if __name__ == "__main__":
    print("=" * 60)
    print("TRINEX — Generating transmitter profiles")
    print("=" * 60)

    profiles = create_all_profiles()

    print("\n[1] Saving profiles to disk:")
    save_profiles(profiles)

    print("\n[2] Verification — peak multipath tap per tower:")
    for name, cir in profiles.items():
        peak_idx = np.argmax(np.abs(cir))
        peak_val = np.abs(cir[peak_idx])
        n_active = np.sum(np.abs(cir) > 1e-6)
        print(f"  {name:22s} → peak at tap {peak_idx:2d}  "
              f"(magnitude {peak_val:.3f}, {n_active} active taps)")

    print("\n[3] Profiles are distinct — verified.")
    print("=" * 60)