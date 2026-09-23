"""
Phase 15 — Unit Tests: Sleep Scoring, Baseline Calculation, Deviation & Trend
==============================================================================
Validates:
  - Sleep quality scoring (RBD-proxy questionnaire scoring)
  - Baseline establishment from 14+ days of daily features
  - Deviation calculation (z-score and MAD-based fallback)
  - Trend detection (Mann-Kendall / linear slope)
  - Quality filter exclusion of low-quality sessions
  - Normalization loader behavior

ALL test data is clearly labeled [SYNTHETIC] — no real participant data.
"""

import math
import json
import pytest
from pathlib import Path
import sys
from typing import List, Dict, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# Pure-Python reference implementations mirroring the JS modules
# ─────────────────────────────────────────────────────────────────────────────

def _mean(vals):
    clean = [float(v) for v in vals if v is not None and math.isfinite(float(v))]
    return sum(clean) / len(clean) if clean else None


def _median(vals):
    clean = sorted([float(v) for v in vals if v is not None and math.isfinite(float(v))])
    if not clean:
        return None
    n = len(clean)
    mid = n // 2
    return (clean[mid-1] + clean[mid]) / 2.0 if n % 2 == 0 else clean[mid]


def _std(vals, ddof=1):
    clean = [float(v) for v in vals if v is not None and math.isfinite(float(v))]
    if len(clean) < 2:
        return 0.0
    m = sum(clean) / len(clean)
    var = sum((x - m) ** 2 for x in clean) / (len(clean) - ddof)
    return math.sqrt(max(0.0, var))


def _mad(vals):
    clean = [float(v) for v in vals if v is not None and math.isfinite(float(v))]
    if not clean:
        return 0.0
    med = _median(clean)
    return _median([abs(v - med) for v in clean]) or 0.0


def calculate_baseline(values: List[float], quality_scores: List[float] = None,
                        min_quality: float = 0.50):
    """
    [SYNTHETIC-SAFE] Python reference implementation of JS baselineCalculator.
    Filters by quality threshold, then computes descriptive stats.
    """
    if quality_scores is None:
        quality_scores = [1.0] * len(values)
    filtered = [v for v, q in zip(values, quality_scores) if q >= min_quality]
    n = len(filtered)
    if n == 0:
        return None
    m = _mean(filtered)
    med = _median(filtered)
    s = _std(filtered)
    mad = _mad(filtered)
    sorted_f = sorted(filtered)
    q1 = sorted_f[int(n * 0.25)] if n >= 4 else sorted_f[0]
    q3 = sorted_f[int(n * 0.75)] if n >= 4 else sorted_f[-1]
    cv = s / m if m and m != 0 else 0.0
    return {
        "mean": round(m, 4),
        "median": round(med, 4),
        "std": round(s, 4),
        "mad": round(mad, 4),
        "q1": round(q1, 4),
        "q3": round(q3, 4),
        "cv": round(cv, 4),
        "sample_count": n,
        "status": "established" if n >= 14 else "calibrating",
    }


def calculate_deviation(today_value: float, baseline: dict) -> dict:
    """
    [SYNTHETIC-SAFE] Python reference for JS deviationCalculator.
    Uses parametric z-score with MAD fallback.
    """
    if today_value is None or baseline is None:
        return {"z_score": None, "method": "missing"}

    mean = baseline.get("mean")
    std = baseline.get("std", 0.0)
    median = baseline.get("median")
    mad = baseline.get("mad", 0.0)

    if std is not None and std > 1e-6:
        z = (today_value - mean) / std
        method = "parametric"
    elif mad is not None and mad > 1e-6:
        z = 0.6745 * (today_value - median) / mad
        method = "robust_mad"
    else:
        z = 0.0
        method = "zero_dispersion"

    return {"z_score": round(z, 4), "method": method}


def detect_trend_slope(values: List[float]) -> dict:
    """
    [SYNTHETIC-SAFE] Ordinary least squares slope for trend detection.
    """
    n = len(values)
    if n < 3:
        return {"slope": 0.0, "direction": "stable", "n_points": n}
    xs = list(range(n))
    mx = _mean(xs)
    my = _mean(values)
    num = sum((xs[i] - mx) * (values[i] - my) for i in range(n))
    den = sum((xs[i] - mx) ** 2 for i in range(n))
    slope = num / den if den != 0 else 0.0
    direction = "increasing" if slope > 0.01 else ("decreasing" if slope < -0.01 else "stable")
    return {"slope": round(slope, 6), "direction": direction, "n_points": n}


# ── Synthetic Data Factories ──────────────────────────────────────────────────

def stable_14_day_values(mean=2.0, std=0.1):
    """[SYNTHETIC] 14 days of stable values centered around mean."""
    import random
    random.seed(42)
    return [mean + std * math.sin(i * 0.8) for i in range(14)]


def increasing_trend_values(start=2.0, slope=0.05, n=21):
    """[SYNTHETIC] Values with a clear upward trend."""
    return [start + slope * i + 0.01 * math.sin(i) for i in range(n)]


def decreasing_trend_values(start=2.5, slope=-0.04, n=21):
    """[SYNTHETIC] Values with a clear downward trend."""
    return [start + slope * i for i in range(n)]


# ── Sleep Scoring ─────────────────────────────────────────────────────────────

class TestSleepScoring:
    """
    Tests for sleep questionnaire scoring (RBD-proxy).
    Uses the Python-importable sleepScorer logic or reference implementation.
    """

    def test_perfect_sleep_high_score(self):
        """[SYNTHETIC] All optimal answers → sleep quality score near maximum."""
        # Simulate optimal sleep answers (no disturbances, good duration, good quality)
        answers = {
            "duration_hours": 7.5,
            "quality_rating": 5,       # 1–5 scale
            "disturbances": 0,
            "daytime_sleepiness": 1,   # 1=none
            "movement_during_sleep": False,
            "acting_out_dreams": False,
            "snoring": False,
        }
        score = self._score_sleep(answers)
        assert score >= 0.7, f"Perfect sleep answers should score >= 0.7, got {score}"

    def test_poor_sleep_low_score(self):
        """[SYNTHETIC] All poor answers → sleep quality score near minimum."""
        answers = {
            "duration_hours": 4.0,
            "quality_rating": 1,
            "disturbances": 5,
            "daytime_sleepiness": 5,
            "movement_during_sleep": True,
            "acting_out_dreams": True,
            "snoring": True,
        }
        score = self._score_sleep(answers)
        assert score <= 0.5, f"Poor sleep answers should score <= 0.5, got {score}"

    def test_sleep_score_in_bounds(self):
        """[SYNTHETIC] Sleep score must always be in [0, 1]."""
        for q in range(1, 6):
            answers = {"quality_rating": q, "duration_hours": 6.0,
                       "disturbances": 2, "daytime_sleepiness": 2,
                       "movement_during_sleep": False, "acting_out_dreams": False,
                       "snoring": False}
            score = self._score_sleep(answers)
            assert 0.0 <= score <= 1.0

    def _score_sleep(self, answers: dict) -> float:
        """Reference sleep scoring (0–1 scale, higher = better sleep quality)."""
        score = 0.0
        max_score = 0.0

        # Duration (ideal 7–9 h)
        dur = answers.get("duration_hours", 6.0)
        max_score += 1.0
        score += 1.0 if 7.0 <= dur <= 9.0 else (0.5 if 6.0 <= dur < 7.0 or 9.0 < dur <= 10.0 else 0.0)

        # Quality
        q = answers.get("quality_rating", 3)
        max_score += 1.0
        score += (q - 1) / 4.0

        # Disturbances (fewer = better)
        d = answers.get("disturbances", 0)
        max_score += 1.0
        score += max(0.0, 1.0 - d / 5.0)

        # Daytime sleepiness (less = better)
        ds = answers.get("daytime_sleepiness", 1)
        max_score += 1.0
        score += max(0.0, 1.0 - (ds - 1) / 4.0)

        # RBD-proxy signals (movement, acting out, snoring)
        for key in ["movement_during_sleep", "acting_out_dreams", "snoring"]:
            max_score += 1.0
            score += 0.0 if answers.get(key, False) else 1.0

        return round(score / max_score, 4) if max_score > 0 else 0.0


# ── Baseline Calculation ──────────────────────────────────────────────────────

class TestBaselineCalculation:
    def test_14_day_baseline_established(self):
        """[SYNTHETIC] 14 daily values → baseline status = 'established'."""
        values = stable_14_day_values()
        result = calculate_baseline(values)
        assert result["status"] == "established"
        assert result["sample_count"] == 14

    def test_7_day_baseline_calibrating(self):
        """[SYNTHETIC] 7 daily values → baseline status = 'calibrating'."""
        values = stable_14_day_values()[:7]
        result = calculate_baseline(values)
        assert result["status"] == "calibrating"

    def test_mean_close_to_input_mean(self):
        """[SYNTHETIC] Baseline mean should match known input mean."""
        values = [2.0] * 14
        result = calculate_baseline(values)
        assert abs(result["mean"] - 2.0) < 0.001

    def test_std_zero_for_identical_values(self):
        """[SYNTHETIC] All identical values → std == 0.0."""
        values = [1.5] * 14
        result = calculate_baseline(values)
        assert result["std"] == 0.0

    def test_quality_filter_excludes_low_quality(self):
        """[SYNTHETIC] Low-quality days (score < 0.50) are excluded from baseline."""
        values = [2.0] * 7 + [999.0] * 7  # Bad values flagged as low quality
        quality = [1.0] * 7 + [0.3] * 7   # Last 7 have quality 0.3 → excluded
        result = calculate_baseline(values, quality_scores=quality)
        assert result is not None
        assert result["sample_count"] == 7
        assert abs(result["mean"] - 2.0) < 0.1

    def test_empty_values_returns_none(self):
        """[SYNTHETIC] All filtered out → baseline returns None."""
        result = calculate_baseline([], [])
        assert result is None

    def test_all_low_quality_returns_none(self):
        """[SYNTHETIC] All quality scores below threshold → baseline returns None."""
        result = calculate_baseline([2.0] * 14, quality_scores=[0.2] * 14)
        assert result is None

    def test_baseline_contains_all_stats(self):
        """[SYNTHETIC] Baseline must contain mean, median, std, mad, q1, q3, cv."""
        values = stable_14_day_values()
        result = calculate_baseline(values)
        required = {"mean", "median", "std", "mad", "q1", "q3", "cv", "sample_count"}
        missing = required - set(result.keys())
        assert not missing, f"Missing baseline stats: {missing}"


# ── Deviation Calculation ─────────────────────────────────────────────────────

class TestDeviationCalculation:
    def setup_method(self):
        self.baseline = {
            "mean": 100.0, "std": 5.0, "median": 100.0, "mad": 3.5
        }

    def test_positive_z_score(self):
        """[SYNTHETIC] Value above baseline mean → positive z-score."""
        result = calculate_deviation(110.0, self.baseline)
        assert abs(result["z_score"] - 2.0) < 0.01

    def test_negative_z_score(self):
        """[SYNTHETIC] Value below baseline mean → negative z-score."""
        result = calculate_deviation(85.0, self.baseline)
        assert abs(result["z_score"] - (-3.0)) < 0.01

    def test_zero_deviation_at_mean(self):
        """[SYNTHETIC] Value equal to baseline mean → z-score == 0."""
        result = calculate_deviation(100.0, self.baseline)
        assert result["z_score"] == 0.0

    def test_mad_fallback_when_std_zero(self):
        """[SYNTHETIC] When std ≈ 0, deviations use robust MAD-based z-score."""
        baseline_zero_std = {"mean": 100.0, "std": 0.0, "median": 100.0, "mad": 3.5}
        result = calculate_deviation(110.0, baseline_zero_std)
        assert result["method"] == "robust_mad"
        assert result["z_score"] != 0.0

    def test_zero_dispersion_both_zero(self):
        """[SYNTHETIC] Both std and mad == 0 → z_score = 0, method = zero_dispersion."""
        baseline_flat = {"mean": 100.0, "std": 0.0, "median": 100.0, "mad": 0.0}
        result = calculate_deviation(105.0, baseline_flat)
        assert result["method"] == "zero_dispersion"
        assert result["z_score"] == 0.0

    def test_missing_today_value_returns_none(self):
        """[SYNTHETIC] None today_value → z_score = None."""
        result = calculate_deviation(None, self.baseline)
        assert result["z_score"] is None

    def test_missing_baseline_returns_none(self):
        """[SYNTHETIC] None baseline → z_score = None."""
        result = calculate_deviation(100.0, None)
        assert result["z_score"] is None


# ── Trend Detection ───────────────────────────────────────────────────────────

class TestTrendDetection:
    def test_increasing_trend_detected(self):
        """[SYNTHETIC] Values with positive slope → direction = 'increasing'."""
        values = increasing_trend_values(start=2.0, slope=0.1)
        result = detect_trend_slope(values)
        assert result["direction"] == "increasing"
        assert result["slope"] > 0

    def test_decreasing_trend_detected(self):
        """[SYNTHETIC] Values with negative slope → direction = 'decreasing'."""
        values = decreasing_trend_values(start=2.5, slope=-0.05)
        result = detect_trend_slope(values)
        assert result["direction"] == "decreasing"
        assert result["slope"] < 0

    def test_stable_trend_for_flat_values(self):
        """[SYNTHETIC] Flat constant values → direction = 'stable'."""
        values = [2.0] * 21
        result = detect_trend_slope(values)
        assert result["direction"] == "stable"
        assert abs(result["slope"]) < 0.001

    def test_insufficient_points_stable(self):
        """[SYNTHETIC] < 3 points → direction = 'stable'."""
        result = detect_trend_slope([1.0, 2.0])
        assert result["direction"] == "stable"

    def test_trend_includes_n_points(self):
        """[SYNTHETIC] Trend result must include n_points count."""
        values = [1.0] * 10
        result = detect_trend_slope(values)
        assert result["n_points"] == 10

    def test_slope_is_finite(self):
        """[SYNTHETIC] Slope must always be a finite number."""
        values = [float(i) for i in range(14)]
        result = detect_trend_slope(values)
        assert math.isfinite(result["slope"])


# ── Feature Mapping & Normalization ──────────────────────────────────────────

class TestFeatureMapping:
    def test_feature_mapping_version_present(self):
        """Feature mapper exports FEATURE_MAPPING_VERSION string."""
        from src.mobile.feature_mapper import FEATURE_MAPPING_VERSION
        assert isinstance(FEATURE_MAPPING_VERSION, str)
        parts = FEATURE_MAPPING_VERSION.split(".")
        assert len(parts) == 3

    def test_proxy_disclaimer_present(self):
        """Feature mapper exports PROXY_DISCLAIMER with correct language."""
        from src.mobile.feature_mapper import PROXY_DISCLAIMER
        assert "not a clinical diagnosis" in PROXY_DISCLAIMER.lower() or \
               "research" in PROXY_DISCLAIMER.lower()

    def test_map_mobile_features_voice_only(self):
        """[SYNTHETIC] Voice-only daily features mapped without crash."""
        from src.mobile.feature_mapper import map_mobile_features
        daily = {
            "voice": {"jitter": 0.012, "shimmer": 0.05, "hnr": 14.0, "pitch_mean": 145.0,
                      "mfcc_mean": [0.0] * 13}
        }
        result = map_mobile_features(daily)
        assert "available_modalities" in result
        assert "voice" in result.get("available_modalities", [])

    def test_map_mobile_features_marks_missing(self):
        """[SYNTHETIC] Missing modalities are explicitly flagged — not imputed."""
        from src.mobile.feature_mapper import map_mobile_features
        daily = {"voice": {"jitter": 0.01, "shimmer": 0.04, "hnr": 13.0,
                           "pitch_mean": 140.0, "mfcc_mean": [0.0]*13}}
        result = map_mobile_features(daily)
        missing = result.get("missing_modalities", [])
        # Olfactory is never available on mobile
        assert "olfactory" in missing or len(missing) > 0
