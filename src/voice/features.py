"""
Voice Feature Extraction Module for MPF-PD (Phase 3).

Two feature extraction pathways:

  PATH A — Tabular (UCI Parkinson's Telemonitoring CSV):
    extract_tabular_voice_features(df)
    Directly reads jitter, shimmer, HNR, RPDE, DFA, PPE from the precomputed
    feature table. No raw audio needed.
    This is the PRIMARY path for the uci_voice dataset.

  PATH B — Raw Audio (librosa):
    extract_spectral_features(audio, sr)
    Computes MFCCs, delta-MFCCs, spectral centroid, bandwidth, rolloff,
    spectral contrast, zero-crossing rate, pitch (mean F0, std F0,
    voiced_fraction via librosa.pyin), and pause-related features (n_pauses,
    pause_ratio, mean_pause_duration_sec, speech_rate_sps via librosa.effects.split)
    from a raw waveform.
    Used when audio files are available (e.g., mPower m4a recordings).

  PATH C — Parselmouth / Praat jitter/shimmer:
    extract_praat_features(audio, sr)
    Requires parselmouth installation. Falls back gracefully to NaN columns
    if parselmouth is not available, with a logged WARNING.
    Do NOT silently substitute fabricated values for unavailable features.

FEATURE LIMITATIONS (documented per project rules):
  - If parselmouth is not installed, jitter/shimmer/HNR from praat cannot
    be computed from raw waveform. Columns are set to NaN and a warning logged.
  - The UCI feature table already contains precomputed jitter/shimmer/HNR.
    These are used directly (PATH A) without re-extracting from raw audio.
  - No features use future diagnosis information as input.

RESEARCH PROTOTYPE ONLY — NOT A CLINICAL TOOL.
"""

import logging
from typing import Dict, Any, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
# UCI Telemonitoring feature columns (raw names from the dataset)
# ─────────────────────────────────────────────────────────────────
UCI_RAW_FEATURE_COLS = [
    "Jitter(%)",
    "Jitter(Abs)",
    "Jitter:RAP",
    "Jitter:PPQ5",
    "Jitter:DDP",
    "Shimmer",
    "Shimmer(dB)",
    "Shimmer:APQ3",
    "Shimmer:APQ5",
    "Shimmer:APQ11",
    "Shimmer:DDA",
    "NHR",
    "HNR",
    "RPDE",
    "DFA",
    "PPE",
]

# Canonical renamed columns (safe Python identifiers)
UCI_FEATURE_RENAMED = {
    "Jitter(%)": "jitter_pct",
    "Jitter(Abs)": "jitter_abs",
    "Jitter:RAP": "jitter_rap",
    "Jitter:PPQ5": "jitter_ppq5",
    "Jitter:DDP": "jitter_ddp",
    "Shimmer": "shimmer",
    "Shimmer(dB)": "shimmer_db",
    "Shimmer:APQ3": "shimmer_apq3",
    "Shimmer:APQ5": "shimmer_apq5",
    "Shimmer:APQ11": "shimmer_apq11",
    "Shimmer:DDA": "shimmer_dda",
    "NHR": "nhr",
    "HNR": "hnr",
    "RPDE": "rpde",
    "DFA": "dfa",
    "PPE": "ppe",
}

TABULAR_FEATURE_NAMES = list(UCI_FEATURE_RENAMED.values())

# Spectral feature names (PATH B)
N_MFCC = 13

# Pitch feature names (PATH B — requires librosa.pyin)
PITCH_FEATURE_NAMES = [
    "pitch_mean_hz",    # Mean fundamental frequency (voiced frames only)
    "pitch_std_hz",     # Std of fundamental frequency (voiced frames)
    "voiced_fraction",  # Fraction of frames detected as voiced
]

# Pause-related feature names (PATH B — requires librosa.effects.split)
PAUSE_FEATURE_NAMES = [
    "n_pauses",                # Number of pause segments detected
    "pause_ratio",             # Fraction of total duration that is silence/pause
    "mean_pause_duration_sec", # Mean pause duration in seconds
    "speech_rate_sps",         # Speech rate: voiced segments per second of total audio
]

SPECTRAL_FEATURE_NAMES = (
    [f"mfcc_{i}" for i in range(N_MFCC)]
    + [f"mfcc_delta_{i}" for i in range(N_MFCC)]
    + ["spectral_centroid", "spectral_bandwidth", "spectral_rolloff",
       "spectral_contrast_mean", "zero_crossing_rate"]
    + PITCH_FEATURE_NAMES
    + PAUSE_FEATURE_NAMES
)

# Combined feature list when both paths are available
ALL_FEATURE_NAMES = TABULAR_FEATURE_NAMES + SPECTRAL_FEATURE_NAMES

# Documented limitations
VOICE_LIMITATIONS = [
    "UCI Parkinson's Telemonitoring dataset (uci_voice) has NO healthy controls "
    "(all 42 participants are PD patients with longitudinal UPDRS scores). "
    "Binary classification is binarized UPDRS severity rather than PD vs. healthy control.",
    "Jitter/shimmer/HNR extracted from UCI CSV (precomputed by original authors) "
    "using Praat tools. These are not re-computed here to avoid introducing toolchain discrepancies.",
    "Parselmouth/Praat jitter-shimmer extraction from raw waveform is only attempted "
    "when parselmouth is installed; otherwise feature columns are set to NaN.",
    "Spectral features (MFCCs etc.) are computed only when raw audio files are provided. "
    "The UCI dataset ships as a precomputed feature CSV — no raw audio files are distributed.",
    "Pitch (F0) and pause-related features are extracted via librosa.pyin and "
    "librosa.effects.split only for raw audio input (PATH B). They are NOT available "
    "from the UCI Telemonitoring tabular CSV, and are NOT used in the tabular training pipeline.",
    "Voice alone is unlikely to be a novel biomarker for PD; "
    "contribution is as a component in multimodal fusion (Phase 6).",
    "No clinical claims: all risk scores are research prototype estimates.",
]


# ─────────────────────────────────────────────────────────────────
# PATH A: UCI Tabular feature extraction
# ─────────────────────────────────────────────────────────────────

def extract_tabular_voice_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract voice features directly from the UCI Parkinson's Telemonitoring
    pre-extracted feature table.

    Renames raw columns to safe Python identifiers. Missing columns are set to NaN
    and documented. No values are invented.

    Args:
        df: DataFrame with UCI raw column names (e.g., 'Jitter(%)', 'HNR', ...).

    Returns:
        pd.DataFrame: Features with canonical column names.
    """
    feat = pd.DataFrame(index=df.index)

    missing_cols = []
    for raw_col, new_col in UCI_FEATURE_RENAMED.items():
        if raw_col in df.columns:
            feat[new_col] = df[raw_col].astype(float)
        else:
            feat[new_col] = np.nan
            missing_cols.append(raw_col)

    if missing_cols:
        logger.warning(
            "Missing UCI feature columns (set to NaN): %s", missing_cols
        )

    return feat[TABULAR_FEATURE_NAMES]


# ─────────────────────────────────────────────────────────────────
# PATH B: Spectral feature extraction from raw audio (librosa)
# ─────────────────────────────────────────────────────────────────

def extract_spectral_features(
    audio: np.ndarray,
    sr: int = 16000,
    n_mfcc: int = N_MFCC,
) -> Dict[str, Any]:
    """
    Extract spectral, cepstral, pitch, and pause-related features from a raw audio
    array using librosa.

    Features:
      - MFCCs (mean across time, n_mfcc coefficients)
      - MFCC delta (mean across time)
      - Spectral centroid (mean)
      - Spectral bandwidth (mean)
      - Spectral rolloff (mean)
      - Spectral contrast (mean across bands → scalar)
      - Zero-crossing rate (mean)
      - Pitch / F0 (mean Hz, std Hz, voiced_fraction) — via librosa.pyin
      - Pause features (n_pauses, pause_ratio, mean_pause_duration_sec,
        speech_rate_sps) — via librosa.effects.split

    Pitch and pause features are extracted in separate try/except blocks so that
    a failure in one does NOT prevent the others from being computed.

    Args:
        audio: 1-D float32 audio array (mono, preprocessed).
        sr: Sample rate.
        n_mfcc: Number of MFCC coefficients.

    Returns:
        Dict mapping feature name to float value.
    """
    try:
        import librosa
    except ImportError:
        logger.error("librosa not installed. Cannot extract spectral features.")
        return {name: np.nan for name in SPECTRAL_FEATURE_NAMES}

    features: Dict[str, Any] = {}

    try:
        # MFCCs
        mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=n_mfcc)
        for i in range(n_mfcc):
            features[f"mfcc_{i}"] = float(np.mean(mfcc[i]))

        # MFCC deltas
        mfcc_delta = librosa.feature.delta(mfcc)
        for i in range(n_mfcc):
            features[f"mfcc_delta_{i}"] = float(np.mean(mfcc_delta[i]))

        # Spectral centroid
        centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)
        features["spectral_centroid"] = float(np.mean(centroid))

        # Spectral bandwidth
        bandwidth = librosa.feature.spectral_bandwidth(y=audio, sr=sr)
        features["spectral_bandwidth"] = float(np.mean(bandwidth))

        # Spectral rolloff
        rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sr)
        features["spectral_rolloff"] = float(np.mean(rolloff))

        # Spectral contrast
        contrast = librosa.feature.spectral_contrast(y=audio, sr=sr)
        features["spectral_contrast_mean"] = float(np.mean(contrast))

        # Zero-crossing rate
        zcr = librosa.feature.zero_crossing_rate(y=audio)
        features["zero_crossing_rate"] = float(np.mean(zcr))

        # ── Pitch features (librosa.pyin) ────────────────────────────────
        try:
            f0, voiced_flag, _ = librosa.pyin(
                audio,
                fmin=librosa.note_to_hz("C2"),   # ~65 Hz — below typical speech
                fmax=librosa.note_to_hz("C7"),   # ~2093 Hz — above typical speech
                sr=sr,
            )
            voiced_f0 = f0[voiced_flag.astype(bool)] if voiced_flag is not None else f0[~np.isnan(f0)]
            voiced_f0 = voiced_f0[~np.isnan(voiced_f0)]

            features["pitch_mean_hz"] = float(np.mean(voiced_f0)) if len(voiced_f0) > 0 else np.nan
            features["pitch_std_hz"] = float(np.std(voiced_f0)) if len(voiced_f0) > 0 else np.nan
            features["voiced_fraction"] = float(np.mean(voiced_flag)) if voiced_flag is not None else np.nan
        except Exception as exc_pitch:
            logger.warning("Pitch (pyin) extraction failed: %s. Features set to NaN.", exc_pitch)
            for name in PITCH_FEATURE_NAMES:
                features.setdefault(name, np.nan)

        # ── Pause-related features (librosa.effects.split) ───────────────
        try:
            intervals = librosa.effects.split(audio, top_db=20, frame_length=2048, hop_length=512)
            total_duration = len(audio) / sr if sr > 0 else 1.0

            n_pauses = max(0, len(intervals) - 1)
            speech_samples = sum(int(e) - int(s) for s, e in intervals) if len(intervals) > 0 else 0
            speech_duration = speech_samples / sr if sr > 0 else 0.0
            pause_duration_total = max(0.0, total_duration - speech_duration)
            pause_ratio = pause_duration_total / total_duration if total_duration > 0 else 0.0
            mean_pause_dur = pause_duration_total / n_pauses if n_pauses > 0 else 0.0
            # Speech rate: number of voiced speech segments per second of total audio
            speech_rate_sps = len(intervals) / total_duration if total_duration > 0 else 0.0

            features["n_pauses"] = float(n_pauses)
            features["pause_ratio"] = float(pause_ratio)
            features["mean_pause_duration_sec"] = float(mean_pause_dur)
            features["speech_rate_sps"] = float(speech_rate_sps)
        except Exception as exc_pause:
            logger.warning("Pause feature extraction failed: %s. Features set to NaN.", exc_pause)
            for name in PAUSE_FEATURE_NAMES:
                features.setdefault(name, np.nan)

    except Exception as exc:
        logger.error("Spectral feature extraction failed: %s", exc)
        for name in SPECTRAL_FEATURE_NAMES:
            features.setdefault(name, np.nan)

    return features


# ─────────────────────────────────────────────────────────────────
# PATH C: Parselmouth / Praat jitter, shimmer, HNR
# ─────────────────────────────────────────────────────────────────

def extract_praat_features(
    audio: np.ndarray,
    sr: int = 16000,
) -> Dict[str, float]:
    """
    Attempt to extract jitter, shimmer, and HNR from raw audio using parselmouth.

    If parselmouth is not installed, returns NaN for all Praat features.
    Does NOT fabricate replacement values.

    Args:
        audio: 1-D float32 audio array.
        sr: Sample rate.

    Returns:
        Dict with keys: jitter_local, shimmer_local, hnr_mean.
                        All NaN if parselmouth unavailable.
    """
    praat_features = {
        "jitter_local_praat": np.nan,
        "shimmer_local_praat": np.nan,
        "hnr_mean_praat": np.nan,
    }

    try:
        import parselmouth
        from parselmouth.praat import call

        snd = parselmouth.Sound(audio.astype(np.float64), sampling_frequency=sr)
        pitch = call(snd, "To Pitch", 0.0, 75, 600)
        point_process = call([snd, pitch], "To PointProcess (cc)")

        jitter = call(point_process, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
        shimmer = call([snd, point_process], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
        harmonicity = call(snd, "To Harmonicity (cc)", 0.01, 75, 0.1, 1.0)
        hnr = call(harmonicity, "Get mean", 0, 0)

        praat_features["jitter_local_praat"] = float(jitter) if jitter is not None else np.nan
        praat_features["shimmer_local_praat"] = float(shimmer) if shimmer is not None else np.nan
        praat_features["hnr_mean_praat"] = float(hnr) if hnr is not None else np.nan

    except ImportError:
        logger.warning(
            "parselmouth not installed. Jitter/shimmer/HNR from Praat are unavailable. "
            "Features set to NaN — NOT imputed or fabricated. "
            "Install parselmouth to enable Praat-based voice quality features."
        )
    except Exception as exc:
        logger.warning("Praat feature extraction failed: %s. Features set to NaN.", exc)

    return praat_features


# ─────────────────────────────────────────────────────────────────
# Unified feature extraction for a single audio recording row
# ─────────────────────────────────────────────────────────────────

def extract_voice_features(
    audio: Optional[np.ndarray] = None,
    sr: int = 16000,
    tabular_row: Optional[pd.Series] = None,
    use_praat: bool = False,
) -> Dict[str, float]:
    """
    Unified feature extraction dispatcher.

    If tabular_row is provided (PATH A): extract UCI tabular features.
    If audio is provided (PATH B/C): extract spectral + optional Praat features.
    If both are provided: merge both feature sets (union).

    Args:
        audio: Optional raw audio array.
        sr: Sample rate of audio.
        tabular_row: Optional pandas Series from UCI feature table.
        use_praat: If True, also attempt Praat extraction from raw audio.

    Returns:
        Dict[str, float]: Combined feature dictionary.
    """
    all_features: Dict[str, float] = {}

    # PATH A — tabular
    if tabular_row is not None:
        df_row = pd.DataFrame([tabular_row])
        tab_feat = extract_tabular_voice_features(df_row)
        all_features.update(tab_feat.iloc[0].to_dict())

    # PATH B — spectral
    if audio is not None:
        spec_feat = extract_spectral_features(audio, sr=sr)
        all_features.update(spec_feat)

        # PATH C — Praat (optional)
        if use_praat:
            praat_feat = extract_praat_features(audio, sr=sr)
            all_features.update(praat_feat)

    return all_features


def get_feature_names(mode: str = "tabular") -> List[str]:
    """
    Return feature name list for a given extraction mode.

    Args:
        mode: 'tabular', 'spectral', or 'all'.

    Returns:
        List of feature names.
    """
    if mode == "tabular":
        return TABULAR_FEATURE_NAMES
    elif mode == "spectral":
        return SPECTRAL_FEATURE_NAMES
    elif mode == "all":
        return TABULAR_FEATURE_NAMES + SPECTRAL_FEATURE_NAMES
    else:
        raise ValueError(f"Unknown mode '{mode}'. Choose 'tabular', 'spectral', or 'all'.")
