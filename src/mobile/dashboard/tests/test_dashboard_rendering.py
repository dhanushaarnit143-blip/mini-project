"""
Tests for MPF Mobile Extension — Dashboard Rendering & Structure (Phase 14)

Verifies:
1. All 6 core dashboard sections implemented and structured properly:
   - Section 1: Today's Summary (modality completion, quality scores, status indicator)
   - Section 2: Personal Trends (14/30/90 day ranges, baseline band mean ± 1 std, current marker)
   - Section 3: Deviation Alerts (severity levels, single day / sustained duration, non-diagnostic text)
   - Section 4: Research Screening Result (fusion risk score, available/missing modalities, disclaimer, explainability)
   - Section 5: Data Quality (adherence percentage, missing patterns, modality breakdown)
   - Section 6: Privacy & Data Controls (granular consent, export data, deletion confirmation, transparency)
2. Mathematical calculations in DashboardDataService:
   - Baseline bands (mean ± 1 std)
   - Deviation classifications across z-score boundaries
   - Adherence rate and streak calculations
3. Mobile responsive structure and CSS layout constraints.
4. Component exports and interface integrity.

All test fixtures use clearly labeled [SYNTHETIC] values.
"""

import json
import os
import re
import subprocess
from pathlib import Path
import pytest

DASHBOARD_DIR = Path(__file__).resolve().parent.parent
TESTS_DIR = Path(__file__).resolve().parent

REQUIRED_JSX_FILES = [
    "DashboardScreen.jsx",
    "TrendChart.jsx",
    "DeviationAlert.jsx",
    "ScreeningResult.jsx",
    "DataQualityPanel.jsx",
    "PrivacyControls.jsx",
]


def read_component(filename: str) -> str:
    path = DASHBOARD_DIR / filename
    assert path.exists(), f"Expected file {filename} does not exist in {DASHBOARD_DIR}"
    return path.read_text(encoding="utf-8")


def run_node_eval(js_code: str) -> dict:
    """Evaluates JavaScript code snippet using Node.js and parses JSON output."""
    res = subprocess.run(
        ["node", "-e", js_code],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True
    )
    return json.loads(res.stdout)


# =========================================================================
# File & Export Verification
# =========================================================================

def test_dashboard_files_exist():
    """Verify all deliverables specified in Phase 14 exist in src/mobile/dashboard/."""
    for filename in REQUIRED_JSX_FILES:
        path = DASHBOARD_DIR / filename
        assert path.exists(), f"Missing required file: {filename}"
        assert path.stat().st_size > 500, f"File {filename} is suspiciously small."


def test_index_exports():
    """Verify index.js exports all dashboard components and constants."""
    index_content = read_component("index.js")
    expected_exports = [
        "DashboardScreen",
        "TrendChart",
        "DeviationAlert",
        "ScreeningResult",
        "DataQualityPanel",
        "PrivacyControls",
        "DELETION_CONFIRMATION_PHRASE"
    ]
    for exp in expected_exports:
        assert exp in index_content, f"index.js must export {exp}"


# =========================================================================
# Section 1: Today's Summary Verification
# =========================================================================

def test_section1_today_summary_structure():
    """Verify Section 1 in DashboardScreen includes task completion, quality scores, and quick baseline status."""
    content = read_component("DashboardScreen.jsx")
    assert "Section 1: Today's Summary" in content or "section-today-summary" in content

    # Check for completion status & quality
    assert "Completed" in content
    assert "Quality" in content

    # Check for quick status indicators
    assert "Within personal baseline" in content
    assert "Deviation noted" in content

    # Check modality task names
    for mod in ["Voice", "Motor", "Typing", "Visual", "Sleep"]:
        assert mod in content, f"Today's summary must include {mod} task"


# =========================================================================
# Section 2: Personal Trends Verification
# =========================================================================

def test_section2_personal_trends_structure():
    """Verify Section 2 TrendChart contains 14/30/90 day selector, baseline envelope (mean ± 1 std), and markers."""
    content = read_component("TrendChart.jsx")

    # Time range selector
    for r in ["14d", "30d", "90d"]:
        assert r in content, f"TrendChart must support time range {r}"

    # Baseline envelope and mean
    assert "mean ± 1 std" in content or "mean ± 1 standard deviation" in content.lower()
    assert "baselineMean" in content
    assert "baselineStd" in content

    # Current value callout
    assert "currentValue" in content
    assert "Latest Observation" in content

    # Required safe labels
    assert "Within personal baseline" in content
    assert "Moderate deviation from baseline" in content

    # SVG chart elements
    assert "<svg" in content
    assert "rect" in content  # Baseline band
    assert "polyline" in content  # Trend line
    assert "circle" in content  # Data points


# =========================================================================
# Section 3: Deviation Alerts Verification
# =========================================================================

def test_section3_deviation_alerts_structure():
    """Verify Section 3 DeviationAlert handles mild, moderate, significant severity and durations."""
    content = read_component("DeviationAlert.jsx")

    # Severities
    assert "Mild deviation from baseline" in content
    assert "Moderate deviation from baseline" in content
    assert "Significant deviation from baseline" in content

    # Durations
    assert "Sustained deviation detected" in content
    assert "Single day observation" in content

    # Mandatory Safe Summary phrasing
    assert "Your recent measurements differ from your personal baseline" in content

    # Acknowledge function
    assert "onAcknowledge" in content


# =========================================================================
# Section 4: Research Screening Result Verification
# =========================================================================

def test_section4_screening_result_structure():
    """Verify Section 4 ScreeningResult handles risk estimates, modality lists, and mandatory disclaimer."""
    content = read_component("ScreeningResult.jsx")

    # Overall risk estimate & models
    assert "riskScore" in content
    assert "Fusion Risk Pattern Index" in content or "risk" in content.lower()

    # Modality coverage
    assert "availableModalities" in content
    assert "missingModalities" in content
    assert "Voice Acoustic Module" in content
    assert "Motor & Gait Module" in content

    # Non-overclaiming for camera (Rule 2)
    assert "Ocular/Visual Behavior Module" in content
    assert "NOT retinal imaging" in content or "Not retinal imaging" in content

    # Explainability breakdown
    assert "Explainability" in content or "attention" in content.lower() or "weight" in content.lower()
    assert "modalityWeights" in content

    # Mandatory Disclaimer
    assert "Research screening result — not a clinical diagnosis" in content


# =========================================================================
# Section 5: Data Quality Verification
# =========================================================================

def test_section5_data_quality_structure():
    """Verify Section 5 DataQualityPanel presents adherence rate, quality scores, and missing data pattern."""
    content = read_component("DataQualityPanel.jsx")

    # Adherence
    assert "Protocol Adherence" in content
    assert "adherenceRatePct" in content
    assert "Streak" in content

    # Modality quality breakdown
    assert "typing" in content
    assert "voice" in content
    assert "motor" in content
    assert "visual" in content
    assert "sleep" in content

    # Missing data pattern matrix
    assert "14-Day Collection Pattern" in content or "last14DaysMatrix" in content
    assert "Missing" in content
    assert "Quality" in content


# =========================================================================
# Section 6: Privacy & Data Controls Verification
# =========================================================================

def test_section6_privacy_controls_structure():
    """Verify Section 6 PrivacyControls includes consent toggles, export, deletion, and transparency guide."""
    content = read_component("PrivacyControls.jsx")

    # Consent toggles
    assert "localConsents" in content
    assert "handleToggleConsent" in content
    assert "data_collection" in content

    # Export functionality (GDPR Art. 20)
    assert "handleExport" in content or "onExportData" in content
    assert "Export My Data" in content

    # Deletion functionality (GDPR Art. 17)
    assert "DELETE MY RESEARCH DATA" in content
    assert "handleDeleteConfirm" in content or "onDeleteData" in content

    # Transparency modal
    assert "What is Collected" in content
    assert "Strictly NEVER Collected" in content or "Zero keystroke characters" in content
    assert "pseudonymousId" in content


# =========================================================================
# Dashboard Data Calculations (Evaluated in Node.js)
# =========================================================================

def test_dashboard_service_calculations_in_node():
    """Execute mathematical assertions in Node.js on DashboardDataService [SYNTHETIC]."""
    service_uri = (DASHBOARD_DIR / "dashboardDataService.js").as_uri()
    js_code = f"""
    import('{service_uri}').then(m => {{
        const Svc = m.DashboardDataService;

        // 1. Test Baseline Band
        const band = Svc.computeBaselineBand(100.0, 10.0);

        // 2. Test Classification Thresholds
        const normal = Svc.classifyDeviation(105.0, 100.0, 10.0);     // z = +0.5
        const mild = Svc.classifyDeviation(118.0, 100.0, 10.0);       // z = +1.8
        const moderate = Svc.classifyDeviation(125.0, 100.0, 10.0);   // z = +2.5
        const significant = Svc.classifyDeviation(135.0, 100.0, 10.0);// z = +3.5

        // 3. Test Adherence
        const adh = Svc.calculateAdherence(12, 14);

        // 4. Test Screening Result Formatting
        const resLow = Svc.formatScreeningResult(0.25);
        const resHigh = Svc.formatScreeningResult(0.72);

        console.log(JSON.stringify({{
            band,
            normal,
            mild,
            moderate,
            significant,
            adh,
            resLow,
            resHigh
        }}));
    }}).catch(err => {{
        console.error(err);
        process.exit(1);
    }});
    """
    result = run_node_eval(js_code)

    # 1. Baseline Band
    assert result["band"]["lowerBound"] == 90.0
    assert result["band"]["upperBound"] == 110.0

    # 2. Classifications
    assert result["normal"]["label"] == "Within personal baseline"
    assert result["normal"]["severity"] == "normal"

    assert result["mild"]["label"] == "Mild deviation from baseline"
    assert result["mild"]["severity"] == "mild"

    assert result["moderate"]["label"] == "Moderate deviation from baseline"
    assert result["moderate"]["severity"] == "moderate"

    assert result["significant"]["label"] == "Significant deviation from baseline"
    assert result["significant"]["severity"] == "significant"

    # 3. Adherence
    assert result["adh"]["adherenceRatePct"] == 86
    assert result["adh"]["isTargetMet"] is True

    # 4. Screening Result
    assert result["resLow"]["patternLabel"] == "Within personal baseline"
    assert result["resLow"]["disclaimer"] == "Research screening result — not a clinical diagnosis"
    assert result["resHigh"]["patternLabel"] == "Elevated Parkinson's risk pattern detected"
    assert len(result["resHigh"]["missingModalities"]) == 2


# =========================================================================
# Mobile Responsiveness & Container Constraints
# =========================================================================

def test_mobile_responsiveness_classes():
    """Verify that top-level dashboard container applies responsive constraints suitable for mobile screens."""
    content = read_component("DashboardScreen.jsx")

    # Mobile viewport container constraint
    assert "max-w-md" in content, "DashboardScreen must have mobile max-width container (max-w-md)"
    assert "mx-auto" in content, "DashboardScreen container must be centered"
    assert "min-h-screen" in content, "DashboardScreen must fill screen height"


def test_calibration_state_handling():
    """Verify ScreeningResult.jsx renders calibration progress message when baselineStatus is calibrating."""
    content = read_component("ScreeningResult.jsx")
    assert "baselineStatus === 'calibrating'" in content or "calibrating" in content
    assert "Baseline Calibration Active" in content
    assert "Zero population-level comparisons" in content or "withheld until your personal normal" in content
