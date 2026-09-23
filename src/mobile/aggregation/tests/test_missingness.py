"""
Tests for MPF Mobile Extension — Missingness Tracking Engine (Phase 9)

Validates:
1. Complete tracking of all 5 mobile modalities: typing, voice, motor, visual, sleep.
2. Low-quality exclusion: modalities with only low-quality sessions are tracked as
   'low_quality' and excluded from 'available_modalities'.
3. Completeness ratio calculation (available / 5.0).
4. Strict enforcement of NON-IMPUTATION: missing modalities must remain null and
   cannot be filled with default or synthetic numbers.
5. Dual parity test between Python and JavaScript (missingnessTracker.js).

ALL test data is clearly labeled [SYNTHETIC].
"""

import json
import subprocess
import pytest
from pathlib import Path

JS_MODULE_PATH = Path(__file__).resolve().parents[1] / "missingnessTracker.js"
TRACKED_MODALITIES = ["typing", "voice", "motor", "visual", "sleep"]


def track_missingness_py(modality_evaluations: dict) -> dict:
    """Python reference mirror of trackMissingness."""
    available = []
    missing = []
    low_quality = []
    modality_status = {}

    for mod in TRACKED_MODALITIES:
        ev = modality_evaluations.get(mod, {})
        status = ev.get("status", "missing")
        if status == "valid":
            available.append(mod)
            modality_status[mod] = "available"
        elif status == "low_quality":
            low_quality.append(mod)
            missing.append(mod)
            modality_status[mod] = "low_quality"
        else:
            missing.append(mod)
            modality_status[mod] = "missing"

    ratio = round(len(available) / len(TRACKED_MODALITIES), 2)
    return {
        "available_modalities": available,
        "missing_modalities": missing,
        "low_quality_modalities": low_quality,
        "modality_status": modality_status,
        "completeness_ratio": ratio,
    }


def validate_no_imputation_py(vector: dict):
    """Python reference mirror of validateNoImputation."""
    errors = []
    missing = vector.get("missing_modalities", [])
    available = vector.get("available_modalities", [])

    for m in missing:
        if m in available:
            errors.append(f"Overlap: {m} is in both available and missing")
        val = vector.get(m)
        if val is not None:
            errors.append(f"Imputation violation: {m} has data despite being missing")

    for a in available:
        val = vector.get(a)
        if val is None:
            errors.append(f"Missing data: {a} is marked available but value is None")

    return len(errors) == 0, errors


# ── Python Unit Tests ────────────────────────────────────────────────────────

def test_missingness_tracking_all_available():
    """Verify state when all 5 modalities are valid."""
    evals = {m: {"status": "valid"} for m in TRACKED_MODALITIES}
    res = track_missingness_py(evals)
    assert len(res["available_modalities"]) == 5
    assert len(res["missing_modalities"]) == 0
    assert len(res["low_quality_modalities"]) == 0
    assert res["completeness_ratio"] == 1.0


def test_missingness_tracking_partial_availability():
    """Verify state with 3 available, 2 missing (matching prompt example)."""
    evals = {
        "typing": {"status": "valid"},
        "voice": {"status": "valid"},
        "motor": {"status": "valid"},
        "visual": {"status": "missing"},
        "sleep": {"status": "missing"},
    }
    res = track_missingness_py(evals)
    assert res["available_modalities"] == ["typing", "voice", "motor"]
    assert res["missing_modalities"] == ["visual", "sleep"]
    assert res["completeness_ratio"] == 0.60


def test_missingness_tracking_low_quality_exclusion():
    """Verify modality with all low-quality sessions is excluded from available modalities."""
    evals = {
        "typing": {"status": "valid"},
        "voice": {"status": "low_quality"},
        "motor": {"status": "valid"},
        "visual": {"status": "missing"},
        "sleep": {"status": "missing"},
    }
    res = track_missingness_py(evals)
    assert "voice" in res["low_quality_modalities"]
    assert "voice" in res["missing_modalities"]
    assert "voice" not in res["available_modalities"]
    assert res["available_modalities"] == ["typing", "motor"]
    assert res["completeness_ratio"] == 0.40


def test_strict_non_imputation_enforcement():
    """Verify validator catches any attempted imputation of missing modalities."""
    # [SYNTHETIC] compliant vector with null for missing modalities
    compliant_vector = {
        "available_modalities": ["typing", "voice"],
        "missing_modalities": ["motor", "visual", "sleep"],
        "typing": {"typing_speed": 220},
        "voice": {"jitter": 0.01},
        "motor": None,
        "visual": None,
        "sleep": None,
    }
    valid, errors = validate_no_imputation_py(compliant_vector)
    assert valid is True
    assert len(errors) == 0

    # [SYNTHETIC] non-compliant vector with imputed fake motor data
    imputed_vector = {
        "available_modalities": ["typing", "voice"],
        "missing_modalities": ["motor", "visual", "sleep"],
        "typing": {"typing_speed": 220},
        "voice": {"jitter": 0.01},
        "motor": {"cadence": 105.0}, # VIOLATION: Should be null!
        "visual": None,
        "sleep": None,
    }
    valid, errors = validate_no_imputation_py(imputed_vector)
    assert valid is False
    assert any("Imputation violation: motor" in e for e in errors)


# ── JavaScript Parity Tests (Executing Node.js) ──────────────────────────────

def test_js_missingness_tracker_parity():
    """Verify missingnessTracker.js behaves identically under Node.js."""
    js_test_code = f"""
    const {{ trackMissingness, validateNoImputation }} = require({json.dumps(str(JS_MODULE_PATH))});

    const evals = {{
      typing: {{ status: 'valid' }},
      voice: {{ status: 'valid' }},
      motor: {{ status: 'valid' }},
      visual: {{ status: 'missing' }},
      sleep: {{ status: 'missing' }}
    }};

    const trackerResult = trackMissingness(evals);

    const testVector = {{
      available_modalities: ['typing', 'voice', 'motor'],
      missing_modalities: ['visual', 'sleep'],
      typing: {{ speed: 200 }},
      voice: {{ jitter: 0.02 }},
      motor: {{ cadence: 100 }},
      visual: null,
      sleep: null
    }};

    const validCheck = validateNoImputation(testVector);

    const badVector = Object.assign({{}}, testVector, {{ visual: {{ blink_rate: 15 }} }});
    const badCheck = validateNoImputation(badVector);

    console.log(JSON.stringify({{
      available: trackerResult.available_modalities,
      missing: trackerResult.missing_modalities,
      ratio: trackerResult.completeness_ratio,
      validCheckPass: validCheck.valid,
      badCheckPass: badCheck.valid
    }}));
    """

    res = subprocess.run(
        ["node", "-e", js_test_code],
        capture_output=True,
        text=True,
        check=True
    )
    data = json.loads(res.stdout.strip())
    assert data["available"] == ["typing", "voice", "motor"]
    assert data["missing"] == ["visual", "sleep"]
    assert data["ratio"] == 0.60
    assert data["validCheckPass"] is True
    assert data["badCheckPass"] is False
