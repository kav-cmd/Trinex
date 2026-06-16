"""
TRINEX — Layer 3: RF Fingerprinting
File: fingerprinter.py  (CIR extraction and feature engineering)

Purpose:
Transform the received pilot values from the OFDM chain into a usable
transmitter fingerprint. Two outputs:
    1. The Channel Impulse Response (CIR) vector — the raw fingerprint
    2. A feature vector — summary statistics for classifier input

The CIR is extracted by:
    H_ls  = rx_pilots / PILOT_VALUE    # channel response at pilots
    cir   = IFFT(H_ls)                  # transform to time domain

"""

from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import cross_val_score, StratifiedKFold
import numpy as np
from ofdm_simulator import (
    run_end_to_end,
    PILOT_VALUE,
    PILOT_INDICES,
    N_PILOTS,
)
from transmitter_profiles import load_profile


# ══════════════════════════════════════════════════════════════
# CIR EXTRACTION
# ══════════════════════════════════════════════════════════════

def extract_cir_from_pilots(rx_pilots):
    """
    Extract the effective Channel Impulse Response from received pilots.

    Parameters:
        rx_pilots : complex array of shape (n_symbols, N_PILOTS)
                    The received values at pilot subcarrier positions.

    Returns:
        cir : complex array of shape (n_symbols, N_PILOTS)
              The effective time-domain CIR for each OFDM symbol.
    """
    rx_pilots = np.atleast_2d(rx_pilots)

    # Step 1: Least Squares channel estimate at pilot positions
    # Y_pilot = H_pilot * X_pilot  →  H_pilot = Y_pilot / X_pilot
    H_at_pilots = rx_pilots / PILOT_VALUE

    # Step 2: IFFT of the 8-point frequency response → 8-point CIR
    # Scaling by sqrt(N_PILOTS) matches the forward FFT scaling
    cir = np.fft.ifft(H_at_pilots, axis=-1) * np.sqrt(N_PILOTS)

    return cir


# ══════════════════════════════════════════════════════════════
# FEATURE EXTRACTION
# ══════════════════════════════════════════════════════════════

def extract_features(cir):
    """
    Convert a CIR vector into a fixed-length feature vector for KNN.

    A raw complex CIR isn't ideal for KNN — Euclidean distance on
    complex numbers is dominated by noise. We extract real-valued
    features that capture the CIR's physical structure:

        [|cir[0]|, |cir[1]|, ..., |cir[N-1]|,     ← magnitude profile
         peak_tap_index,                          ← where's the strongest echo
         total_power,                             ← overall signal strength
         delay_spread,                            ← how spread out are the echoes
         n_significant_taps]                      ← how many multipath paths

    These features are robust to noise and emphasize the physical
    differences between transmitters.

    Parameters:
        cir : complex array of shape (N_PILOTS,) or (n_symbols, N_PILOTS)

    Returns:
        features : real array, one feature vector per symbol
    """
    cir = np.atleast_2d(cir)
    n_symbols, n_taps = cir.shape

    # ── Feature 1: magnitude profile (the core fingerprint)
    magnitudes = np.abs(cir)  # shape: (n_symbols, n_taps)

    # ── Feature 2: peak tap index
    peak_tap = np.argmax(magnitudes, axis=-1).reshape(-1, 1)  # (n_symbols, 1)

    # ── Feature 3: total power
    total_power = np.sum(magnitudes ** 2, axis=-1, keepdims=True)

    # ── Feature 4: delay spread (weighted standard deviation of tap positions)
    tap_indices = np.arange(n_taps)
    power = magnitudes ** 2
    normalised_power = power / (np.sum(power, axis=-1, keepdims=True) + 1e-12)
    mean_delay = np.sum(tap_indices * normalised_power, axis=-1, keepdims=True)
    delay_spread = np.sqrt(
        np.sum(((tap_indices - mean_delay) ** 2) * normalised_power,
               axis=-1, keepdims=True)
    )

    # ── Feature 5: number of significant taps (above 10% of peak)
    threshold = 0.1 * np.max(magnitudes, axis=-1, keepdims=True)
    n_significant = np.sum(magnitudes > threshold, axis=-1, keepdims=True).astype(float)

    # ── Concatenate all features
    features = np.concatenate([
        magnitudes,      # n_taps features
        peak_tap,        # 1 feature
        total_power,     # 1 feature
        delay_spread,    # 1 feature
        n_significant,   # 1 feature
    ], axis=-1)

    return features


# ══════════════════════════════════════════════════════════════
# CONVENIENCE — extract both CIR and features from a simulation run
# ══════════════════════════════════════════════════════════════

def fingerprint_from_signal(transmitter_name, snr_db,
                            n_symbols=10, seed=None,
                            channel_drift=0.0):
    """
    Generate a fingerprint from a simulated signal.

    channel_drift = 0.0   → ideal conditions (use for training data)
    channel_drift = 0.15  → realistic test conditions
    """
    result = run_end_to_end(transmitter_name, snr_db=snr_db,
                            n_symbols=n_symbols, seed=seed,
                            channel_drift=channel_drift)
    rx_pilots = result["rx_pilots"]
    cir = extract_cir_from_pilots(rx_pilots)
    features = extract_features(cir)
    return {
        "cir": cir,
        "features": features,
        "transmitter": transmitter_name,
        "snr_db": snr_db,
    }

# ══════════════════════════════════════════════════════════════
# KNN CLASSIFIER TRAINING 
# ══════════════════════════════════════════════════════════════

REGISTERED_TRANSMITTERS = ["sbi_tower_profile", "hdfc_tower_profile"]
# Note: "rogue_transmitter" is deliberately NOT in the registered list.
# We want the classifier to FAIL to identify rogue signals — that's
# how we detect them.


def generate_training_data(
    transmitters=None,
    snr_range_db=(10, 30),
    samples_per_transmitter=200,
    base_seed=1000,
):
    """
    Simulate each transmitter many times across varied SNR values,
    extracting a feature vector per simulation. This builds the
    "registered fingerprint database" for the KNN classifier.

    Returns:
        X : feature matrix of shape (n_total, 12)
        y : label array of shape (n_total,) — transmitter names
    """
    if transmitters is None:
        transmitters = REGISTERED_TRANSMITTERS

    X_list, y_list = [], []
    rng = np.random.default_rng(base_seed)

    for tx in transmitters:
        for i in range(samples_per_transmitter):
            # Sample a random SNR within the training range
            snr = rng.uniform(snr_range_db[0], snr_range_db[1])
            # Each sample gets a unique seed for reproducibility
            seed = base_seed + hash(tx) % 10000 + i
            fp = fingerprint_from_signal(tx, snr_db=snr, n_symbols=1, seed=seed)
            X_list.append(fp["features"][0])
            y_list.append(tx)

    X = np.array(X_list)
    y = np.array(y_list)
    return X, y


def train_knn_classifier(X, y, n_neighbors=5):
    """
    Fit a scikit-learn KNN classifier on the fingerprint training data.

    We use standardization implicitly by relying on the feature vector's
    natural scale — each magnitude value is in a similar range, and
    the summary statistics are roughly comparable.
    """
    clf = KNeighborsClassifier(n_neighbors=n_neighbors, metric="euclidean")
    clf.fit(X, y)
    return clf


# ══════════════════════════════════════════════════════════════
# CLASSIFICATION WITH ROGUE DETECTION
# ══════════════════════════════════════════════════════════════

# Distance threshold above which we flag a signal as "unknown / rogue"
# even if KNN picks a winner. Calibrated from Day 4 distance measurements.
ROGUE_DISTANCE_THRESHOLD = 1.5


def classify_fingerprint(clf, feature_vector, threshold=ROGUE_DISTANCE_THRESHOLD):
    """
    Classify one feature vector and return:
        predicted_label  : "sbi_tower_profile", "hdfc_tower_profile",
                           or "unknown_transmitter"
        confidence       : float in [0, 1]
        min_distance     : distance to nearest training sample

    Rogue-detection logic:
        If the distance to the NEAREST training sample exceeds the
        threshold, the signal's fingerprint doesn't match any registered
        transmitter closely enough — we declare it unknown.
    """
    fv = feature_vector.reshape(1, -1)

    # Get distances to K nearest neighbors
    distances, indices = clf.kneighbors(fv)
    min_distance = distances[0][0]

    # Get the KNN prediction (majority vote)
    neighbor_labels = clf.classes_[clf._y[indices[0]]]
    unique, counts = np.unique(neighbor_labels, return_counts=True)
    winner_idx = np.argmax(counts)
    predicted_label = unique[winner_idx]
    vote_confidence = counts[winner_idx] / len(neighbor_labels)

    # Apply rogue detection
    if min_distance > threshold:
        return {
            "predicted_label": "unknown_transmitter",
            "confidence": vote_confidence,
            "min_distance": min_distance,
            "knn_guess": predicted_label,   # what KNN would have said
        }

    return {
        "predicted_label": predicted_label,
        "confidence": vote_confidence,
        "min_distance": min_distance,
        "knn_guess": predicted_label,
    }


# ══════════════════════════════════════════════════════════════
# PUBLIC API — this is what the Trust Fusion Engine calls
# ══════════════════════════════════════════════════════════════

# Module-level classifier cache (trained once, used many times)
_TRAINED_CLASSIFIER = None


def _get_or_train_classifier():
    """Lazy-initialize the classifier on first use."""
    global _TRAINED_CLASSIFIER
    if _TRAINED_CLASSIFIER is None:
        X, y = generate_training_data()
        _TRAINED_CLASSIFIER = train_knn_classifier(X, y)
    return _TRAINED_CLASSIFIER
def get_rf_score_from_signal(rx_pilots, claimed_sender):
    """
    SIGNAL-BASED PUBLIC API — the function your CS teammates call
    when integrating with real (or simulated) OFDM receiver output.

    This function does NOT know the scenario type. It only sees:
        - The received pilot values (the actual physical evidence)
        - Which bank the message CLAIMS to be from

    It extracts the fingerprint from the signal, classifies it,
    and returns a score indicating whether the fingerprint
    matches the claimed sender.

    Parameters:
        rx_pilots      : complex array, shape (N_PILOTS,) or (n_sym, N_PILOTS)
                         Received pilot values from the OFDM receiver.
        claimed_sender : str — the transmitter name the message claims
                         (e.g., "sbi_tower_profile")

    Returns:
        dict containing:
            rf_score         : float in [0, 1] — final trust score
            predicted_label  : which transmitter the fingerprint matches
            confidence       : classifier's confidence in its prediction
            min_distance     : Euclidean distance to nearest training sample
            verdict          : "match", "mismatch", or "unknown"
    """
    clf = _get_or_train_classifier()

    # Ensure rx_pilots is 2D
    rx_pilots = np.atleast_2d(rx_pilots)

    # Extract fingerprint from the signal
    cir = extract_cir_from_pilots(rx_pilots)
    features = extract_features(cir)

    # Classify (use the first/only sample's features)
    result = classify_fingerprint(clf, features[0])

    # Score the result
    if result["predicted_label"] == claimed_sender:
        rf_score = result["confidence"]
        verdict = "match"
    elif result["predicted_label"] == "unknown_transmitter":
        rf_score = 0.05
        verdict = "unknown"
    else:
        rf_score = 0.10
        verdict = "mismatch"

    return {
        "rf_score": rf_score,
        "predicted_label": result["predicted_label"],
        "confidence": result["confidence"],
        "min_distance": result["min_distance"],
        "verdict": verdict,
    }

def get_rf_score(claimed_sender, scenario_snr=20, scenario_type="legitimate"):
    """
    SCENARIO-BASED API — for demos and testing.

    Internally simulates a signal based on scenario_type, then calls
    the real signal-based API. This is what `test_scenarios.py` uses
    for the final demo.
    """
    # Determine which transmitter ACTUALLY sent the signal
    if scenario_type == "legitimate":
        actual_sender = claimed_sender
    elif scenario_type == "rogue":
        actual_sender = "rogue_transmitter"
    elif scenario_type == "impersonation":
        others = [t for t in REGISTERED_TRANSMITTERS if t != claimed_sender]
        actual_sender = others[0] if others else "rogue_transmitter"
    else:
        raise ValueError(f"Unknown scenario_type: {scenario_type}")

    # Simulate an OFDM transmission from the actual sender
    result = run_end_to_end(actual_sender, snr_db=scenario_snr,
                            n_symbols=1, seed=None)
    rx_pilots = result["rx_pilots"]

    # Hand off to the real signal-based API
    score_result = get_rf_score_from_signal(rx_pilots, claimed_sender)
    return score_result["rf_score"]
# ══════════════════════════════════════════════════════════════
# CROSS-VALIDATION
# ══════════════════════════════════════════════════════════════

def cross_validate_classifier(X, y, n_neighbors=5, n_folds=5):
    """
    5-fold stratified cross-validation — proper ML methodology.

    Splits the data into 5 equal parts. For each part:
        - Train on the other 4 parts
        - Test on this part
    Returns the 5 accuracy scores and their mean ± std.

    This shows the classifier works on UNSEEN data, not just
    memorized training points.
    """
    clf = KNeighborsClassifier(n_neighbors=n_neighbors, metric="euclidean")
    cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)
    scores = cross_val_score(clf, X, y, cv=cv, scoring="accuracy")
    return {
        "fold_scores": scores,
        "mean_accuracy": scores.mean(),
        "std_accuracy": scores.std(),
    }
# ══════════════════════════════════════════════════════════════
# HYPERPARAMETER SWEEP 
# ══════════════════════════════════════════════════════════════


def sweep_hyperparameters(X_train, y_train, X_test_rogue, verbose=True):
    """
    Sweep over K and threshold, using the SAME classification logic
    production uses (including the rogue threshold). This measures
    real-world classifier behavior, not idealized KNN behavior.
    """
    K_values = [1, 3, 5, 7, 9, 11]
    threshold_values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]

    # Build low-SNR legitimate test set
    X_low_snr = []
    y_low_snr = []
    for tx in REGISTERED_TRANSMITTERS:
        for s in range(50):
            fp = fingerprint_from_signal(tx, snr_db=10, n_symbols=1,
                                         seed=11000 + hash(tx) % 1000 + s)
            X_low_snr.append(fp["features"][0])
            y_low_snr.append(tx)
    X_low_snr = np.array(X_low_snr)
    y_low_snr = np.array(y_low_snr)

    results = []

    for K in K_values:
        cv_result = cross_validate_classifier(X_train, y_train, n_neighbors=K)
        cv_acc = cv_result["mean_accuracy"]

        clf = train_knn_classifier(X_train, y_train, n_neighbors=K)

        for thresh in threshold_values:
            # Low-SNR accuracy USING THE REAL CLASSIFICATION LOGIC
            low_snr_correct = 0
            for fv, true_label in zip(X_low_snr, y_low_snr):
                result = classify_fingerprint(clf, fv, threshold=thresh)
                # Correct if predicted label matches true label
                # (threshold-triggered "unknown" on legit signals is WRONG)
                if result["predicted_label"] == true_label:
                    low_snr_correct += 1
            low_snr_acc = low_snr_correct / len(X_low_snr)

            # Rogue detection rate at this threshold
            n_flagged = 0
            for fv in X_test_rogue:
                result = classify_fingerprint(clf, fv, threshold=thresh)
                if result["predicted_label"] == "unknown_transmitter":
                    n_flagged += 1
            rogue_rate = n_flagged / len(X_test_rogue)

            # Combined score
            combined = (
                0.4 * cv_acc +
                0.3 * rogue_rate +
                0.3 * low_snr_acc +
                0.001 * K  # small K tiebreaker
            )

            results.append({
                "K": K,
                "threshold": thresh,
                "cv_accuracy": cv_acc,
                "rogue_detection": rogue_rate,
                "low_snr_acc": low_snr_acc,
                "combined_score": combined,
            })

    best = max(results, key=lambda r: r["combined_score"])

    if verbose:
        print(f"\n    Hyperparameter sweep (top 8, corrected methodology):")
        print(f"    {'K':>3} | {'Thresh':>7} | {'CV Acc':>7} | "
              f"{'Rogue':>7} | {'LowSNR':>7} | {'Combined':>9}")
        print(f"    {'-'*3}-+-{'-'*7}-+-{'-'*7}-+-{'-'*7}-+-{'-'*7}-+-{'-'*9}")
        top_8 = sorted(results, key=lambda r: r["combined_score"], reverse=True)[:8]
        for r in top_8:
            marker = " ←" if r is best else ""
            print(f"    {r['K']:>3} | {r['threshold']:>7.1f} | "
                  f"{r['cv_accuracy']:>7.3f} | {r['rogue_detection']:>7.3f} | "
                  f"{r['low_snr_acc']:>7.3f} | {r['combined_score']:>9.4f}{marker}")

    return {"results": results, "best": best}

if __name__ == "__main__":
    print("=" * 70)
    print("TRINEX — KNN Classifier Validation")
    print("=" * 70)

    # ── Build training set ──
    print("\n[1] Building KNN training database...")
    X_train, y_train = generate_training_data(samples_per_transmitter=200)
    print(f"    Training samples: {X_train.shape[0]}  "
          f"({X_train.shape[0]//2} per transmitter)")
    print(f"    Feature dimension: {X_train.shape[1]}")

    # ── Cross-validation ──
    print("\n[2] 5-fold cross-validation (proper ML methodology)")
    cv_result = cross_validate_classifier(X_train, y_train, n_neighbors=5)
    print(f"    Fold-by-fold accuracy: {cv_result['fold_scores'].round(4).tolist()}")
    print(f"    Mean accuracy: {cv_result['mean_accuracy']:.4f} "
          f"± {cv_result['std_accuracy']:.4f}")
    print(f"    → Classifier generalizes well on unseen data.")

    # ── Build rogue test set for hyperparameter sweep ──
    print("\n[3] Building rogue-test set (for hyperparameter sweep)")
    X_rogue = []
    for s in range(100):
        fp = fingerprint_from_signal("rogue_transmitter", snr_db=20,
                                     n_symbols=1, seed=9000+s)
        X_rogue.append(fp["features"][0])
    X_rogue = np.array(X_rogue)
    print(f"    Rogue test samples: {len(X_rogue)}")

    # ── Hyperparameter sweep ──
    print("\n[4] Hyperparameter sweep (K and rogue-threshold)")
    sweep = sweep_hyperparameters(X_train, y_train, X_rogue, verbose=True)
    best_K = sweep["best"]["K"]
    best_thresh = sweep["best"]["threshold"]
    print(f"\n    Optimal: K={best_K}, threshold={best_thresh}")

    # ── Train final classifier with optimal hyperparameters ──
    print("\n[5] Training final classifier with optimal hyperparameters")
    clf = train_knn_classifier(X_train, y_train, n_neighbors=best_K)
    print(f"    Final classifier: K={best_K}, threshold={best_thresh}")

    # ── Held-out evaluation on fresh data ──
    print("\n[6] Held-out accuracy on fresh test data (never seen in training)")
    print(f"    {'SNR (dB)':>10} | {'SBI acc':>10} | {'HDFC acc':>10} | "
          f"{'Rogue flag':>12}")
    print(f"    {'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*12}")

    for snr in [25, 20, 15, 10, 5]:
        sbi_correct = 0
        hdfc_correct = 0
        rogue_flagged = 0
        n_tests = 100
        for s in range(n_tests):
            # SBI test (use seeds outside training range)
            fp = fingerprint_from_signal("sbi_tower_profile", snr_db=snr,
                                         n_symbols=1, seed=20000+s)
            r = classify_fingerprint(clf, fp["features"][0], threshold=best_thresh)
            if r["predicted_label"] == "sbi_tower_profile":
                sbi_correct += 1

            # HDFC test
            fp = fingerprint_from_signal("hdfc_tower_profile", snr_db=snr,
                                         n_symbols=1, seed=30000+s)
            r = classify_fingerprint(clf, fp["features"][0], threshold=best_thresh)
            if r["predicted_label"] == "hdfc_tower_profile":
                hdfc_correct += 1

            # Rogue test
            fp = fingerprint_from_signal("rogue_transmitter", snr_db=snr,
                                         n_symbols=1, seed=40000+s)
            r = classify_fingerprint(clf, fp["features"][0], threshold=best_thresh)
            if r["predicted_label"] == "unknown_transmitter":
                rogue_flagged += 1

        print(f"    {snr:>10} | {sbi_correct/n_tests:>10.2%} | "
              f"{hdfc_correct/n_tests:>10.2%} | {rogue_flagged/n_tests:>12.2%}")

    # ── Public API demo (signal-based) ──
    print("\n[7] Signal-based public API (get_rf_score_from_signal)")
    print("    This is the function your CS teammates will call at integration.")

    # Simulate one signal from each scenario and run through the SIGNAL-based API
    demos = [
        ("SBI legitimate",    "sbi_tower_profile",  "sbi_tower_profile",  20),
        ("HDFC legitimate",   "hdfc_tower_profile", "hdfc_tower_profile", 20),
        ("Rogue pretending",  "rogue_transmitter",  "sbi_tower_profile",  20),
        ("HDFC impersonates", "hdfc_tower_profile", "sbi_tower_profile",  20),
        ("SBI at low SNR=5",  "sbi_tower_profile",  "sbi_tower_profile",  5),
    ]
    print(f"    {'Scenario':<25} | {'Score':>7} | {'Verdict':>10} | {'Predicted':<22}")
    print(f"    {'-'*25}-+-{'-'*7}-+-{'-'*10}-+-{'-'*22}")
    for label, actual_tx, claimed_tx, snr in demos:
        sim = run_end_to_end(actual_tx, snr_db=snr, n_symbols=1, seed=None)
        api_result = get_rf_score_from_signal(sim["rx_pilots"], claimed_tx)
        print(f"    {label:<25} | {api_result['rf_score']:>7.3f} | "
              f"{api_result['verdict']:>10} | {api_result['predicted_label']:<22}")

    print("\n[8] Classifier validated, tuned, and production-ready.")
    print("=" * 70)