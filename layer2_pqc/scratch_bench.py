import time
import oqs
import os

message = b"Your OTP is 482910. Valid 10 min. Do not share. -SBI"
iterations = 1000

print(f"{'Algorithm':<15} | {'KeyGen (ms)':<12} | {'Sign (ms)':<10} | {'Verify (ms)':<10}")
print("-" * 55)

for algo in ['ML-DSA-44', 'ML-DSA-65', 'ML-DSA-87']:
    try:
        with oqs.Signature(algo) as signer:
            # Warm up
            pk = signer.generate_keypair()
            sig = signer.sign(message)
            
            # KeyGen
            start = time.time()
            for _ in range(100):
                with oqs.Signature(algo) as s:
                    s.generate_keypair()
            keygen_ms = (time.time() - start) / 100 * 1000

            # Sign
            start = time.time()
            for _ in range(iterations):
                signer.sign(message)
            sign_ms = (time.time() - start) / iterations * 1000

            # Verify
            start = time.time()
            for _ in range(iterations):
                signer.verify(message, sig, pk)
            verify_ms = (time.time() - start) / iterations * 1000

            print(f"{algo:<15} | {keygen_ms:<12.3f} | {sign_ms:<10.3f} | {verify_ms:<10.3f}")
    except Exception as e:
        print(f"{algo:<15} | Error: {e}")
