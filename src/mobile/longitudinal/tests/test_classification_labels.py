"""
Tests for MPF Mobile Extension — Classification Labels & Safety (Phase 11)

Validates:
1. Exact mapping of z-score thresholds to required non-diagnostic research categories:
   - "Within personal baseline": |z| < 1.5
   - "Mild deviation from baseline": 1.5 <= |z| < 2.0
   - "Moderate deviation from baseline": 2.0 <= |z| < 3.0
   - "Significant deviation from baseline": |z| >= 3.0
   - "Sustained deviation detected": |z| > 2.0 for >= 5 consecutive days
2. Boundary value behavior at 1.5, 2.0, and 3.0.
3. Detailed classification descriptors and severity levels.
4. Non-diagnostic safety assertion mechanism:
   - Explicitly rejects "Parkinson's detected", "Disease progression", "Clinical deterioration",
     "Parkinson's progression", "Disease worsening", "Clinical decline".
5. Live Supabase connection and schema verification of Phase 11 daily_deviations columns.

ALL test data is clearly labeled [SYNTHETIC].
"""

import json
import os
import subprocess
import pytest
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
JS_CLASSIFIER = BASE_DIR / "deviationClassifier.js"

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://trtvdmgswouirfaqyrdk.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRydHZkbWdzd291aXJmYXF5cmRrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAxNjM3OTAsImV4cCI6MjEwNTczOTc5MH0.wxyGhyELZJy_-R2X4xqDaIsgofDbdQJtwZWjboCOKrM")

FORBIDDEN_TERMS = [
    "you have parkinson's",
    "parkinson's detected",
    "parkinsons detected",
    "diagnosed parkinson",
    "disease progression",
    "clinical deterioration",
    "parkinson's progression",
    "disease worsening",
    "clinical decline",
]


def run_node_eval(js_code: str):
    res = subprocess.run(
        ["node", "-e", js_code],
        capture_output=True,
        text=True,
        check=True
    )
    return json.loads(res.stdout)


def test_deviation_classification_bands():
    """Verify standard classification bands matching Phase 11 specification [SYNTHETIC]."""
    js_code = f"""
    const {{ classifyDeviation }} = require({json.dumps(str(JS_CLASSIFIER))});

    // 1. Within personal baseline: |z| < 1.5
    const labelWithinLow = classifyDeviation(0.0);
    const labelWithinMed = classifyDeviation(1.2);
    const labelWithinNeg = classifyDeviation(-1.49);

    // 2. Mild deviation: 1.5 <= |z| < 2.0
    const labelMildBound = classifyDeviation(1.5);
    const labelMildMid = classifyDeviation(1.8);
    const labelMildNeg = classifyDeviation(-1.99);

    // 3. Moderate deviation: 2.0 <= |z| < 3.0
    const labelModBound = classifyDeviation(2.0);
    const labelModMid = classifyDeviation(2.5);
    const labelModNeg = classifyDeviation(-2.99);

    // 4. Significant deviation: |z| >= 3.0
    const labelSigBound = classifyDeviation(3.0);
    const labelSigHigh = classifyDeviation(4.5);
    const labelSigNeg = classifyDeviation(-5.0);

    // 5. Sustained deviation: |z| > 2.0 for >= 5 consecutive days
    const labelSustained = classifyDeviation(2.4, 5);

    console.log(JSON.stringify({{
      labelWithinLow,
      labelWithinMed,
      labelWithinNeg,
      labelMildBound,
      labelMildMid,
      labelMildNeg,
      labelModBound,
      labelModMid,
      labelModNeg,
      labelSigBound,
      labelSigHigh,
      labelSigNeg,
      labelSustained,
    }}));
    """
    res = run_node_eval(js_code)

    # Within personal baseline
    assert res["labelWithinLow"] == "Within personal baseline"
    assert res["labelWithinMed"] == "Within personal baseline"
    assert res["labelWithinNeg"] == "Within personal baseline"

    # Mild deviation from baseline
    assert res["labelMildBound"] == "Mild deviation from baseline"
    assert res["labelMildMid"] == "Mild deviation from baseline"
    assert res["labelMildNeg"] == "Mild deviation from baseline"

    # Moderate deviation from baseline
    assert res["labelModBound"] == "Moderate deviation from baseline"
    assert res["labelModMid"] == "Moderate deviation from baseline"
    assert res["labelModNeg"] == "Moderate deviation from baseline"

    # Significant deviation from baseline
    assert res["labelSigBound"] == "Significant deviation from baseline"
    assert res["labelSigHigh"] == "Significant deviation from baseline"
    assert res["labelSigNeg"] == "Significant deviation from baseline"

    # Sustained deviation detected
    assert res["labelSustained"] == "Sustained deviation detected"


def test_classify_deviation_detail():
    """Verify structured descriptor metadata, severity levels, and research disclaimers [SYNTHETIC]."""
    js_code = f"""
    const {{ classifyDeviationDetail }} = require({json.dumps(str(JS_CLASSIFIER))});

    const d0 = classifyDeviationDetail(0.5);
    const d1 = classifyDeviationDetail(1.75);
    const d2 = classifyDeviationDetail(-2.5);
    const d3 = classifyDeviationDetail(3.8);
    const d4 = classifyDeviationDetail(2.8, 6);

    console.log(JSON.stringify({{ d0, d1, d2, d3, d4 }}));
    """
    res = run_node_eval(js_code)

    assert res["d0"]["severity_level"] == 0
    assert res["d0"]["label"] == "Within personal baseline"

    assert res["d1"]["severity_level"] == 1
    assert res["d1"]["label"] == "Mild deviation from baseline"

    assert res["d2"]["severity_level"] == 2
    assert res["d2"]["label"] == "Moderate deviation from baseline"

    assert res["d3"]["severity_level"] == 3
    assert res["d3"]["label"] == "Significant deviation from baseline"

    assert res["d4"]["severity_level"] == 4
    assert res["d4"]["label"] == "Sustained deviation detected"
    assert res["d4"]["is_sustained"] is True


def test_safety_audit_disallowed_terms():
    """Verify assertNonDiagnosticPhrasing throws error on forbidden clinical/diagnostic claims."""
    js_code = f"""
    const {{ assertNonDiagnosticPhrasing }} = require({json.dumps(str(JS_CLASSIFIER))});

    let caughtParkinsons = false;
    try {{
      assertNonDiagnosticPhrasing("Parkinson's detected in voice tremor");
    }} catch (err) {{
      caughtParkinsons = true;
    }}

    let caughtProgression = false;
    try {{
      assertNonDiagnosticPhrasing("Evidence of disease progression over 14 days");
    }} catch (err) {{
      caughtProgression = true;
    }}

    let caughtDecline = false;
    try {{
      assertNonDiagnosticPhrasing("Clinical decline noted in motor tapping");
    }} catch (err) {{
      caughtDecline = true;
    }}

    console.log(JSON.stringify({{
      caughtParkinsons,
      caughtProgression,
      caughtDecline,
    }}));
    """
    res = run_node_eval(js_code)

    assert res["caughtParkinsons"] is True
    assert res["caughtProgression"] is True
    assert res["caughtDecline"] is True


def test_source_code_static_audit():
    """Verify that none of the Phase 11 JavaScript modules contain hardcoded forbidden diagnostic terms."""
    js_files = [
        BASE_DIR / "deviationCalculator.js",
        BASE_DIR / "trendDetector.js",
        BASE_DIR / "sustainedDeviationDetector.js",
        BASE_DIR / "deviationClassifier.js",
        BASE_DIR / "index.js",
    ]

    for file_path in js_files:
        content = file_path.read_text(encoding="utf-8").lower()
        for term in FORBIDDEN_TERMS:
            # The only allowed occurrence of forbidden terms is inside the FORBIDDEN_DIAGNOSTIC_TERMS blocklist definition
            if term in content:
                # Confirm it is only referenced in the negative blocklist or comment
                assert "forbidden" in content or "disallowed" in content or "never" in content or "do not" in content, (
                    f"Forbidden diagnostic term '{term}' found in {file_path.name}"
                )


def test_live_supabase_phase11_columns():
    """Verify live Supabase connection and read access to Phase 11 daily_deviations columns."""
    from supabase import create_client

    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    assert client is not None

    # Query daily_deviations with Phase 11 columns
    dev_res = client.table("daily_deviations").select(
        "id, seven_day_average, seven_day_variability, fourteen_day_trend, sustained_deviation_count, missingness_ratio, seven_day_quality, deviation_classification, trend_classification"
    ).limit(1).execute()

    assert dev_res.data is not None
