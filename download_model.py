"""
download_model.py
Helper script to download a pre-trained fine-tuned DistilBERT spam classifier
directly from HuggingFace Hub and set it up for the TRINEX pipeline.
"""
import os
from transformers import DistilBertForSequenceClassification, DistilBertTokenizerFast

MODEL_DIR = "models/distilbert_finetuned"
MODEL_ID = "mariagrandury/distilbert-base-uncased-finetuned-sms-spam-detection"

def download():
    print("=" * 60)
    print("DOWNLOADING PRE-TRAINED DISTILBERT SPAM CLASSIFIER")
    print("=" * 60)
    
    print(f"Fetching '{MODEL_ID}' from HuggingFace...")
    model = DistilBertForSequenceClassification.from_pretrained(MODEL_ID)
    tokenizer = DistilBertTokenizerFast.from_pretrained(MODEL_ID)
    
    print(f"Saving model to {MODEL_DIR}...")
    os.makedirs(MODEL_DIR, exist_ok=True)
    model.save_pretrained(MODEL_DIR)
    tokenizer.save_pretrained(os.path.join(MODEL_DIR, "tokenizer"))
    
    print("\n[SUCCESS] Pre-trained model successfully installed!")
    print("The TRINEX pipeline will now use the live deep learning model.")
    print("=" * 60)

if __name__ == "__main__":
    download()
