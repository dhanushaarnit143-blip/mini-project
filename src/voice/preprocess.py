"""
Audio Preprocessing Module for MPF-PD Voice Pipeline (Phase 3).

Handles:
  - Loading audio from file (librosa / soundfile)
  - Converting to mono
  - Resampling to a common 16 kHz target
  - Trimming leading/trailing silence
  - Safe amplitude normalization (peak-normalize; handles near-zero audio)
  - Segmenting valid speech windows (optional)

Preprocessing is applied STRICTLY in the correct direction:
  - No future information is used.
  - Scaler/normalizer statistics are fitted only on training audio in train.py.
  - Trimming and resampling are deterministic and signal-only operations.

UCI Voice Dataset note:
  The UCI Parkinson's Telemonitoring dataset (uci_voice) is a pre-extracted feature
  table (CSV) containing jitter, shimmer, HNR, RPDE, DFA, and PPE.
  It does NOT ship raw audio files.
  Therefore this preprocessing module:
    a) Is used for ANY future raw audio input to the predict_voice() function.
    b) Generates synthetic waveforms only for unit tests (labeled as synthetic).
    c) The CSV tabular branch (load_uci_voice_features) bypasses raw audio loading.

RESEARCH PROTOTYPE ONLY — NOT A CLINICAL TOOL.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

TARGET_SR = 16000          # Standard resampling target
TOP_DB_TRIM = 30.0         # Silence trimming threshold (dB below peak)
MAX_SEGMENT_DURATION = 10.0  # Maximum single-segment duration (seconds)
MIN_SEGMENT_DURATION = 0.5   # Minimum usable segment duration (seconds)


def load_audio(
    file_path: str,
    target_sr: int = TARGET_SR,
    mono: bool = True,
) -> Tuple[Optional[np.ndarray], int]:
    """
    Load an audio file, convert to mono, and resample to target_sr.

    Args:
        file_path: Absolute or relative path to the audio file.
        target_sr: Target sampling rate (default 16000 Hz).
        mono: If True, convert multi-channel audio to mono.

    Returns:
        Tuple (audio_array, sample_rate):
          - audio_array: float32 numpy array, shape (n_samples,). None if load fails.
          - sample_rate: Effective sample rate (= target_sr if resampled).
    """
    try:
        import librosa
    except ImportError:
        logger.error("librosa not installed. Cannot load raw audio files.")
        return None, 0

    path = Path(file_path)
    if not path.exists():
        logger.error("Audio file not found: %s", file_path)
        return None, 0

    try:
        audio, sr = librosa.load(str(path), sr=target_sr, mono=mono)
        audio = audio.astype(np.float32)
        logger.debug("Loaded '%s': %d samples @ %d Hz", file_path, len(audio), sr)
        return audio, sr
    except Exception as exc:
        logger.error("Failed to load audio file '%s': %s", file_path, exc)
        return None, 0


def preprocess_audio(
    audio: np.ndarray,
    sr: int = TARGET_SR,
    trim_silence: bool = True,
    normalize: bool = True,
    top_db: float = TOP_DB_TRIM,
) -> np.ndarray:
    """
    Apply deterministic preprocessing to a loaded audio array.

    Steps:
      1. Ensure mono (1-D) array.
      2. Trim leading/trailing silence (librosa.effects.trim).
      3. Peak-normalize safely (avoids divide-by-zero on near-silent audio).

    No future-dependent transformations are applied.

    Args:
        audio: 1-D float32 audio array.
        sr: Sample rate (used for logging only in this function).
        trim_silence: If True, trim leading/trailing silence.
        normalize: If True, peak-normalize to [-1, 1].
        top_db: Top-dB threshold for silence trimming.

    Returns:
        Preprocessed 1-D float32 audio array.
    """
    try:
        import librosa
    except ImportError:
        logger.warning("librosa not available; skipping silence trim.")
        trim_silence = False

    # 1. Force 1-D mono
    if audio.ndim == 2:
        audio = audio.mean(axis=0)
    audio = audio.astype(np.float32)

    # 2. Trim silence
    if trim_silence:
        try:
            audio_trimmed, _ = librosa.effects.trim(audio, top_db=top_db)
            if len(audio_trimmed) >= int(MIN_SEGMENT_DURATION * sr):
                audio = audio_trimmed
            else:
                logger.warning(
                    "Trimmed audio is too short (%.2fs < %.2fs); using untrimmed.",
                    len(audio_trimmed) / sr,
                    MIN_SEGMENT_DURATION,
                )
        except Exception as exc:
            logger.warning("Silence trimming failed: %s. Using raw audio.", exc)

    # 3. Peak normalize
    if normalize:
        peak = float(np.max(np.abs(audio)))
        if peak > 1e-8:
            audio = audio / peak
        else:
            logger.warning(
                "Audio peak amplitude is near zero (%.2e). Skipping normalization.", peak
            )

    return audio


def segment_audio(
    audio: np.ndarray,
    sr: int = TARGET_SR,
    segment_duration: float = MAX_SEGMENT_DURATION,
    hop_duration: float = 5.0,
) -> list:
    """
    Segment a long audio array into overlapping windows.

    Used when a recording exceeds max_segment_duration (e.g., a sustained /a/ vowel).
    Each segment must be at least MIN_SEGMENT_DURATION seconds.

    Args:
        audio: 1-D float32 audio array.
        sr: Sample rate.
        segment_duration: Window size in seconds.
        hop_duration: Hop size in seconds.

    Returns:
        List of 1-D float32 numpy arrays (segments).
    """
    seg_len = int(segment_duration * sr)
    hop_len = int(hop_duration * sr)
    min_len = int(MIN_SEGMENT_DURATION * sr)

    if len(audio) <= seg_len:
        return [audio]

    segments = []
    start = 0
    while start < len(audio):
        seg = audio[start: start + seg_len]
        if len(seg) >= min_len:
            segments.append(seg)
        start += hop_len

    return segments if segments else [audio]


def generate_synthetic_audio(
    duration_sec: float = 2.0,
    sr: int = TARGET_SR,
    seed: int = 42,
    label: str = "synthetic_test",
) -> np.ndarray:
    """
    Generate a synthetic audio array for UNIT TESTING ONLY.

    THIS FUNCTION PRODUCES SYNTHETIC DATA.
    Output must NEVER be used as real voice data in clinical evaluation.

    Args:
        duration_sec: Duration of synthetic audio in seconds.
        sr: Sample rate.
        seed: Random seed.
        label: Human-readable label attached via docstring (for auditability).

    Returns:
        1-D float32 numpy array of synthetic audio.
    """
    rng = np.random.RandomState(seed)
    n_samples = int(duration_sec * sr)
    t = np.linspace(0, duration_sec, n_samples, endpoint=False)
    # Simple voiced-like signal: sum of harmonics + small noise
    audio = (
        0.5 * np.sin(2 * np.pi * 120 * t)     # fundamental
        + 0.25 * np.sin(2 * np.pi * 240 * t)  # 2nd harmonic
        + 0.1 * np.sin(2 * np.pi * 360 * t)   # 3rd harmonic
        + 0.05 * rng.randn(n_samples)          # noise
    )
    audio = (audio / np.max(np.abs(audio))).astype(np.float32)
    logger.debug("[SYNTHETIC] Generated synthetic audio: label='%s', dur=%.1fs", label, duration_sec)
    return audio


def generate_silent_audio(
    duration_sec: float = 0.5,
    sr: int = TARGET_SR,
) -> np.ndarray:
    """
    Generate a near-silent audio array for unit testing quality rejection.

    THIS IS SYNTHETIC. Used only to verify quality gates function correctly.
    """
    n_samples = int(duration_sec * sr)
    return np.zeros(n_samples, dtype=np.float32) + 1e-9
