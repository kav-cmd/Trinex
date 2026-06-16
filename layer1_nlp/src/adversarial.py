"""
src/adversarial.py
Adversarial / OOD test suite — messages never seen during training.
"""

import torch
from transformers import pipeline

ADVERSARIAL_MSGS = [
    # Obvious fraud
    ("OBVIOUS FRAUD",   "Congratulations! You've won Rs.10,00,000. Click here to claim now!"),
    ("OBVIOUS FRAUD",   "Pay Rs.2000 registration fee for guaranteed work from home job."),
    # Subtle fraud
    ("SUBTLE FRAUD",    "Your account will be deactivated. Verify now: secure-sbi.in/verify"),
    ("SUBTLE FRAUD",    "You have received a refund of Rs.500. Confirm your UPI ID to proceed."),
    ("SUBTLE FRAUD",    "URGENT: KYC expired. Update now or account blocked: bit.ly/kycupd8"),
    # Legitimate
    ("LEGIT — OTP",     "OTP for HDFC login is 839201. Valid 10 mins. Never share with anyone."),
    ("LEGIT — RECHARGE","Airtel recharge Rs.239 successful. Validity: 28 days. Thank you."),
    ("LEGIT — DELIVERY","Your parcel is out for delivery. Track at delhivery.com/track/ABC"),
    # Edge cases
    ("EDGE — BANK",     "SBI: INR 5000 debited from A/c XX1234 on 01-Jan. Avl bal: 12500."),
    ("EDGE — JOBS",     "Exciting opportunity! Apply at careers.tcs.com before 31 Jan."),
]


def run_adversarial_tests(model_path: str):
    """Load the saved model and run adversarial messages through it."""
    classifier = pipeline(
        "text-classification",
        model=model_path,
        tokenizer=f"{model_path}/tokenizer",
        device=0 if torch.cuda.is_available() else -1,
    )

    print(f"\n{'Category':<22} {'Pred':<8} {'Conf':>5}   Result   Message")
    print("-" * 100)

    for category, msg in ADVERSARIAL_MSGS:
        result = classifier(msg, truncation=True, max_length=128)[0]
        label = result["label"]
        score = result["score"]
        icon = "[FRAUD]" if label == "FRAUD" else "[HAM]"

        if "EDGE" in category:
            verdict = "  ?  (ambiguous)"
        elif (label == "FRAUD" and "FRAUD" in category) or (
            label == "HAM" and "LEGIT" in category
        ):
            verdict = "  [correct]"
        else:
            verdict = "  [WRONG]"

        print(f"{category:<22} {icon:<8} {label:<7} {score:>5.3f}   {verdict:<16}  {msg[:50]}")
