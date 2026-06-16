"""
TRINEX — Integration Test
File: test_integration.py (place in TRINEX root, NOT in layer3_rf)

Verifies that the RF layer public API works correctly when called
from outside the layer3_rf directory, exactly as CS teammates will.
"""

import sys
import os

# Add layer3_rf to path so it can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "layer3_rf"))

from fingerprinter import get_rf_score, get_rf_score_from_signal
from ofdm_simulator import run_end_to_end

print("=" * 60)
print("TRINEX — RF Layer Integration Test")
print("=" * 60)

print("\n[1] Testing scenario-based API (get_rf_score)")
scenarios = [
    ("sbi_tower_profile",  20, "legitimate",    "SBI legitimate (20 dB)"),
    ("hdfc_tower_profile", 20, "legitimate",    "HDFC legitimate (20 dB)"),
    ("sbi_tower_profile",  20, "rogue",         "Rogue attack on SBI"),
    ("sbi_tower_profile",  20, "impersonation", "HDFC impersonates SBI"),
    ("sbi_tower_profile",  15, "legitimate",    "SBI legitimate (15 dB)"),
]
print(f"    {'Scenario':<30} | {'RF Score':>10} | {'Expected':>10}")
print(f"    {'-'*30}-+-{'-'*10}-+-{'-'*10}")
all_passed = True
for claimed, snr, stype, label in scenarios:
    score = get_rf_score(claimed, scenario_snr=snr,
                         scenario_type=stype)
    expected = "HIGH" if stype == "legitimate" else "LOW"
    actual = "HIGH" if score > 0.5 else "LOW"
    status = "✓" if expected == actual else "✗"
    if expected != actual:
        all_passed = False
    print(f"    {label:<30} | {score:>10.3f} | {status} {expected:>8}")

print("\n[2] Testing signal-based API (get_rf_score_from_signal)")
result = run_end_to_end("sbi_tower_profile", snr_db=20,
                        n_symbols=1, seed=42, channel_drift=0.20)
rx_pilots = result["rx_pilots"]
api_result = get_rf_score_from_signal(rx_pilots, "sbi_tower_profile")
print(f"    RF score        : {api_result['rf_score']:.3f}")
print(f"    Verdict         : {api_result['verdict']}")
print(f"    Predicted       : {api_result['predicted_label']}")
print(f"    Min distance    : {api_result['min_distance']:.3f}")

print("\n[3] Integration summary")
if all_passed and api_result["verdict"] == "match":
    print("    All tests passed — RF layer is integration-ready.")
else:
    print("    Some tests failed — check output above.")

print("=" * 60)
