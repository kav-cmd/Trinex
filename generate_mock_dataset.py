"""
generate_mock_dataset.py
Generates high-quality synthetic datasets for Indian banking alerts.
Populates:
  - data/dataset/raw/indian_fraud_collected.csv
  - data/dataset/raw/certIn_advisories.csv
"""
import os
import pandas as pd

RAW_DIR = "data/dataset/raw"

# --- Legitimate Alerts (Label = 0) ---
legit_messages = [
    # SBI
    "Dear Customer, INR 1,500.00 has been debited from A/c XX1234 on 14-Jun-26. Avl Bal: INR 24,300.00. -SBI",
    "Dear Customer, INR 10,000.00 has been credited to A/c XX1234 on 15-Jun-26. Ref: Ref123456789. -SBI",
    "Your OTP for SBI NetBanking login is 482910. Valid for 10 minutes. Do not share this with anyone.",
    "SBI: Your transaction of INR 3,200.00 on Credit Card ending 9876 is successful at Amazon. Avl Limit: INR 45,000.00.",
    # HDFC
    "HDFC Bank: Rs.5000 debited from account ending 4521 on 24-Mar. Avl bal Rs.45230. Not you? Report to bank.",
    "HDFC Bank OTP: 739201 is your verification code for online transaction at Flipkart. Do not share.",
    "Your HDFC Credit Card bill of Rs 12,450.00 is due on 28-Jun-26. Minimum due Rs 620.00. Please pay to avoid charges.",
    "Rs. 250.00 credited to your HDFC Bank A/c ending 8812 via UPI Ref 62714528391. Avl Bal: Rs 15,240.00.",
    # ICICI
    "ICICI Bank: Your UPI transaction of Rs.1000 to Swiggy is successful. Ref: 123456.",
    "Dear Customer, your ICICI Bank account ending 3012 is credited with Rs 45,000.00 salary on 31-May-26.",
    "ICICI Bank: OTP for password reset is 554192. Do not disclose to anyone. Bank never asks for OTP.",
    "ATM Cash withdrawal of Rs 10,000.00 on ICICI Bank Debit card ending 5510 at ICICI ATM. Avl Bal: Rs 89,320.00.",
    # Axis
    "Axis Bank: Your EMI of Rs.3500 for loan account ending 7890 auto-debited on 05-Jun-26.",
    "Axis Bank OTP: 981204 is your verification code. Valid for 5 minutes. Axis Bank will never call you for OTP.",
    "Axis Bank: Rs. 15,000.00 has been credited to your A/c ending 2451 via IMPS Ref: Axis991283.",
    # Kotak
    "Kotak Bank: OTP for netbanking login is 739201. Valid 10 min. Do not share.",
    "Kotak Bank: Rs 2,400.00 debited from A/c ending 0124 on 12-Jun. Avl Bal: Rs 42,900.00.",
    # PNB
    "PNB: Rs.10000 credited to account ending 3456 by NEFT. Avl bal Rs.55000. Not you? Contact bank helpline.",
    "PNB OTP: 301984 is your code for Aadhaar linking verification. Valid for 10 minutes."
]

# Expand legit templates with minor variations
legit_expanded = []
for i in range(10):
    for msg in legit_messages:
        # Create variation by changing amounts/dates slightly
        var_msg = msg.replace("1,500.00", f"{1000 + i*350}.00")
        var_msg = var_msg.replace("10,000.00", f"{5000 + i*1200}.00")
        var_msg = var_msg.replace("482910", f"{100000 + i*15432}")
        var_msg = var_msg.replace("739201", f"{200000 + i*17432}")
        legit_expanded.append(var_msg)

# --- Fraud/Phishing Alerts (Label = 1) ---
fraud_messages = [
    # SBI Phishing
    "URGENT: Your SBI account is BLOCKED. Update KYC immediately at http://bit.ly/sbi-kyc to reactivate your card.",
    "SBI Alert: Unauthorized login attempt detected from IP 192.168.1.55. Verify identity at http://sbi-secure-net.in now.",
    "Dear SBI customer, your PAN card is not linked to your account. Update at http://tinyurl.com/sbi-pan-link or your account will be suspended.",
    # HDFC Phishing
    "HDFC Bank: Your HDFC account shows suspicious activity. Reset your password at http://hdfc-security-portal.net to secure your funds.",
    "URGENT: Your HDFC netbanking access is suspended due to invalid login attempts. Re-verify here: http://bit.ly/hdfc-reverify.",
    # ICICI Phishing
    "ICICI Bank Alert: We detected an unauthorized transaction of Rs 49,999.00. If not you, block immediately at http://icici-fraud-alert.in.",
    "Dear ICICI Customer, update your mobile number and KYC profile at http://icici-kyc-check.com to avoid account closure.",
    # generic / UPI phishing
    "NPCI Alert: Your UPI KYC has expired. Update your details at http://npci-kyc-update.in or your UPI services will be blocked in 24 hours.",
    "Congratulations! You have won a cashback reward of Rs 2,500.00 from PhonePe. Claim now at http://bit.ly/ppe-reward-2500.",
    "Your Paytm wallet is suspended due to incomplete KYC documents. Please verify your identity at http://paytm-kyc-desk.com immediately.",
    # OTP Requests
    "HDFC Bank: A transaction of Rs 15,000 is pending. Share the OTP you received with our executive on call to confirm.",
    "SBI Customer Care: We are upgrading your credit card limit. Please reply with the 6-digit OTP sent to your phone to activate the offer."
]

# Expand fraud templates with variations
fraud_expanded = []
for i in range(15):
    for msg in fraud_messages:
        var_msg = msg.replace("2,500.00", f"{1500 + i*450}.00")
        var_msg = var_msg.replace("49,999.00", f"{25000 + i*3200}.00")
        var_msg = var_msg.replace("sbi-kyc", f"sbi-kyc-update-{i}")
        var_msg = var_msg.replace("hdfc-reverify", f"hdfc-verify-portal-{i}")
        var_msg = var_msg.replace("15,000", f"{12000 + i*1000}")
        fraud_expanded.append(var_msg)


def generate():
    os.makedirs(RAW_DIR, exist_ok=True)
    
    # 1. Indian Fraud Dataset (mix of legit and fraud bank alerts)
    print(f"Generating Indian Fraud dataset...")
    indian_df = pd.DataFrame({
        "text": legit_expanded[:120] + fraud_expanded[:120],
        "label": [0] * 120 + [1] * 120
    })
    indian_path = os.path.join(RAW_DIR, "indian_fraud_collected.csv")
    indian_df.to_csv(indian_path, index=False)
    print(f"  Saved {len(indian_df)} samples to {indian_path}")

    # 2. CertIn Advisories (focused heavily on security alerts and phishing reports)
    print(f"Generating CertIn Advisories dataset...")
    certin_df = pd.DataFrame({
        "text": legit_expanded[120:200] + fraud_expanded[120:200],
        "label": [0] * len(legit_expanded[120:200]) + [1] * len(fraud_expanded[120:200])
    })
    certin_path = os.path.join(RAW_DIR, "certIn_advisories.csv")
    certin_df.to_csv(certin_path, index=False)
    print(f"  Saved {len(certin_df)} samples to {certin_path}")

    # 3. UCI Spam SMS fallback header file (to satisfy the loader since it also downloads from HF)
    uci_path = os.path.join(RAW_DIR, "uci_sms_spam.csv")
    pd.DataFrame({"text": ["dummy"], "label": [0]}).to_csv(uci_path, index=False)
    print(f"  Saved placeholder to {uci_path}")

    print("\n[SUCCESS] Simulated datasets generated successfully!")
    print("You can now safely run the training scripts.")

if __name__ == "__main__":
    generate()
