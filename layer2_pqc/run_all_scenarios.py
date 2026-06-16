"""
run_all_scenarios.py

Runs the PQC attack scenarios and verifies results using the Multi-Bank Gateway.
Uses ML-DSA-65 (CRYSTALS-Dilithium3 / NIST FIPS 204).
"""

import json
import os
import sys
from verify import get_pqc_score

base = os.path.dirname(os.path.abspath(__file__))
test_path = os.path.join(base, 'test_cases')

print("\n" + "=" * 60)
print("PQC LAYER — SECURITY SCENARIO EVALUATION")
print("CRYSTALS-Dilithium3 | NIST FIPS 204")
print("=" * 60)

# Define the scenarios based on the generated files
test_files = [
    ('legit_sbi-alerts.json',      'Scenario 1: Authentic SBI OTP',      'LEGITIMATE'),
    ('legit_hdfcbk.json',          'Scenario 2: Authentic HDFC Alert',   'LEGITIMATE'),
    ('fraud_sbi-alerts.json',      'Scenario 3: Unsigned SBI Phishing',  'FRAUD'),
    ('fraud_npci.json',            'Scenario 4: Fake NPCI KYC Link',     'FRAUD'),
    ('tampered_sbi.json',          'Scenario 5: Tampered Transaction',   'FRAUD'),
]

results_log = []
all_passed  = True

if not os.path.exists(test_path):
    print(f"Error: {test_path} not found. Run 'python3 generate_test_cases.py' first.")
    sys.exit(1)

for filename, label, expected in test_files:
    file_path = os.path.join(test_path, filename)
    
    if not os.path.exists(file_path):
        print(f"Skipping {filename}: File not found.")
        continue

    with open(file_path) as f:
        packet = json.load(f)

    # Verify using the PQC verification function (keys are loaded automatically)
    result  = get_pqc_score(packet)

    verdict = 'LEGITIMATE' if result['valid'] else 'FRAUD'
    passed  = (verdict == expected)
    if not passed:
        all_passed = False

    # Print result
    print(f"\n{label}")
    print(f"File     : {filename}")
    print(f"Bank     : {result.get('bank_name', 'Unknown')}")
    print(f"Status   : {result['status']}")
    print(f"Verdict  : {verdict}")
    print(f"Expected : {expected}")
    print(f"Result   : {'✅ PASS' if passed else '❌ FAIL'}")
    print("-" * 60)

    results_log.append({
        'Scenario': label,
        'Status'   : result['status'],
        'Verdict'  : verdict,
        'Expected' : expected,
        'Result': 'PASS' if passed else 'FAIL'
    })

print(f"\nOverall Result: {'✅ ALL SCENARIOS PASSED' if all_passed else '❌ SOME SCENARIOS FAILED'}")

# Save results
os.makedirs(os.path.join(base, 'results'), exist_ok=True)
output_path = os.path.join(base, 'results', 'scenario_results.json')
with open(output_path, 'w') as f:
    json.dump(results_log, f, indent=2)

# Display Results
print("\nSUMMARY TABLE:")
print("=" * 75)
header = f"{'Scenario':<30} | {'Status':<20} | {'Verdict':<12} | {'Result':<6}"
print(header)
print("-" * 75)
for res in results_log:
    print(f"{res['Scenario']:<30} | {res['Status']:<20} | {res['Verdict']:<12} | {res['Result']:<6}")
print("=" * 75)

# Save results
os.makedirs(os.path.join(base, 'results'), exist_ok=True)
output_path = os.path.join(base, 'results', 'scenario_results.json')
with open(output_path, 'w') as f:
    json.dump(results_log, f, indent=2)

print("\nResults saved to 'results/scenario_results.json'")
print("Done!")

