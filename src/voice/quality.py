"""
Audio Quality Checking Module for MPF-PD Voice Pipeline (Phase 3).

Implements pre-screening quality gates for raw audio files before
they enter the feature extraction pipeline.

Quality failures are logged and the file is EXCLUDED from training/evaluation.
Failures are never silently replaced with synthetic substitutes.

Checks:
  - Minimum duration (seconds)
  - Expected sample rate
  - Mono vs multichannel
  - Silence ratio (proportion of near-zero frames)
  - Clipping (proportion of saturated samples)
  - Low signal energy (RMS below threshold)
  - High noise estimate (zero-crossing rate proxy)

RESEARCH PROTOTYPE ONLY — NOT A CLINICAL TOOL.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Quality thresholds (documented constants — not hidden magic numbers)
QUALITY_DEFAULTS = {
    "min_duration_sec": 1.0,          # Minimum valid recording duration
    "expected_sr": 16000,             # Expected sampling rate after resampling
    "max_silence_ratio": 0.90,        # If >90% of frames are silent, reject
    "clipping_threshold": 0.98,       # Samples above this amplitude are clipped
    "max_clipping_ratio": 0.01,       # If >1% of samples are clipped, warn/reject
    "min_rms_energy": 1e-4,           # Minimum RMS energy (normalized audio)
    "max_zcr_rate": 0.60,             # High ZCR = noise-dominated signal
    "silence_frame_threshold": 0.01,  # RMS below this treated as silence
    "frame_length": 2048,             # Frame length for frame-level analysis
    "hop_length": 512,                # Hop length for frame-level analysis
}


def check_audio_quality(
    audio: Optional[np.ndarray],
    sr: int,
    file_path: str = "<unknown>",
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Run all quality checks on a loaded audio array.

    Args:
        audio: 1-D numpy array of audio samples (mono, float32).
               If None, the file was unloadable — automatic FAIL.
        sr: Sampling rate of the loaded audio.
        file_path: Original file path (for logging only).
        config: Override quality threshold dictionary. Missing keys fall back to QUALITY_DEFAULTS.

    Returns:
        Dict with keys:
          - passed (bool): True if ALL checks pass.
          - issues (list[str]): List of failure reasons (empty if passed).
          - metrics (dict): Computed metrics (for logging/audit).
    """
    cfg = {**QUALITY_DEFAULTS, **(config or {})}
    issues: List[str] = []
    metrics: Dict[str, Any] = {}

    # 0. Audio array must not be None
    if audio is None:
        return {
            "passed": False,
            "issues": ["Audio could not be loaded (None array)."],
            "metrics": {},
        }

    # 1. Minimum duration
    duration_sec = len(audio) / sr if sr > 0 else 0.0
    metrics["duration_sec"] = round(duration_sec, 3)
    if duration_sec < cfg["min_duration_sec"]:
        issues.append(
            f"Duration {duration_sec:.2f}s is below minimum {cfg['min_duration_sec']}s."
        )

    # 2. Sample rate check
    metrics["sample_rate"] = sr
    if sr != cfg["expected_sr"]:
        # This is a WARNING not a hard fail — preprocessing will resample
        logger.warning(
            "Audio '%s' sample rate %d != expected %d. Will be resampled.",
            file_path, sr, cfg["expected_sr"]
        )

    # 3. Channel check — must be 1-D (mono) at this stage
    if audio.ndim != 1:
        issues.append(
            f"Audio has {audio.ndim} dimensions; expected 1-D mono array."
        )

    # 4. Silence ratio (frame-level RMS energy)
    if audio.ndim == 1 and len(audio) > cfg["frame_length"]:
        frame_len = cfg["frame_length"]
        hop_len = cfg["hop_length"]
        n_frames = max(1, (len(audio) - frame_len) // hop_len + 1)
        rms_frames = []
        for i in range(n_frames):
            start = i * hop_len
            frame = audio[start: start + frame_len]
            rms_frames.append(float(np.sqrt(np.mean(frame ** 2))))
        rms_arr = np.array(rms_frames)
        silence_ratio = float(np.mean(rms_arr < cfg["silence_frame_threshold"]))
        metrics["silence_ratio"] = round(silence_ratio, 4)
        if silence_ratio > cfg["max_silence_ratio"]:
            issues.append(
                f"Silence ratio {silence_ratio:.2%} exceeds max {cfg['max_silence_ratio']:.0%}."
            )
    else:
        metrics["silence_ratio"] = None

    # 5. Clipping detection
    if audio.ndim == 1:
        clip_thresh = cfg["clipping_threshold"]
        clipping_ratio = float(np.mean(np.abs(audio) >= clip_thresh))
        metrics["clipping_ratio"] = round(clipping_ratio, 5)
        if clipping_ratio > cfg["max_clipping_ratio"]:
            issues.append(
                f"Clipping ratio {clipping_ratio:.3%} exceeds max {cfg['max_clipping_ratio']:.1%}."
            )

    # 6. Signal energy (whole-file RMS)
    if audio.ndim == 1:
        rms_energy = float(np.sqrt(np.mean(audio ** 2))) if len(audio) > 0 else 0.0
        metrics["rms_energy"] = round(rms_energy, 6)
        if rms_energy < cfg["min_rms_energy"]:
            issues.append(
                f"RMS energy {rms_energy:.6f} below minimum {cfg['min_rms_energy']}. "
                "Signal may be empty or nearly silent."
            )

    # 7. Zero-crossing rate proxy for noise
    if audio.ndim == 1 and len(audio) > 1:
        zcr = float(np.mean(np.abs(np.diff(np.sign(audio))) > 0))
        metrics["zero_crossing_rate"] = round(zcr, 4)
        if zcr > cfg["max_zcr_rate"]:
            issues.append(
                f"Zero-crossing rate {zcr:.3f} exceeds max {cfg['max_zcr_rate']}. "
                "Recording may be noise-dominated."
            )
    else:
        metrics["zero_crossing_rate"] = None

    passed = len(issues) == 0

    if not passed:
        logger.warning(
            "Audio quality FAILED for '%s'. Issues: %s", file_path, issues
        )
    else:
        logger.debug("Audio quality PASSED for '%s'.", file_path)

    return {
        "passed": passed,
        "issues": issues,
        "metrics": metrics,
    }
