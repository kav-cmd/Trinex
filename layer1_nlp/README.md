# 🔐 TRINEX — DistilBERT Fraud/Spam Classifier (v2 — Robust Edition)

A production-ready NLP pipeline to detect **SMS fraud and spam** using fine-tuned DistilBERT, with 5-Fold Stratified Cross-Validation, data augmentation, and adversarial testing.

---

## 🚀 What's New in v2

| Feature | Detail |
|---|---|
| 📦 Dataset | ~6,000+ samples: HuggingFace `sms_spam` + Indian fraud + CertIn advisories |
| 🔄 Augmentation | Applied **per training fold only** — no data leakage |
| 🧪 Evaluation | 5-Fold Stratified Cross-Validation |
| 🛡️ Regularization | Weight decay, warmup scheduling, best-model checkpointing |
| 🚨 Robustness | Adversarial / OOD test messages included |
| 📊 Metrics | Per-fold metrics + averaged confusion matrix |

---

## 📁 Repository Structure

```
TRINEX/
├── notebooks/
│   └── TRINEX_v2_robust.ipynb       # Full Colab notebook
├── src/
│   ├── data_loader.py               # Dataset loading & merging
│   ├── preprocess.py                # Text cleaning & deduplication
│   ├── augment.py                   # Data augmentation functions
│   ├── model.py                     # DistilBERT model & tokenizer factory
│   ├── train.py                     # 5-Fold cross-validation training
│   ├── evaluate.py                  # Metrics, plots, confusion matrix
│   └── adversarial.py               # OOD / adversarial test suite
├── scripts/
│   ├── predict.py                   # Production inference script
│   └── run_training.py              # End-to-end training entrypoint
├── data/
│   └── README.md                    # How to add your custom CSVs
├── models/
│   └── .gitkeep                     # Model weights go here (not tracked)
├── requirements.txt
├── .gitignore
└── README.md
```

---

## ⚙️ Setup

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/TRINEX.git
cd TRINEX
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Add your datasets
Place these CSVs in `data/raw/`:
- `indian_fraud_collected.csv` — columns: `text`, `label`
- `certIn_advisories.csv` — columns: `text`, `label`

The HuggingFace `sms_spam` dataset loads automatically.

---

## 🏋️ Training

```bash
python scripts/run_training.py
```

This runs 5-fold cross-validation and saves the best model (by F1) to `models/distilbert_finetuned/`.

> **Recommended:** GPU (T4 or better). Training takes ~30–45 mins on ~6k samples.

---

## 🔮 Inference

```python
from scripts.predict import predict

fraud_prob, label = predict("Congratulations! You've won Rs.10,00,000. Click here!")
print(label, fraud_prob)  # FRAUD  0.9981
```

---

## 📊 Interpreting Cross-Validation F1

| Mean F1 | Meaning |
|---------|---------|
| > 0.95 | ⚠️ Double-check for data leakage; add more diverse samples |
| 0.85–0.95 | ✅ Good — model generalises well |
| 0.75–0.85 | ⚠️ Decent — try more epochs or data cleaning |
| < 0.75 | ❌ Poor — likely class imbalance or data quality issue |

High std across folds (> 0.05 on F1) means your dataset needs more diversity.

---

## 🗺️ Next Steps

1. If adversarial results are poor → add those message types to your dataset
2. Wire `scripts/predict.py` into your TRINEX app backend
3. Add a Layer 2 rule-based scorer (URLs, urgency words, UPI IDs) for even better recall

---

## 📄 License

MIT License
