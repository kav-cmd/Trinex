"""
scripts/predict.py
Production inference script for TRINEX fraud/spam detection.

Usage:
    from scripts.predict import predict
    prob, label = predict("Congratulations! You've won Rs.10,00,000!")
    print(label, prob)  # FRAUD  0.9981
"""

import torch
from transformers import DistilBertForSequenceClassification, DistilBertTokenizerFast

MODEL_PATH = "models/distilbert_finetuned"

_model = None
_tokenizer = None


def _load():
    global _model, _tokenizer
    if _model is None:
        print(f"Loading model from {MODEL_PATH}...")
        _tokenizer = DistilBertTokenizerFast.from_pretrained(f"{MODEL_PATH}/tokenizer")
        _model = DistilBertForSequenceClassification.from_pretrained(MODEL_PATH)
        _model.eval()
        if torch.cuda.is_available():
            _model = _model.cuda()
        print("✅ Model loaded.")


def predict(text: str, threshold: float = 0.5) -> tuple[float, str]:
    """
    Classify a message as FRAUD or HAM.

    Args:
        text:      The SMS/message text to classify.
        threshold: Probability threshold for FRAUD (default 0.5).

    Returns:
        (fraud_probability, label) where label is 'FRAUD' or 'HAM'.
    """
    _load()
    inputs = _tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding="max_length",
        max_length=128,
    )
    if torch.cuda.is_available():
        inputs = {k: v.cuda() for k, v in inputs.items()}

    with torch.no_grad():
        logits = _model(**inputs).logits

    probs = torch.softmax(logits, dim=-1)[0]
    fraud_prob = probs[1].item()
    label = "FRAUD" if fraud_prob >= threshold else "HAM"
    return round(fraud_prob, 4), label


if __name__ == "__main__":
    import sys
    msg = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Test message"
    prob, label = predict(msg)
    print(f"Label: {label}  |  Fraud probability: {prob:.4f}")
