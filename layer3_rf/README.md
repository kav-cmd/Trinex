# TRINEX Layer 3 — RF Fingerprinting Module

**Project:** Fraud Detection in Network Communication Systems
**Team:** PS24 — RV College of Engineering
**Authors:** Manaswi (1RV23EC075), Naman Manoj Jain (1RV23EC083)
**Guide:** Dr. Padmaja K V, Department of Electronics and Instrumentation

## Overview

This module implements the physical-layer authentication component
of the TRINEX fraud-detection framework. It verifies whether a
financial communication message physically originated from a
registered bank transmitter by extracting Channel Impulse Response
(CIR) fingerprints from simulated OFDM transmissions and matching
them against a registered profile database.

The module outputs a normalized RF confidence score in the range
[0, 1] that feeds into the central Trust Fusion Engine alongside
the NLP-based semantic analysis layer and the Post-Quantum
Cryptography signature verification layer.

## Module Structure

| File | Purpose |
|------|---------|
| `transmitter_profiles.py` | Generate and store the registered CIR database |
| `ofdm_simulator.py` | Simulate full OFDM transmitter → channel → receiver chain |
| `fingerprinter.py` | Extract CIR fingerprints and compute feature vectors |
| `visualize_fingerprints.py` | Generate result plots for reports |
| `generate_progress_plot.py` | BER vs SNR curve generator |
| `profiles/` | Saved transmitter fingerprint files (.npy format) |

## Technical Approach

The module simulates a simplified OFDM physical layer:
- 64 subcarriers with 8 pilot subcarriers
- QPSK modulation
- 16-sample cyclic prefix
- Multipath fading channel with configurable AWGN

Channel estimation is performed using Least Squares on the pilot
subcarriers. The resulting channel frequency response is
inverse-Fourier-transformed to recover an 8-point effective CIR,
which is characterised through a 12-dimensional feature vector
combining magnitude profile, peak delay, total power, delay
spread, and active-tap count.

## How to Run

Activate the virtual environment, then from the `layer3_rf`
directory:

```bash
python transmitter_profiles.py     # Step 1: Generate registered database
python ofdm_simulator.py           # Step 2: Verify OFDM chain (BER vs SNR)
python fingerprinter.py            # Step 3: Test fingerprint distinguishability
python visualize_fingerprints.py   # Step 4: Generate result plots
```

## Key Results

- BER of 0.0016 at SNR = 30 dB, rising smoothly to 0.30 at SNR = -5 dB
- All three transmitter fingerprints distinguishable with
  Euclidean distance between 3.53 and 5.62 in the 12-dimensional
  feature space
- Intra-class standard deviation of 0.000 at SNR ≥ 10 dB,
  indicating perfectly stable fingerprints
- Graceful degradation at SNR = 0 dB (std grows to ~1.0)

## Next Steps

- KNN classifier training on feature vectors
- Attack injection module (jamming, replay, rogue transmitter)
- Integration interface: `get_rf_score(transmitter_id, snr)`
- Final evaluation plots (confusion matrix, accuracy vs SNR)

## Dependencies

- Python 3.10+
- NumPy
- SciPy
- scikit-learn
- Matplotlib