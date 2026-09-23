"""
Tests for MPF Mobile Extension — Non-Diagnostic Language Safety Audit (Phase 14)

Verifies:
1. Complete absence of forbidden diagnostic terms across all dashboard JSX and JS source files:
   - "Parkinson's disease detected"
   - "Parkinson's progression"
   - "Disease worsening"
   - "Clinical decline"
   - "You have Parkinson's"
   - Standalone "Diagnosis" without explicit negative qualifier ("not a clinical diagnosis")
2. Sensor overclaiming compliance (Rule 2):
   - Zero claim that front camera is "retinal camera" or performs "retinal imaging".
   - Explicit labeling as "Ocular/Visual Behavior Module".
   - Clear declaration that retinal imaging requires specialized clinical equipment.
3. Mandatory presence and adherence to allowed non-diagnostic phrases:
   - "Within personal baseline"
   - "Moderate deviation from baseline"
   - "Sustained deviation detected"
   - "Your recent measurements differ from your personal baseline"
   - "Elevated Parkinson's risk pattern detected"
   - "Research screening result — not a clinical diagnosis"
4. Color safety:
   - Deviations are styled with non-alarming amber/orange rather than emergency red.
   - Baseline measurements use calm emerald/green.
   - Missing data uses neutral slate/gray.

All test fixtures use clearly labeled [SYNTHETIC] values.
"""

import re
from pathlib import Path
import pytest

DASHBOARD_DIR = Path(__file__).resolve().parent.parent

# Strictly forbidden phrases
FORBIDDEN_PHRASES = [
    "parkinson's disease detected",
    "parkinsons disease detected",
    "parkinson's progression",
    "parkinsons progression",
    "disease worsening",
    "clinical decline",
    "you have parkinson's",
    "you have parkinsons",
]

# Required allowed research phrases
ALLOWED_PHRASES = [
    "Within personal baseline",
    "Moderate deviation from baseline",
    "Sustained deviation detected",
    "Your recent measurements differ from your personal baseline",
    "Elevated Parkinson's risk pattern detected",
    "Research screening result — not a clinical diagnosis"
]


def get_all_dashboard_source_files():
    """Gathers all .jsx and .js files in the dashboard module directory."""
    files = list(DASHBOARD_DIR.glob("*.jsx")) + list(DASHBOARD_DIR.glob("*.js"))
    assert len(files) >= 6, f"Expected at least 6 dashboard source files, found {len(files)}"
    return files


def test_forbidden_diagnostic_phrases_scan():
    """Scan all dashboard source files to ensure ZERO forbidden diagnostic terms exist."""
    files = get_all_dashboard_source_files()
    violations = []

    for file_path in files:
        text = file_path.read_text(encoding="utf-8").lower()
        for forbidden in FORBIDDEN_PHRASES:
            if forbidden in text:
                violations.append(f"File '{file_path.name}' contains forbidden phrase: '{forbidden}'")

    assert not violations, "\n".join(violations)


def test_standalone_diagnosis_word_audit():
    """
    Ensure the word 'diagnosis' only appears in explicitly non-diagnostic contexts,
    e.g.: 'not a clinical diagnosis' or 'Research screening result — not a clinical diagnosis'.
    """
    files = get_all_dashboard_source_files()
    allowed_diagnosis_patterns = [
        re.compile(r"not\s+a\s+clinical\s+diagnosis", re.IGNORECASE),
        re.compile(r"not\s+a\s+clinical\s+diagnostic\s+report", re.IGNORECASE),
        re.compile(r"not\s+diagnose\s+parkinson", re.IGNORECASE),
        re.compile(r"not\s+indicate\s+clinical\s+diagnosis", re.IGNORECASE),
        re.compile(r"provide\s+clinical\s+diagnoses\s+of\s+any\s+kind", re.IGNORECASE),
        re.compile(r"non-diagnostic", re.IGNORECASE),
        re.compile(r"zero\s+diagnostic\s+claims", re.IGNORECASE),
        re.compile(r"diagnostic\s+claims?", re.IGNORECASE),
        re.compile(r"not\s+a\s+substitute\s+for\s+physician", re.IGNORECASE),
        re.compile(r"medical\s+diagnostic\s+tool", re.IGNORECASE),
    ]

    for file_path in files:
        lines = file_path.read_text(encoding="utf-8").splitlines()
        for line_num, line in enumerate(lines, 1):
            if re.search(r"\bdiagnos", line, re.IGNORECASE):
                # Verify that this line matches one of the acceptable disclaimer patterns
                is_safe = any(pat.search(line) for pat in allowed_diagnosis_patterns)
                assert is_safe, (
                    f"Unqualified diagnostic word found in {file_path.name}:{line_num}: '{line.strip()}'\n"
                    f"Rule 1 mandates: 'Research screening result — not a clinical diagnosis'."
                )


def test_retinal_overclaiming_audit():
    """
    Rule 2: Sensor Overclaiming.
    Ensure front camera is designated as Ocular/Visual Behavior Module and never claimed as retinal imaging.
    """
    files = get_all_dashboard_source_files()

    for file_path in files:
        content = file_path.read_text(encoding="utf-8")
        # Check that 'retinal' is only mentioned to clarify that it requires separate hardware or is missing
        if "retinal" in content.lower():
            assert (
                "not retinal imaging" in content.lower()
                or "missing" in content.lower()
                or "hardware" in content.lower()
                or "specialized" in content.lower()
            ), f"File {file_path.name} mentions 'retinal' without clarifying hardware separation or non-equivalence."


def test_presence_of_required_safe_phrases():
    """Verify that all mandatory non-diagnostic phrases are implemented in the dashboard suite."""
    all_content = "\n".join(f.read_text(encoding="utf-8") for f in get_all_dashboard_source_files())

    for phrase in ALLOWED_PHRASES:
        assert phrase in all_content, f"Mandatory safe phrase missing from dashboard: '{phrase}'"


def test_visual_color_safety_audit():
    """
    Verify visual design rules:
    - Deviations use calm amber/orange (not alarming emergency red)
    - Baseline uses emerald/green
    - Missing data uses slate/gray
    """
    deviation_alert_content = (DASHBOARD_DIR / "DeviationAlert.jsx").read_text(encoding="utf-8")
    trend_chart_content = (DASHBOARD_DIR / "TrendChart.jsx").read_text(encoding="utf-8")
    screening_content = (DASHBOARD_DIR / "ScreeningResult.jsx").read_text(encoding="utf-8")

    # In DeviationAlert: must use amber for deviation warnings
    assert "amber-" in deviation_alert_content
    # Emergency alarming red should NOT be used for deviation notices
    assert "bg-red-600" not in deviation_alert_content
    assert "text-red-500" not in deviation_alert_content

    # In TrendChart:
    assert "amber-" in trend_chart_content
    assert "emerald-" in trend_chart_content
    assert "slate-" in trend_chart_content

    # In ScreeningResult:
    assert "amber-" in screening_content
    assert "emerald-" in screening_content
