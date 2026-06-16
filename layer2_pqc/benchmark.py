import time
import oqs
import os
import json

print("Running benchmark...")
print("=" * 90)

message = b"Your OTP is 482910. Valid 10 min. Do not share. -SBI"
bench_results = []
iterations = 1000

# Benchmark official ML-DSA levels (formerly Dilithium 2, 3, and 5)
for algo in ['ML-DSA-44', 'ML-DSA-65', 'ML-DSA-87']:
    print(f"Testing {algo}...")

    try:
        with oqs.Signature(algo) as signer:
            public_key = signer.generate_keypair()
            sig = signer.sign(message)

            # 1. KeyGen time (averaged over 100 runs)
            start = time.time()
            for _ in range(100):
                with oqs.Signature(algo) as s:
                    pk = s.generate_keypair()
            keygen_ms = (time.time() - start) / 100 * 1000

            # 2. Sign time (averaged over 1000 runs)
            start = time.time()
            for _ in range(iterations):
                sig = signer.sign(message)
            sign_ms = (time.time() - start) / iterations * 1000

            # 3. Verify time (averaged over 1000 runs)
            start = time.time()
            for _ in range(iterations):
                signer.verify(message, sig, public_key)
            verify_ms = (time.time() - start) / iterations * 1000

            bench_results.append({
                'Algorithm'          : algo,
                'Public Key (bytes)' : len(public_key),
                'Signature (bytes)'  : len(sig),
                'KeyGen (ms)'        : round(keygen_ms, 3),
                'Sign (ms)'          : round(sign_ms, 3),
                'Verify (ms)'        : round(verify_ms, 3),
                'Quantum Safe'       : 'Yes'
            })
    except Exception as e:
        print(f"Error testing {algo}: {e}")

# Add classical reference values
bench_results.append({
    'Algorithm'          : 'RSA-2048',
    'Public Key (bytes)' : 256,
    'Signature (bytes)'  : 256,
    'KeyGen (ms)'        : 500.0,
    'Sign (ms)'          : 1.5,
    'Verify (ms)'        : 0.05,
    'Quantum Safe'       : 'No'
})

bench_results.append({
    'Algorithm'          : 'ECDSA-256',
    'Public Key (bytes)' : 64,
    'Signature (bytes)'  : 64,
    'KeyGen (ms)'        : 0.1,
    'Sign (ms)'          : 0.5,
    'Verify (ms)'        : 1.2,
    'Quantum Safe'       : 'No'
})

# Display Results
print("\nBENCHMARK RESULTS")
print("=" * 90)
header = f"{'Algorithm':<15} | {'PubKey':<8} | {'Sig':<8} | {'KeyGen':<10} | {'Sign':<10} | {'Verify':<10}"
print(header)
print("-" * 90)
for res in bench_results:
    pk_size = res.get('Public Key (bytes)', 'N/A')
    sig_size = res.get('Signature (bytes)', 'N/A')
    kg = res.get('KeyGen (ms)', 0)
    sn = res.get('Sign (ms)', 0)
    vr = res.get('Verify (ms)', 0)
    print(f"{res['Algorithm']:<15} | {pk_size:<8} | {sig_size:<8} | {kg:<10.3f} | {sn:<10.3f} | {vr:<10.3f}")
print("=" * 90)

# Save results
base = os.path.dirname(os.path.abspath(__file__))
os.makedirs(f'{base}/results', exist_ok=True)
with open(f'{base}/results/benchmark_results.json', 'w') as f:
    json.dump(bench_results, f, indent=2)

print("\nBenchmark saved to 'results/benchmark_results.json'!")
