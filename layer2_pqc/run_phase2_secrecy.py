import oqs
import json
import os
import sys

# Ensure current directory is in path
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from bank_registry import MultiBankGateway
from verify import process_secure_packet

def run_secrecy_demo():
    print("\n" + "=" * 65)
    print("TRINEX PHASE 2: QUANTUM-SAFE SECRECY & ENCRYPTION")
    print("Algorithms: ML-KEM-768 + AES-256 + ML-DSA-65")
    print("=" * 65)

    gateway = MultiBankGateway()
    
    # 1. SETUP: Client (User Phone) generates a Kyber Keypair
    print("\n[Step 1] Client generates ML-KEM-768 Keypair...")
    with oqs.KeyEncapsulation("ML-KEM-768") as client_kem:
        client_pub = client_kem.generate_keypair()
        
        # 2. BANK: SBI wants to send a secret OTP
        print("[Step 2] SBI Gateway prepares an encrypted OTP...")
        secret_msg = "Your private login code is: 8829-QX-01"
        sender_id = "SBI-ALERTS"
        
        # Create a secure packet using the client's public key
        secure_packet = gateway.create_secure_packet(secret_msg, sender_id, client_public_key=client_pub)
        
        print(f"\nOutgoing Packet (JSON):")
        print(f"  - Body (Encrypted): {secure_packet['message'][:30]}...")
        print(f"  - KEM Ciphertext:   {secure_packet['kem_ciphertext'][:30]}...")
        print(f"  - ML-DSA Signature: {secure_packet['signature'][:30]}...")

        # 3. RECEIVER: Process the packet
        print("\n[Step 3] Client receives and processes the packet...")
        
        # Simulation: Pass the 'client_kem' object as the private key source
        result = process_secure_packet(secure_packet, client_private_key=client_kem)
        
        print(f"\nFinal Result:")
        print(f"  - Authenticity: {'✅ VERIFIED' if result['valid'] else '❌ FAILED'}")
        print(f"  - Status:       {result['status']}")
        print(f"  - Decrypted Content: '{result.get('plaintext', 'N/A')}'")
        
        if result.get('plaintext') == secret_msg:
            print("\n✅ SUCCESS: Message was securely transmitted via Quantum Handshake.")
        else:
            print("\n❌ FAILURE: Message decryption failed or content mismatch.")

    # 4. ATTACK SIMULATION: Tampering with Encrypted Body
    print("\n" + "-" * 65)
    print("[Attack Test] Attempting to modify encrypted ciphertext...")
    tampered_packet = secure_packet.copy()
    # Modify one byte of the base64 ciphertext
    msg_list = list(tampered_packet['message'])
    msg_list[-1] = 'A' if msg_list[-1] != 'A' else 'B'
    tampered_packet['message'] = "".join(msg_list)
    
    # Authenticity check should catch it because signature is over the ciphertext
    result_tamper = process_secure_packet(tampered_packet, client_private_key=client_kem)
    print(f"  - Status: {result_tamper['status']}")
    print(f"  - Detail: {result_tamper['detail']}")
    
    if not result_tamper['valid']:
        print("✅ SUCCESS: Tampering detected by PQC signature.")
        
    print("=" * 65)

if __name__ == "__main__":
    run_secrecy_demo()
