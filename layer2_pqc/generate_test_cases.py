import sys
import os
import json

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from bank_registry import MultiBankGateway


def generate_all():
    print("="*55)
    print("GENERATING TEST CASES (Real Dilithium3)")
    print("="*55)

    gateway   = MultiBankGateway()
    test_path = os.path.join(BASE, 'test_cases')
    os.makedirs(test_path, exist_ok=True)

    cases = []

    legitimate = [
        ("Your OTP for SBI NetBanking is 482910. Valid for 10 minutes. Do not share. -SBI",  "SBI-ALERTS", "SBI legitimate OTP"),
        ("HDFC Bank: Rs.5000 debited from account ending 4521 on 24-Mar. Avl bal Rs.45230",  "HDFCBK",     "HDFC debit alert"),
        ("ICICI Bank: Your UPI transaction of Rs.1000 to Swiggy is successful. Ref: 123456","ICICIB",     "ICICI UPI transaction"),
        ("Axis Bank: Your EMI of Rs.3500 for loan account ending 7890 auto-debited",         "AXISBK",     "Axis EMI debit"),
        ("Kotak Bank: OTP for netbanking login is 739201. Valid 10 min. Do not share.",     "KOTAKB",     "Kotak OTP"),
        ("PNB: Rs.10000 credited to account ending 3456 by NEFT. Avl bal Rs.55000",         "PNB-ALERTS", "PNB credit alert")
    ]

    for msg, sender, label in legitimate:
        packet = gateway.sign_message(msg, sender)
        fname  = f"legit_{sender.lower()}.json"
        with open(os.path.join(test_path, fname), 'w') as f:
            json.dump(packet, f, indent=2)
        cases.append({
            'file': fname, 'label': label, 'bank': sender,
            'type': 'legitimate', 'expected': 'LEGITIMATE'
        })
        print(f"✅ {label}")

    fraud = [
        ("URGENT your SBI account blocked. Verify at bit.ly/sbi-secure immediately.",       "SBI-ALERTS", "SBI phishing"),
        ("HDFC: Your account shows suspicious activity. Reset password at hdfc-secure.net", "HDFCBK",     "HDFC phishing"),
        ("ICICI Alert: Unauthorized login. Call 9876543210 to secure your account NOW.",   "ICICIB",     "ICICI vishing"),
        ("Dear customer your UPI KYC expired. Update at npci-kyc-update.in or UPI blocked","NPCI",       "Fake NPCI KYC")
    ]

    for msg, sender, label in fraud:
        packet = gateway.unsigned_packet(msg, sender)
        fname  = f"fraud_{sender.lower()}.json"
        with open(os.path.join(test_path, fname), 'w') as f:
            json.dump(packet, f, indent=2)
        cases.append({
            'file': fname, 'label': label, 'bank': sender,
            'type': 'fraud', 'expected': 'FRAUD'
        })
        print(f"❌ {label}")

    legit_sbi = gateway.sign_message(
        "SBI: Rs.500 debited from account ending 4521",
        "SBI-ALERTS"
    )
    tampered            = legit_sbi.copy()
    tampered['message'] = "SBI: Rs.50000 debited from account ending 4521"
    with open(os.path.join(test_path, 'tampered_sbi.json'), 'w') as f:
        json.dump(tampered, f, indent=2)
    cases.append({
        'file': 'tampered_sbi.json', 'label': 'SBI tampered amount',
        'bank': 'SBI-ALERTS', 'type': 'tampered', 'expected': 'FRAUD'
    })
    print("⚠️  SBI tampered amount")

    with open(os.path.join(test_path, 'index.json'), 'w') as f:
        json.dump(cases, f, indent=2)

    print(f"\n{len(cases)} test cases generated")
    print(f"Saved to: {test_path}")


if __name__ == "__main__":
    generate_all()