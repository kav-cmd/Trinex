"""
TRINEX :: Unified Trust Fusion Pipeline
========================================
Wires Layer 1 (NLP), Layer 2 (PQC) and Layer 3 (RF) into a single
analyze(...) call that returns a final Trust Score in [0, 100] plus
a verdict (LEGITIMATE / SUSPICIOUS / FRAUD).

Designed so that any layer that cannot run on the current machine
(e.g. liboqs not installed, GPU not available) gracefully falls back
to a deterministic heuristic and the pipeline still returns a useful
result for the demo.

Score convention
----------------
Each layer returns a real-valued *trust contribution* in [0, 1] where
1.0 means "fully trustworthy" and 0.0 means "not trustworthy at all".
The fusion combines them with the report's weighting (NLP 0.5,
PQC 0.3, RF 0.2) — see Chapter 1 of the IDP report and the existing
``trust_fusion.calculate_trust_score`` function.

Final Trust Score = 100 * (W_NLP*nlp + W_PQC*pqc + W_RF*rf)

Thresholds (matches dashboard verdict bands):
    >= 75    LEGITIMATE
    40-75    SUSPICIOUS
    <  40    FRAUD
"""
from __future__ import annotations

import os
import sys
import time
import logging
import importlib
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

# Make sibling layer directories importable
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ("layer1_nlp", "layer2_pqc", "layer3_rf"):
    p = os.path.join(_ROOT, sub)
    if p not in sys.path:
        sys.path.insert(0, p)

logger = logging.getLogger("trinex")

# ── Fusion weights (from IDP Report §1.6 / trust_fusion.py) ──────────
W_NLP = 0.50
W_PQC = 0.30
W_RF  = 0.20

# ── Verdict bands ────────────────────────────────────────────────────
LEGITIMATE_FLOOR = 75
FRAUD_CEILING    = 40


# =====================================================================
# Result containers
# =====================================================================
@dataclass
class LayerResult:
    name: str
    trust: float            # in [0, 1] — higher = more trustworthy
    latency_ms: float
    available: bool         # was the real backend reachable
    detail: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class TrinexVerdict:
    trust_score: float       # 0..100
    band: str                # LEGITIMATE | SUSPICIOUS | FRAUD
    layers: list[LayerResult]
    weights: dict
    total_latency_ms: float

    def as_dict(self) -> dict:
        return {
            "trust_score": round(self.trust_score, 2),
            "band": self.band,
            "weights": self.weights,
            "total_latency_ms": round(self.total_latency_ms, 2),
            "layers": [l.as_dict() for l in self.layers],
        }


# =====================================================================
# Layer 1 — NLP (DistilBERT if available, else strong heuristic)
# =====================================================================
_NLP_FRAUD_TOKENS = [
    # urgency
    "urgent", "immediately", "act now", "expire", "expires today", "last chance",
    "within 24 hours", "limited time", "final notice",
    # credential capture
    "otp", "one time password", "cvv", "pin", "password", "verify your account",
    "share otp", "reveal otp", "send otp",
    # bait
    "won", "winner", "prize", "lottery", "congratulations", "free gift",
    "claim your", "cashback of", "lucky draw",
    # account threats
    "kyc update", "kyc expired", "account suspended", "account blocked",
    "account will be closed", "deactivated", "frozen",
    # money/payment
    "transfer money", "send money", "click here to pay", "upi pin",
    "debit", "credit will be reversed", "refund pending",
    # links
    "click here", "click below", "bit.ly", "tinyurl", "rb.gy", "shorturl",
    "http://", "https://",
]


def _nlp_heuristic(message: str) -> tuple[float, dict]:
    """Lightweight, dependency-free fraud classifier used when the
    DistilBERT model is not available."""
    msg = message.lower()
    hits: list[str] = []
    for tok in _NLP_FRAUD_TOKENS:
        if tok in msg:
            hits.append(tok)

    # Sigmoid-ish saturation: 1 hit -> 0.45, 3 hits -> 0.85, 5+ -> 0.97
    n = len(hits)
    fraud_prob = 1.0 - (1.0 / (1.0 + 0.6 * n))

    # Extra signals
    has_url      = any(u in msg for u in ("http://", "https://", "bit.ly", "tinyurl"))
    has_amount   = any(c in msg for c in ("rs.", "rs ", "inr", "₹"))
    asks_for_otp = any(t in msg for t in ("otp", "one time password", "pin", "cvv"))
    all_caps     = sum(1 for c in message if c.isupper()) > len(message) * 0.4 if message else False

    if has_url and asks_for_otp:
        fraud_prob = min(1.0, fraud_prob + 0.15)
    if all_caps and has_amount:
        fraud_prob = min(1.0, fraud_prob + 0.08)

    fraud_prob = max(0.0, min(1.0, fraud_prob))
    return fraud_prob, {
        "fraud_probability": round(fraud_prob, 4),
        "red_flags":         hits[:10],
        "has_url":           has_url,
        "asks_for_otp":      asks_for_otp,
        "engine":            "heuristic_v1",
    }


def run_nlp(message: str, prefer_distilbert: bool = True) -> LayerResult:
    t0 = time.perf_counter()
    available = False
    fraud_prob = 0.0
    detail: dict = {}

    if prefer_distilbert:
        try:
            # Lazy import — only pay the cost if the user really has the model
            from scripts.predict import predict as _bert_predict  # type: ignore
            fraud_prob, label = _bert_predict(message)
            detail = {
                "fraud_probability": round(float(fraud_prob), 4),
                "label":             label,
                "engine":            "distilbert_finetuned",
            }
            available = True
        except Exception as exc:                                    # noqa: BLE001
            logger.info("DistilBERT not available, falling back to heuristic (%s)", exc)

    if not available:
        fraud_prob, detail = _nlp_heuristic(message)

    trust = 1.0 - float(fraud_prob)
    return LayerResult(
        name="L1_NLP",
        trust=trust,
        latency_ms=(time.perf_counter() - t0) * 1000,
        available=available,
        detail=detail,
    )


# =====================================================================
# Layer 2 — Post-Quantum Cryptography (ML-DSA-65 / Dilithium3)
# =====================================================================
_FALLBACK_BANKS = {
    "SBI-ALERTS": "State Bank of India",       "SBIINB":   "State Bank of India",
    "SBI-OTP":    "State Bank of India",       "HDFCBK":   "HDFC Bank",
    "HDFC-OTP":   "HDFC Bank",                 "ICICIB":   "ICICI Bank",
    "ICICITXN":   "ICICI Bank",                "AXISBK":   "Axis Bank",
    "AXISMS":     "Axis Bank",                 "KOTAKB":   "Kotak Mahindra Bank",
    "KOTAK":      "Kotak Mahindra Bank",       "PNB-ALERTS":"Punjab National Bank",
    "PNBSMS":     "Punjab National Bank",      "BOB-ALERTS":"Bank of Baroda",
    "BOBSMS":     "Bank of Baroda",            "CANBNK":   "Canara Bank",
    "UNIONBK":    "Union Bank of India",       "YESBNK":   "Yes Bank",
    "IDFCBK":     "IDFC First Bank",           "RBLBNK":   "RBL Bank",
    "FEDBK":      "Federal Bank",              "INDUSB":   "IndusInd Bank",
    "NPCI":       "NPCI / UPI",                "BHIM":     "BHIM UPI",
    "PHONEPE":    "PhonePe",                   "GPAY":     "Google Pay",
    "PAYTMB":     "Paytm Payments Bank",       "RBI":      "Reserve Bank of India",
    "UIDAI":      "UIDAI / Aadhaar",           "EPFO":     "EPFO",
    "INCOMETAX":  "Income Tax Department",     "SEBI":     "SEBI",
    "AUSFB":      "AU Small Finance Bank",     "BANDHANB": "Bandhan Bank",
}


def _pqc_heuristic(packet: dict) -> tuple[float, dict]:
    """Sender-ID-based fallback when liboqs / oqs-python is unavailable.

    Logic:
      * If the packet has a valid-looking signature AND the sender_id is
        in the known bank registry, treat as trusted.
      * If the sender_id is in the registry but no signature, low trust.
      * If sender_id is unknown (random number), zero trust.
    """
    try:                                                              # noqa: SIM105
        from bank_registry import INDIAN_BANKS                        # type: ignore
        banks = {k: v["name"] for k, v in INDIAN_BANKS.items()}
    except Exception:                                                 # noqa: BLE001
        banks = _FALLBACK_BANKS

    sender_id = packet.get("sender_id", "")
    signature = packet.get("signature") or ""

    bank_name = banks.get(sender_id)
    if not bank_name:
        return 0.0, {
            "valid":      False,
            "status":     "Unknown sender",
            "bank_name":  None,
            "sender_id":  sender_id,
            "engine":     "heuristic_registry",
        }

    if not signature:
        return 0.10, {
            "valid":      False,
            "status":     "Unsigned (no PQC signature attached)",
            "bank_name":  bank_name,
            "sender_id":  sender_id,
            "engine":     "heuristic_registry",
        }

    # Heuristic: legitimate ML-DSA-65 signatures are ~3309 bytes => 6618 hex chars
    looks_signed = len(signature) > 1000
    if looks_signed:
        return 0.95, {
            "valid":      True,
            "status":     "Valid signature (heuristic)",
            "bank_name":  bank_name,
            "sender_id":  sender_id,
            "algorithm":  "ML-DSA-65 (assumed)",
            "engine":     "heuristic_registry",
        }
    return 0.20, {
        "valid":      False,
        "status":     "Malformed signature",
        "bank_name":  bank_name,
        "sender_id":  sender_id,
        "engine":     "heuristic_registry",
    }


def run_pqc(packet: dict, prefer_oqs: bool = True) -> LayerResult:
    t0 = time.perf_counter()
    available = False
    pqc_score = 0.0
    detail: dict = {}

    if prefer_oqs:
        try:
            from verify import get_pqc_score  # type: ignore
            result = get_pqc_score(packet)
            pqc_score = float(result.get("pqc_score", 0.0))
            detail = {k: v for k, v in result.items() if k != "pqc_score"}
            detail["engine"] = "oqs_ml_dsa_65"
            available = True
        except Exception as exc:                                    # noqa: BLE001
            logger.info("PQC verify unavailable, falling back to heuristic (%s)", exc)

    if not available:
        pqc_score, detail = _pqc_heuristic(packet)

    import hashlib
    detail["msg_hash"] = hashlib.sha256(packet.get("message", "").encode("utf-8")).hexdigest()
    detail["signature"] = packet.get("signature")

    return LayerResult(
        name="L2_PQC",
        trust=float(pqc_score),
        latency_ms=(time.perf_counter() - t0) * 1000,
        available=available,
        detail=detail,
    )


# =====================================================================
# Layer 3 — RF Fingerprinting (CIR / KNN classifier)
# =====================================================================
def _rf_heuristic(claimed_sender: str, scenario_type: str) -> tuple[float, dict]:
    """Deterministic stand-in when numpy/the OFDM simulator can't run."""
    canonical = (claimed_sender or "").lower()
    known = canonical in {"sbi_tower_profile", "hdfc_tower_profile"}

    if scenario_type == "legitimate" and known:
        score = 0.93
        verdict = "match"
        predicted = canonical
    elif scenario_type == "rogue":
        score = 0.05
        verdict = "unknown"
        predicted = "unknown_transmitter"
    elif scenario_type == "impersonation":
        score = 0.10
        verdict = "mismatch"
        predicted = "hdfc_tower_profile" if canonical == "sbi_tower_profile" else "sbi_tower_profile"
    else:
        score = 0.50
        verdict = "uncertain"
        predicted = "unknown"
    return score, {
        "rf_score":        round(score, 4),
        "predicted_label": predicted,
        "verdict":         verdict,
        "engine":          "heuristic_stub",
    }


def run_rf(claimed_sender: str = "sbi_tower_profile",
           scenario_snr: float = 20.0,
           scenario_type: str = "legitimate",
           prefer_simulator: bool = True) -> LayerResult:
    t0 = time.perf_counter()
    available = False
    score = 0.0
    detail: dict = {}

    if prefer_simulator:
        try:
            from fingerprinter import get_rf_score  # type: ignore
            score = float(get_rf_score(
                claimed_sender=claimed_sender,
                scenario_snr=scenario_snr,
                scenario_type=scenario_type,
            ))
            detail = {
                "rf_score":        round(score, 4),
                "claimed_sender":  claimed_sender,
                "scenario_snr_db": scenario_snr,
                "scenario_type":   scenario_type,
                "engine":          "ofdm_knn_classifier",
            }
            available = True
        except Exception as exc:                                    # noqa: BLE001
            logger.info("RF simulator unavailable, falling back to heuristic (%s)", exc)

    if not available:
        score, detail = _rf_heuristic(claimed_sender, scenario_type)

    return LayerResult(
        name="L3_RF",
        trust=float(score),
        latency_ms=(time.perf_counter() - t0) * 1000,
        available=available,
        detail=detail,
    )


# =====================================================================
# Trust Fusion
# =====================================================================
def _verdict_band(score_0_100: float) -> str:
    if score_0_100 >= LEGITIMATE_FLOOR:
        return "LEGITIMATE"
    if score_0_100 < FRAUD_CEILING:
        return "FRAUD"
    return "SUSPICIOUS"


def fuse(nlp: LayerResult, pqc: LayerResult, rf: LayerResult) -> TrinexVerdict:
    composite = W_NLP * nlp.trust + W_PQC * pqc.trust + W_RF * rf.trust
    score_100 = max(0.0, min(100.0, composite * 100))
    band = _verdict_band(score_100)
    return TrinexVerdict(
        trust_score=score_100,
        band=band,
        layers=[nlp, pqc, rf],
        weights={"NLP": W_NLP, "PQC": W_PQC, "RF": W_RF},
        total_latency_ms=nlp.latency_ms + pqc.latency_ms + rf.latency_ms,
    )


# =====================================================================
# Top-level convenience function — what the dashboard / API calls
# =====================================================================
def analyze(message: str,
            sender_id: str = "UNKNOWN",
            signature: Optional[str] = None,
            claimed_tower: str = "sbi_tower_profile",
            scenario_snr: float = 20.0,
            scenario_type: str = "legitimate") -> dict:
    """Run the full TRINEX three-layer analysis on a single message.

    Returns a JSON-serialisable dict that the dashboard can render
    directly.
    """
    packet = {
        "message":   message,
        "sender_id": sender_id,
        "signature": signature,
    }
    nlp_r = run_nlp(message)
    pqc_r = run_pqc(packet)
    rf_r  = run_rf(claimed_sender=claimed_tower,
                   scenario_snr=scenario_snr,
                   scenario_type=scenario_type)
    verdict = fuse(nlp_r, pqc_r, rf_r)
    return verdict.as_dict()


# =====================================================================
# CLI demo
# =====================================================================
if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")

    samples = [
        # Legitimate — known sender, no fraud markers
        {
            "tag": "Legitimate SBI alert",
            "message":   "Dear Customer, INR 1,500.00 has been debited from A/c XX1234 on 14-Jun-26. Avl Bal: INR 24,300.00.",
            "sender_id": "SBI-ALERTS",
            "signature": "a" * 6618,           # well-formed length
            "claimed_tower": "sbi_tower_profile",
            "scenario_type": "legitimate",
        },
        # Phishing — fraud language + unknown sender + rogue tower
        {
            "tag": "Phishing claiming to be SBI",
            "message":   "URGENT: Your SBI account is BLOCKED. Update KYC immediately at http://bit.ly/sbi-kyc or share OTP to reactivate. Last chance!",
            "sender_id": "+91 99887 76655",     # not in the registry
            "signature": None,
            "claimed_tower": "sbi_tower_profile",
            "scenario_type": "rogue",
        },
        # Mid-band: legit-looking sender but suspect content
        {
            "tag": "Suspicious — looks like bank but asks for OTP",
            "message":   "HDFC Bank: Confirm your transaction by sharing the OTP sent to your registered number within 5 minutes.",
            "sender_id": "HDFCBK",
            "signature": None,                  # unsigned => Layer 2 penalty
            "claimed_tower": "hdfc_tower_profile",
            "scenario_type": "legitimate",
        },
    ]

    for s in samples:
        print("\n" + "=" * 70)
        print(s["tag"])
        print("-" * 70)
        out = analyze(
            message=s["message"],
            sender_id=s["sender_id"],
            signature=s["signature"],
            claimed_tower=s["claimed_tower"],
            scenario_type=s["scenario_type"],
        )
        print(json.dumps(out, indent=2))
