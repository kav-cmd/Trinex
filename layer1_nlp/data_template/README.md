# Data Directory

## Required Files

Place these CSVs in `data/raw/` before running training:

| File | Columns | Description |
|------|---------|-------------|
| `indian_fraud_collected.csv` | `text`, `label` | Indian fraud SMS messages (label 1=fraud, 0=ham) |
| `certIn_advisories.csv` | `text`, `label` | CertIn security advisory messages |

The HuggingFace `sms_spam` dataset (~5,574 rows) is downloaded automatically.

## Label Convention

| Label | Meaning |
|-------|---------|
| `0` | HAM (legitimate message) |
| `1` | FRAUD / SPAM |

## Generated Files (auto-created, gitignored)

- `data/processed/final_dataset.csv` — merged & cleaned dataset
- `data/train_test_split/` — fold splits (if saved)
