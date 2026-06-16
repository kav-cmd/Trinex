from src.utils.logger import get_logger

logger = get_logger(__name__)

def get_decision(trust_score: float) -> str:
    """
    Returns a final decision based on the trust score.
    trust_score >= 0.75 -> SAFE
    0.45 <= trust_score < 0.75 -> SUSPICIOUS
    trust_score < 0.45 -> FRAUD
    """
    if trust_score >= 0.75:
        decision = "SAFE"
    elif trust_score >= 0.45:
        decision = "SUSPICIOUS"
    else:
        decision = "FRAUD"
        
    logger.info(f"Final Decision: {decision} (Score: {trust_score:.4f})")
    return decision
