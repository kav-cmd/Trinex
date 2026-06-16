import logging

logger = logging.getLogger(__name__)

def calculate_trust_score(
    fraud_probability: float, 
    network_risk_score: float,
    rf_anomaly_score: float
) -> float:
    """
    Calculates the final Risk Score combining all three layers.
    Formula:
    Risk = 0.5 * AI_Score + 0.3 * Network_Risk + 0.2 * RF_Anomaly
    
    Note: High score = High Risk.
    """
    # Weights defined in the project summary
    W_AI = 0.5
    W_NET = 0.3
    W_RF = 0.2
    
    final_risk = (
        (fraud_probability * W_AI) +
        (network_risk_score * W_NET) +
        (rf_anomaly_score * W_RF)
    )
    
    logger.info(f"FUSION: AI({fraud_probability:.2f})*0.5 + NET({network_risk_score:.2f})*0.3 + RF({rf_anomaly_score:.2f})*0.2 = {final_risk:.2f}")
    return final_risk

def get_trust_verdict(risk_score: float) -> str:
    if risk_score > 0.75:
        return "⚠ HIGH RISK: Fraud Communication Detected"
    elif risk_score > 0.4:
        return "⚠ MEDIUM RISK: Suspicious Communication"
    else:
        return "✅ LOW RISK: Trustworthy Communication"

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    score = calculate_trust_score(0.91, 0.73, 0.2)
    print(f"Final Risk: {score:.2f} | Verdict: {get_trust_verdict(score)}")
