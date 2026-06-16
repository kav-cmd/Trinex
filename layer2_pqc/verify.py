import json
import os
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

BASE = os.path.dirname(os.path.abspath(__file__))


def _load_registry():
    path = os.path.join(BASE, 'keys', 'registry.json')
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def _load_public_key(bank_short):
    path = os.path.join(BASE, 'keys', 'banks', f'{bank_short}.bin')
    if os.path.exists(path):
        with open(path, 'rb') as f:
            return f.read()
    return None


def detect_bank(message, sender_id=None):
    from bank_registry import INDIAN_BANKS

    if sender_id and sender_id in INDIAN_BANKS:
        info = INDIAN_BANKS[sender_id]
        return {
            'bank_short' : info['short'],
            'bank_name'  : info['name'],
            'sender_id'  : sender_id,
            'detected_by': 'sender_id'
        }

    keywords = {
        'SBI'   : ['sbi', 'state bank'],
        'HDFC'  : ['hdfc'],
        'ICICI' : ['icici'],
        'AXIS'  : ['axis bank'],
        'KOTAK' : ['kotak'],
        'PNB'   : ['pnb', 'punjab national'],
        'BOB'   : ['bob', 'bank of baroda'],
        'NPCI'  : ['upi', 'npci', 'bhim'],
        'PAYTM' : ['paytm']
    }

    msg_lower = message.lower()
    for short, kws in keywords.items():
        if any(kw in msg_lower for kw in kws):
            return {
                'bank_short' : short,
                'bank_name'  : short,
                'sender_id'  : sender_id or 'UNKNOWN',
                'detected_by': 'message_content'
            }

    return {
        'bank_short' : None,
        'bank_name'  : 'Unknown',
        'sender_id'  : sender_id or 'UNKNOWN',
        'detected_by': 'none'
    }


def check_liboqs_available() -> bool:
    import platform
    import ctypes.util
    from pathlib import Path
    
    try:
        if ctypes.util.find_library("oqs") or ctypes.util.find_library("liboqs"):
            return True
    except Exception:
        pass
    
    if "OQS_INSTALL_PATH" in os.environ:
        oqs_install_dir = Path(os.environ["OQS_INSTALL_PATH"])
    else:
        oqs_install_dir = Path.home() / "_oqs"
        
    oqs_lib_dir = oqs_install_dir / "bin" if platform.system() == "Windows" else oqs_install_dir / "lib"
    oqs_lib64_dir = oqs_install_dir / "bin" if platform.system() == "Windows" else oqs_install_dir / "lib64"
    
    for lib_dir in (oqs_lib_dir, oqs_lib64_dir):
        if lib_dir.exists():
            for ext in (".dll", ".so", ".dylib"):
                for file in lib_dir.glob(f"*oqs*{ext}"):
                    if file.is_file():
                        return True
    return False


def get_pqc_score(packet, public_key=None):
    if not check_liboqs_available():
        raise ImportError("liboqs shared library not found; skipping import to prevent auto-install loop")

    try:
        import oqs
    except BaseException as e:
        raise ImportError(f"oqs is not available: {e}") from e

    message    = packet.get('message', '')
    sender_id  = packet.get('sender_id', '')
    bank_info  = detect_bank(message, sender_id)
    bank_short = bank_info['bank_short']

    if not packet.get('signature'):
        return {
            'pqc_score' : 0.0,
            'valid'     : False,
            'status'    : 'No signature found',
            'detail'    : f"Claims to be from {bank_info['bank_name']} but unsigned",
            'bank_name' : bank_info['bank_name'],
            'bank_short': bank_short,
            'sender_id' : sender_id
        }

    if not bank_short:
        return {
            'pqc_score' : 0.0,
            'valid'     : False,
            'status'    : 'Unknown sender',
            'detail'    : 'Cannot identify bank',
            'bank_name' : 'Unknown',
            'bank_short': None,
            'sender_id' : sender_id
        }

    if not public_key:
        public_key = _load_public_key(bank_short)

    if not public_key:
        return {
            'pqc_score' : 0.0,
            'valid'     : False,
            'status'    : f'No key for {bank_short}',
            'detail'    : 'Bank public key not registered',
            'bank_name' : bank_info['bank_name'],
            'bank_short': bank_short,
            'sender_id' : sender_id
        }

    try:
        # Try ML-DSA-65 (NIST standard) first, fallback to Dilithium3
        try:
            verifier = oqs.Signature("ML-DSA-65")
        except Exception:
            verifier = oqs.Signature("Dilithium3")

        msg_bytes = message.encode('utf-8')
        sig_bytes = bytes.fromhex(packet['signature'])
        
        # Real OQS verification: message, signature, public_key
        is_valid = verifier.verify(msg_bytes, sig_bytes, public_key)
        verifier.free() # Ensure resources are freed if not using 'with' statement

        return {
            'pqc_score' : 1.0 if is_valid else 0.0,
            'valid'     : is_valid,
            'status'    : f'Valid signature' if is_valid else 'Invalid signature',
            'detail'    : f'Authentic message from {bank_info["bank_name"]}' if is_valid else 'Tampered or forged',
            'bank_name' : bank_info['bank_name'],
            'bank_short': bank_short,
            'sender_id' : sender_id
        }
    except Exception as e:
        if isinstance(e, ImportError):
            raise
        return {
            'pqc_score' : 0.0,
            'valid'     : False,
            'status'    : 'Verification error',
            'detail'    : str(e),
            'bank_name' : bank_info['bank_name'],
            'bank_short': bank_short,
            'sender_id' : sender_id
        }

# ── Phase 2: Secrecy (KEM + AES Decryption) ───────────

def _aes_decrypt(key, b64_ciphertext):
    """Standard AES-256-CFB Decryption"""
    raw = base64.b64decode(b64_ciphertext)
    iv = raw[:16]
    ciphertext = raw[16:]
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    return (decryptor.update(ciphertext) + decryptor.finalize()).decode()

def process_secure_packet(packet, client_private_key=None, shared_secret=None):
    """
    Full Receiver Logic for Phase 2:
    1. Authenticate (Verify ML-DSA Signature)
    2. Decapsulate (ML-KEM-768 to get AES key)
    3. Decrypt (AES-256 to get plaintext)
    """
    # Step 1: Always verify authenticity first
    auth_result = get_pqc_score(packet)
    
    if not auth_result['valid']:
        return auth_result # Reject immediately if signature fails

    # Step 2: Handle Encryption
    if packet.get('encrypted'):
        try:
            # If we don't have the shared secret yet, we must decapsulate
            if not shared_secret and client_private_key and packet.get('kem_ciphertext'):
                ct_bytes = bytes.fromhex(packet['kem_ciphertext'])
                # Assume client_private_key is an initialized oqs.KeyEncapsulation object
                shared_secret = client_private_key.decap_secret(ct_bytes)

            if shared_secret:
                plaintext = _aes_decrypt(shared_secret, packet['message'])
                auth_result['plaintext'] = plaintext
                auth_result['status']    = "Verified & Decrypted"
                auth_result['detail']    = f"Authentic encrypted message from {auth_result['bank_name']}"
            else:
                auth_result['status']    = "Verified (Encrypted)"
                auth_result['detail']    = "Signature valid, but decryption key missing."
        except Exception as e:
            auth_result['valid']  = False
            auth_result['status'] = "Decryption Error"
            auth_result['detail'] = str(e)
            
    return auth_result


if __name__ == "__main__":
    print("Testing verify.py with all test cases...")
    print("="*55)

    test_path = os.path.join(BASE, 'test_cases')
    if not os.path.exists(test_path):
        print("No test cases. Run generate_test_cases.py first")
        exit()

    for filename in sorted(os.listdir(test_path)):
        if filename.endswith('.json') and filename != 'index.json':
            with open(os.path.join(test_path, filename)) as f:
                packet = json.load(f)
            result = get_pqc_score(packet)
            verdict = "✅ VALID" if result['valid'] else "❌ INVALID"
            print(f"\n{filename}")
            print(f"  Bank   : {result['bank_name']}")
            print(f"  Score  : {result['pqc_score']}")
            print(f"  Status : {result['status']}")
            print(f"  Result : {verdict}")