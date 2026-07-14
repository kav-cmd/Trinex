# TRINEX â€” Trilayer Trust Fusion Engine

**Fraud Detection in Network Communication Systems**
Interdisciplinary Project (CS367P) Â· RV College of Engineering Â· 2026â€“27

This repository merges the three independently-developed security layers
of the TRINEX project into a single integrated pipeline that produces a
unified **Trust Score** for any incoming SMS / message-based
communication, plus a visually interactive dashboard for live demos.

---


![TRINEX dashboard showing a LEGITIMATE verdict](docs/images/dashboard_legitimate.png)

---

## What's in the box

```
TRINEX_Integrated/
â”œâ”€â”€ dashboard/
â”‚   â”œâ”€â”€ index.html              â­ self-contained interactive frontend
â”‚   â””â”€â”€ preview_*.png           rendered screenshots (LEGITIMATE / SUSPICIOUS / FRAUD / mobile)
â”‚
â”œâ”€â”€ fusion_engine/
â”‚   â”œâ”€â”€ trinex_pipeline.py      â­ unified analyze() â€” calls all 3 layers
â”‚   â”œâ”€â”€ trust_fusion.py         original weighted-score formula
â”‚   â”œâ”€â”€ fri_metric.py           Fraud Risk Index utility
â”‚   â”œâ”€â”€ weight_adapter.py       dynamic-weight stub (future scope)
â”‚   â””â”€â”€ test_scenarios.py
â”‚
â”œâ”€â”€ layer1_nlp/                 from level1.zip â€” DistilBERT fraud classifier
â”‚   â”œâ”€â”€ src/                    model.py, train.py, preprocess.py, â€¦
â”‚   â”œâ”€â”€ scripts/predict.py      inference entrypoint
â”‚   â””â”€â”€ README.md
â”‚
â”œâ”€â”€ layer2_pqc/                 ML-DSA-65 + ML-KEM-768
â”‚   â”œâ”€â”€ verify.py               signature verification API
â”‚   â”œâ”€â”€ bank_registry.py        60+ Indian banks with sender-ID â†’ bank mapping
â”‚   â”œâ”€â”€ demo_pqc.py             standalone PQC demo
â”‚   â”œâ”€â”€ test_cases/             pre-built legit / tampered / fraud packets
â”‚   â”œâ”€â”€ keys/banks/             ML-DSA-65 public keys for each bank
â”‚   â”œâ”€â”€ PERFORMANCE_REPORT.md
â”‚   â””â”€â”€ TRINEX_PQC_DeepDive.md
â”‚
â”œâ”€â”€ layer3_rf/                  RF physical-layer fingerprinting
â”‚   â”œâ”€â”€ fingerprinter.py        get_rf_score() public API
â”‚   â”œâ”€â”€ ofdm_simulator.py       64-subcarrier QPSK OFDM chain
â”‚   â”œâ”€â”€ transmitter_profiles.py CIR profile generator
â”‚   â”œâ”€â”€ attack_injector.py      jamming / replay / rogue simulation
â”‚   â”œâ”€â”€ evaluate_rf.py          accuracy plots + CSV
â”‚   â”œâ”€â”€ profiles/               *.npy fingerprint files
â”‚   â””â”€â”€ test_integration.py     5-scenario integration test
â”‚
â”œâ”€â”€ data/                       merged datasets (UCI SMS spam + Indian fraud + CertIn)
â”œâ”€â”€ tests/                      per-layer + fusion tests
â”œâ”€â”€ docs/ARCHITECTURE.md        original architecture document
â””â”€â”€ README.md                   (this file)
```

---

## The trust-fusion math

Each layer returns a **trust contribution** in `[0, 1]` where `1.0` means
fully trustworthy and `0.0` means not trustworthy at all. The fusion
engine combines them using the weights from Â§1.6 of the IDP report:

```
Trust = (W_NLP Ã— t_NLP) + (W_PQC Ã— t_PQC) + (W_RF Ã— t_RF)

W_NLP = 0.50      â† content carries the strongest signal
W_PQC = 0.30      â† cryptographic identity proof
W_RF  = 0.20      â† physical-layer corroboration
```

Final score is scaled to `[0, 100]` for the dashboard. Verdict bands:

| Score   | Band         | Action                                       |
|--------:|:-------------|:---------------------------------------------|
| â‰¥ 75    | LEGITIMATE   | Deliver to user                              |
| 40 â€“ 75 | SUSPICIOUS   | Quarantine and warn                          |
| < 40    | FRAUD        | Block and report                             |

---

## How the three layers plug in

`fusion_engine/trinex_pipeline.py` exposes a single function:

```python
from fusion_engine.trinex_pipeline import analyze

result = analyze(
    message       = "URGENT: Your SBI account is BLOCKED. Share OTP â€¦",
    sender_id     = "VK-SBIBNK",
    signature     = None,                       # hex string if signed
    claimed_tower = "sbi_tower_profile",
    scenario_type = "rogue",                    # legitimate | rogue | impersonation
)
print(result["trust_score"], result["band"])    # 3.12  FRAUD
```

Internally `analyze()` does this:

1. **Layer 1 (NLP)** â€” tries `scripts.predict.predict()` (DistilBERT).
   If `torch` / the fine-tuned model is unavailable, falls back to a
   tuned heuristic that scores `~50` fraud tokens (urgency, OTP capture,
   prize bait, KYC threats, link shorteners, â€¦) plus URL Ã— OTP and
   ALL-CAPS amplifiers.
2. **Layer 2 (PQC)** â€” tries `verify.get_pqc_score()` (ML-DSA-65 via
   `oqs`). If `liboqs` isn't installed, falls back to a registry-based
   heuristic that checks the sender ID against a known-bank list and
   does a signature-length plausibility check.
3. **Layer 3 (RF)** â€” calls `fingerprinter.get_rf_score()` directly
   (works out of the box â€” only numpy + scikit-learn needed).
4. **Fuse** â€” weighted sum â†’ `Trust Score` âˆˆ `[0, 100]` â†’ verdict band.

Each layer returns `{name, trust, latency_ms, available, detail}` so the
dashboard can show *which* backend ran (real vs heuristic) and *how
long* it took.

---

## Running the demo

### Option A â€” just open the dashboard

```bash
# from the project root
open dashboard/index.html        # macOS
xdg-open dashboard/index.html    # Linux
start dashboard/index.html       # Windows
```

The dashboard is a single self-contained HTML file. It loads instantly,
runs the same three-layer logic client-side in JavaScript, and renders
the verdict the same way the Python pipeline would. **No backend, no
Python, no install** â€” useful for the viva-voce demo.

Includes 5 preset packets covering all three verdict bands plus a free-
form input mode.

### Option B â€” run the Python pipeline

```bash
cd TRINEX_Integrated
pip install numpy scikit-learn          # bare minimum (only RF needs these)
python fusion_engine/trinex_pipeline.py
```

Outputs JSON verdicts for three built-in test cases. To run the real
DistilBERT + ML-DSA backends instead of the heuristics:

```bash
pip install torch transformers           # for Layer 1
pip install oqs                          # for Layer 2 (requires liboqs)
# Drop a fine-tuned model into layer1_nlp/models/distilbert_finetuned/
# Run layer2_pqc/bank_registry.py once to generate per-bank ML-DSA keys
```

---

## Verified verdicts

```
Legitimate SBI debit alert       â†’  79.75  LEGITIMATE
Suspicious unsigned HDFC OTP req â†’  54.25  SUSPICIOUS
Spoofed VK-SBIBNK KYC phishing   â†’   3.12  FRAUD
```

These come straight out of `fusion_engine/trinex_pipeline.py`'s CLI
demo. The dashboard reproduces the same numbers with the same weights
and bands.

---


---

## Results gallery

### Layer 1 (NLP) — DistilBERT cross-validation

Mean F1 = **0.9656** across 5 folds; only 8 misclassifications out of 1,029 test messages.

![F1 score per fold and averaged confusion matrix](docs/images/nlp_f1_confusion_matrix.png)

### Layer 3 (RF) — OFDM BER vs SNR across transmitter profiles

![BER vs SNR for SBI tower, HDFC tower, and rogue transmitter](docs/images/rf_ber_vs_snr.png)

### Layer 3 (RF) — Rogue detection ROC (AUC = 0.9992)

Threshold of 1.5 achieves **100% rogue detection** at a **2.5% false-flag rate**.

![ROC curve and TPR/FPR vs decision threshold](docs/images/rf_roc_analysis.png)

## Per-layer accuracy (from each module's own evaluation)

| Layer | Metric                                  | Value |
|:------|:----------------------------------------|------:|
| L1    | DistilBERT 5-fold F1 (cross-val)        | ~0.93 |
| L2    | ML-DSA-65 verify success on tampered    |  100% rejected |
| L3    | Classification accuracy @ SNR=20 dB     | 98.5% |
| L3    | Rogue transmitter detection rate        |  100% |

Numbers come from `layer1_nlp/notebooks/TRINEX_v2_robust.ipynb`,
`layer2_pqc/PERFORMANCE_REPORT.md`, and `layer3_rf/README.md`.

---

## Architecture (matches the IDP report Figure 1.1)

```
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
   â”‚  Message Packet  â”‚       (text + sender_id + optional PQC sig)
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”˜
             â”‚
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
   â”‚  Layer 1 :: Semantic Intelligence                          â”‚
   â”‚  DistilBERT â†’ fraud_prob â†’ t_NLP = 1 âˆ’ fraud_prob          â”‚
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
             â”‚
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
   â”‚  Layer 2 :: Cryptographic Identity                         â”‚
   â”‚  ML-DSA-65 verify(message, sig, bank_pk)  â†’  t_PQC âˆˆ {0,1} â”‚
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
             â”‚
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
   â”‚  Layer 3 :: Physical Layer Fingerprint                     â”‚
   â”‚  OFDM pilots â†’ CIR â†’ KNN(K=11) â†’ t_RF âˆˆ [0,1]              â”‚
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
             â”‚
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
   â”‚  Trust Fusion Engine                                       â”‚
   â”‚  Trust = 0.5Â·t_NLP + 0.3Â·t_PQC + 0.2Â·t_RF                  â”‚
   â”‚  Band  = LEGITIMATE | SUSPICIOUS | FRAUD                   â”‚
   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## Project authors

| Name             | Roll No.    | Branch                        |
|:-----------------|:------------|:------------------------------|
| Aryaki           | 1RV23CS050  | CSE â€” Layer 1 (NLP)           |
| Kavya            | 1RV23CY025  | CSE-CY â€” Layer 2 (PQC)        |
| Manaswi          | 1RV23EC075  | ECE â€” Layer 3 (RF)            |
| Naman Manoj Jain | 1RV23EC083  | ECE â€” Trust Fusion + dashboard|

**Guide:** Dr. Padmaja K V, Professor, Dept. of EIE, RVCE.

---

## License

Academic project â€” all per-layer code retains its original licence
(level1.zip â†’ MIT, PQC layer â†’ academic use, RF layer â†’ academic use).

