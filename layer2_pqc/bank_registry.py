import os
import json
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

BASE = os.path.dirname(os.path.abspath(__file__))


# bank_registry.py — Updated INDIAN_BANKS dictionary

INDIAN_BANKS = {

    # ── Public Sector Banks ───────────────────────────────
    "SBI-ALERTS"  : {"name": "State Bank of India",       "short": "SBI",      "helpline": "1800-11-2211",   "type": "Public Sector"},
    "SBI-OTP"     : {"name": "State Bank of India",       "short": "SBI",      "helpline": "1800-11-2211",   "type": "Public Sector"},
    "SBIINB"      : {"name": "State Bank of India",       "short": "SBI",      "helpline": "1800-11-2211",   "type": "Public Sector"},
    "PNB-ALERTS"  : {"name": "Punjab National Bank",      "short": "PNB",      "helpline": "1800-180-2222",  "type": "Public Sector"},
    "PNBSMS"      : {"name": "Punjab National Bank",      "short": "PNB",      "helpline": "1800-180-2222",  "type": "Public Sector"},
    "BOB-ALERTS"  : {"name": "Bank of Baroda",            "short": "BOB",      "helpline": "1800-258-4455",  "type": "Public Sector"},
    "BOBSMS"      : {"name": "Bank of Baroda",            "short": "BOB",      "helpline": "1800-258-4455",  "type": "Public Sector"},
    "CANBNK"      : {"name": "Canara Bank",               "short": "CANARA",   "helpline": "1800-425-0018",  "type": "Public Sector"},
    "CANBANK"     : {"name": "Canara Bank",               "short": "CANARA",   "helpline": "1800-425-0018",  "type": "Public Sector"},
    "UNIONBK"     : {"name": "Union Bank of India",       "short": "UBI",      "helpline": "1800-22-2244",   "type": "Public Sector"},
    "UNIONB"      : {"name": "Union Bank of India",       "short": "UBI",      "helpline": "1800-22-2244",   "type": "Public Sector"},
    "BOIALRT"     : {"name": "Bank of India",             "short": "BOI",      "helpline": "1800-220-229",   "type": "Public Sector"},
    "BOISMS"      : {"name": "Bank of India",             "short": "BOI",      "helpline": "1800-220-229",   "type": "Public Sector"},
    "INDBNK"      : {"name": "Indian Bank",               "short": "INDIAN",   "helpline": "1800-425-4422",  "type": "Public Sector"},
    "CENTBK"      : {"name": "Central Bank of India",     "short": "CBI",      "helpline": "1800-22-1911",   "type": "Public Sector"},
    "IOBANK"      : {"name": "Indian Overseas Bank",      "short": "IOB",      "helpline": "1800-425-4445",  "type": "Public Sector"},
    "UCOBNK"      : {"name": "UCO Bank",                  "short": "UCO",      "helpline": "1800-103-0123",  "type": "Public Sector"},
    "PSBSMS"      : {"name": "Punjab and Sind Bank",      "short": "PSB",      "helpline": "1800-419-8300",  "type": "Public Sector"},
    "BMAHA"       : {"name": "Bank of Maharashtra",       "short": "BOM",      "helpline": "1800-233-4526",  "type": "Public Sector"},

    # ── Private Sector Banks ──────────────────────────────
    "HDFCBK"      : {"name": "HDFC Bank",                 "short": "HDFC",     "helpline": "1800-202-6161",  "type": "Private Sector"},
    "HDFC-OTP"    : {"name": "HDFC Bank",                 "short": "HDFC",     "helpline": "1800-202-6161",  "type": "Private Sector"},
    "ICICIB"      : {"name": "ICICI Bank",                "short": "ICICI",    "helpline": "1800-200-3344",  "type": "Private Sector"},
    "ICICITXN"    : {"name": "ICICI Bank",                "short": "ICICI",    "helpline": "1800-200-3344",  "type": "Private Sector"},
    "AXISBK"      : {"name": "Axis Bank",                 "short": "AXIS",     "helpline": "1800-419-5959",  "type": "Private Sector"},
    "AXISMS"      : {"name": "Axis Bank",                 "short": "AXIS",     "helpline": "1800-419-5959",  "type": "Private Sector"},
    "KOTAKB"      : {"name": "Kotak Mahindra Bank",       "short": "KOTAK",    "helpline": "1860-266-2666",  "type": "Private Sector"},
    "KOTAK"       : {"name": "Kotak Mahindra Bank",       "short": "KOTAK",    "helpline": "1860-266-2666",  "type": "Private Sector"},
    "INDUSB"      : {"name": "IndusInd Bank",             "short": "INDUSIND", "helpline": "1860-500-5004",  "type": "Private Sector"},
    "INDUSIND"    : {"name": "IndusInd Bank",             "short": "INDUSIND", "helpline": "1860-500-5004",  "type": "Private Sector"},
    "YESBNK"      : {"name": "Yes Bank",                  "short": "YES",      "helpline": "1800-1200",      "type": "Private Sector"},
    "YESB"        : {"name": "Yes Bank",                  "short": "YES",      "helpline": "1800-1200",      "type": "Private Sector"},
    "IDFCBK"      : {"name": "IDFC First Bank",           "short": "IDFC",     "helpline": "1800-419-4332",  "type": "Private Sector"},
    "IDFCFB"      : {"name": "IDFC First Bank",           "short": "IDFC",     "helpline": "1800-419-4332",  "type": "Private Sector"},
    "FEDBK"       : {"name": "Federal Bank",              "short": "FEDERAL",  "helpline": "1800-425-1199",  "type": "Private Sector"},
    "FEDBNK"      : {"name": "Federal Bank",              "short": "FEDERAL",  "helpline": "1800-425-1199",  "type": "Private Sector"},
    "RBLBNK"      : {"name": "RBL Bank",                  "short": "RBL",      "helpline": "1800-121-9050",  "type": "Private Sector"},
    "RBLBANK"     : {"name": "RBL Bank",                  "short": "RBL",      "helpline": "1800-121-9050",  "type": "Private Sector"},
    "SOUTHB"      : {"name": "South Indian Bank",         "short": "SIB",      "helpline": "1800-425-1809",  "type": "Private Sector"},
    "KARNATAKA"   : {"name": "Karnataka Bank",            "short": "KARNATAKA","helpline": "1800-572-8888",  "type": "Private Sector"},
    "DCBBNK"      : {"name": "DCB Bank",                  "short": "DCB",      "helpline": "1800-209-5363",  "type": "Private Sector"},
    "BANDHANB"    : {"name": "Bandhan Bank",              "short": "BANDHAN",  "helpline": "1800-258-8181",  "type": "Private Sector"},
    "JAMMUKB"     : {"name": "Jammu and Kashmir Bank",    "short": "JKBANK",   "helpline": "1800-1800-234",  "type": "Private Sector"},
    "TMBNK"       : {"name": "Tamilnad Mercantile Bank",  "short": "TMB",      "helpline": "1800-425-0426",  "type": "Private Sector"},
    "CITIBK"      : {"name": "Citibank India",            "short": "CITI",     "helpline": "1860-210-2484",  "type": "Foreign Bank"},
    "HSBCIN"      : {"name": "HSBC India",                "short": "HSBC",     "helpline": "1800-267-3456",  "type": "Foreign Bank"},
    "STANDC"      : {"name": "Standard Chartered Bank",   "short": "SCB",      "helpline": "1800-345-1000",  "type": "Foreign Bank"},
    "DEUTSCH"     : {"name": "Deutsche Bank",             "short": "DEUTSCHE", "helpline": "1860-266-6601",  "type": "Foreign Bank"},

    # ── Small Finance Banks ───────────────────────────────
    "AUSFB"       : {"name": "AU Small Finance Bank",     "short": "AU",       "helpline": "1800-1200-1200", "type": "Small Finance Bank"},
    "EQUITASB"    : {"name": "Equitas Small Finance Bank","short": "EQUITAS",  "helpline": "1800-103-1222",  "type": "Small Finance Bank"},
    "UJJIVANB"    : {"name": "Ujjivan Small Finance Bank","short": "UJJIVAN",  "helpline": "1800-208-2121",  "type": "Small Finance Bank"},
    "SURYODAYAB"  : {"name": "Suryoday Small Finance Bank","short": "SURYODAYA","helpline": "1800-266-7711", "type": "Small Finance Bank"},
    "JANASFB"     : {"name": "Jana Small Finance Bank",   "short": "JANA",     "helpline": "1800-2080",      "type": "Small Finance Bank"},
    "ESAFBK"      : {"name": "ESAF Small Finance Bank",   "short": "ESAF",     "helpline": "1800-103-3723",  "type": "Small Finance Bank"},
    "FINCAREB"    : {"name": "Fincare Small Finance Bank","short": "FINCARE",  "helpline": "1860-266-3236",  "type": "Small Finance Bank"},

    # ── Payment Banks ─────────────────────────────────────
    "PAYTMB"      : {"name": "Paytm Payments Bank",       "short": "PAYTM",    "helpline": "0120-4456-456",  "type": "Payment Bank"},
    "AIRTELP"     : {"name": "Airtel Payments Bank",      "short": "AIRTEL",   "helpline": "400",            "type": "Payment Bank"},
    "FINOPB"      : {"name": "Fino Payments Bank",        "short": "FINO",     "helpline": "1860-266-3466",  "type": "Payment Bank"},
    "JIOPB"       : {"name": "Jio Payments Bank",         "short": "JIO",      "helpline": "1800-891-9999",  "type": "Payment Bank"},
    "IPPBSMS"     : {"name": "India Post Payments Bank",  "short": "IPPB",     "helpline": "155299",         "type": "Payment Bank"},
    "NSDLPB"      : {"name": "NSDL Payments Bank",        "short": "NSDL",     "helpline": "1860-258-1000",  "type": "Payment Bank"},

    # ── Payment Networks ──────────────────────────────────
    "NPCI"        : {"name": "NPCI / UPI",                "short": "NPCI",     "helpline": "1800-120-1740",  "type": "Payment Network"},
    "BHIM"        : {"name": "BHIM UPI",                  "short": "BHIM",     "helpline": "1800-120-1740",  "type": "Payment Network"},
    "PHONEPE"     : {"name": "PhonePe",                   "short": "PHONEPE",  "helpline": "080-6872-7374",  "type": "Payment App"},
    "GPAY"        : {"name": "Google Pay",                "short": "GPAY",     "helpline": "1800-419-0157",  "type": "Payment App"},
    "AMAZONPAY"   : {"name": "Amazon Pay",                "short": "AMAZONPAY","helpline": "1800-3000-9009", "type": "Payment App"},
    "MOBIKWIK"    : {"name": "MobiKwik",                  "short": "MOBIKWIK", "helpline": "0124-6727-001",  "type": "Payment App"},
    "FREECHRG"    : {"name": "FreeCharge",                "short": "FREECHARGE","helpline": "1800-100-1888", "type": "Payment App"},

    # ── Cooperative Banks (Major) ─────────────────────────
    "SARASWAT"    : {"name": "Saraswat Bank",             "short": "SARASWAT", "helpline": "1800-229-999",   "type": "Cooperative Bank"},
    "COSMOS"      : {"name": "Cosmos Cooperative Bank",   "short": "COSMOS",   "helpline": "1800-233-0234",  "type": "Cooperative Bank"},

    # ── Government Bodies (commonly impersonated) ─────────
    "RBI"         : {"name": "Reserve Bank of India",     "short": "RBI",      "helpline": "14440",          "type": "Central Bank"},
    "SEBI"        : {"name": "SEBI",                      "short": "SEBI",     "helpline": "1800-266-7575",  "type": "Regulator"},
    "INCOMETAX"   : {"name": "Income Tax Department",     "short": "INCOMETAX","helpline": "1800-180-1961",  "type": "Government"},
    "EPFO"        : {"name": "EPFO",                      "short": "EPFO",     "helpline": "1800-118-005",   "type": "Government"},
    "UIDAI"       : {"name": "UIDAI / Aadhaar",           "short": "UIDAI",    "helpline": "1947",           "type": "Government"},
}


class MultiBankGateway:

    def __init__(self):
        self.banks         = {}
        self.public_keys   = {}
        self.private_keys  = {}
        self._setup_all_banks()

    def _setup_all_banks(self):
        keys_dir = os.path.join(BASE, 'keys', 'banks')
        os.makedirs(keys_dir, exist_ok=True)

        bank_shorts = {}
        for sender_id, info in INDIAN_BANKS.items():
            short = info['short']
            if short not in bank_shorts:
                bank_shorts[short] = {
                    'info'      : info,
                    'sender_ids': []
                }
            bank_shorts[short]['sender_ids'].append(sender_id)

        for short, data in bank_shorts.items():
            import oqs
            # Use ML-DSA-65 (NIST standard for Dilithium3)
            algo = "ML-DSA-65"
            try:
                signer = oqs.Signature(algo)
            except Exception:
                # Fallback to Dilithium3 if ML-DSA name is not recognized
                signer = oqs.Signature("Dilithium3")
                algo = "Dilithium3"

            public_key = signer.generate_keypair()

            with open(os.path.join(keys_dir, f"{short}.bin"), 'wb') as f:
                f.write(public_key)

            self.banks[short] = {
                'signer'    : signer,
                'algo'      : algo,
                'info'      : data['info'],
                'sender_ids': data['sender_ids']
            }
            self.public_keys[short] = public_key

        print(f"Initialised {len(self.banks)} banks with real {algo} keys")

        registry = {}
        for short, data in self.banks.items():
            for sid in data['sender_ids']:
                registry[sid] = short

        with open(os.path.join(BASE, 'keys', 'registry.json'), 'w') as f:
            json.dump(registry, f, indent=2)

        print(f"Registry saved with {len(registry)} sender IDs")

    def sign_message(self, message, sender_id):
        bank_short = INDIAN_BANKS.get(sender_id, {}).get('short')
        if not bank_short:
            raise ValueError(f"Unknown sender: {sender_id}")

        import hashlib, time
        signer    = self.banks[bank_short]['signer']
        algo      = self.banks[bank_short]['algo']
        msg_bytes = message.encode('utf-8')
        signature = signer.sign(msg_bytes)

        return {
            'message'   : message,
            'sender_id' : sender_id,
            'bank_short': bank_short,
            'bank_name' : self.banks[bank_short]['info']['name'],
            'signature' : signature.hex(),
            'algorithm' : algo,
            'msg_hash'  : hashlib.sha256(msg_bytes).hexdigest(),
            'signed'    : True,
            'timestamp' : time.time()
        }

    def unsigned_packet(self, message, sender_id):
        import time
        return {
            'message'   : message,
            'sender_id' : sender_id,
            'bank_short': None,
            'bank_name' : None,
            'signature' : None,
            'signed'    : False,
            'timestamp' : time.time(),
            'encrypted' : False
        }

    # ── Phase 2: Secrecy (KEM + AES) ───────────────────────
    
    def _aes_encrypt(self, key, plaintext):
        """Standard AES-256-CFB Encryption"""
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(plaintext.encode()) + encryptor.finalize()
        return base64.b64encode(iv + ciphertext).decode()

    def create_secure_packet(self, message, sender_id, client_public_key=None):
        """
        Creates a full Quantum-Safe Packet:
        1. Establishes shared secret using ML-KEM-768
        2. Encrypts message with AES-256
        3. Signs the result with ML-DSA-65
        """
        bank_short = INDIAN_BANKS.get(sender_id, {}).get('short')
        if not bank_short:
            raise ValueError(f"Unknown sender: {sender_id}")

        signer = self.banks[bank_short]['signer']
        
        shared_secret = None
        kem_ciphertext = None
        
        # 1. KEM Handshake (ML-KEM-768)
        if client_public_key:
            import oqs
            with oqs.KeyEncapsulation("ML-KEM-768") as bank_kem:
                kem_ciphertext, shared_secret = bank_kem.encap_secret(client_public_key)
        
        # 2. Encryption (AES-256)
        # If no handshake, we simulate using a pre-shared bank key (or keep plaintext for Phase 1 compatibility)
        if shared_secret:
            display_body = self._aes_encrypt(shared_secret, message)
            encrypted = True
        else:
            display_body = message
            encrypted = False

        # 3. Signing (ML-DSA-65)
        # We sign the display_body (encrypted or plain) to ensure tamper-evidence
        msg_bytes = display_body.encode('utf-8')
        signature = signer.sign(msg_bytes)

        import hashlib, time
        return {
            'message'       : display_body,
            'sender_id'     : sender_id,
            'bank_name'     : self.banks[bank_short]['info']['name'],
            'signature'     : signature.hex(),
            'algorithm'     : 'ML-DSA-65',
            'kem_algorithm' : 'ML-KEM-768' if encrypted else None,
            'kem_ciphertext': kem_ciphertext.hex() if kem_ciphertext else None,
            'encrypted'     : encrypted,
            'msg_hash'      : hashlib.sha256(msg_bytes).hexdigest(),
            'timestamp'     : time.time()
        }


if __name__ == "__main__":
    print("="*55)
    print("MULTI-BANK GATEWAY TEST")
    print("Algorithm: CRYSTALS-Dilithium3 (NIST FIPS 204)")
    print("="*55)

    gateway = MultiBankGateway()

    print(f"\nRegistered banks: {len(gateway.banks)}")
    for short, data in gateway.banks.items():
        print(f"  {short:10} ({len(data['sender_ids'])} sender IDs)")