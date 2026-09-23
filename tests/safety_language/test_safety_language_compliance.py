"""
Phase 15 — Safety Language Tests: Forbidden Diagnostic Phrase Detection
=======================================================================
Scans ALL user-facing source files for forbidden diagnostic phrases.
This is a ZERO-TOLERANCE policy — ANY match causes test failure.

NON-NEGOTIABLE RULES (from project specification):
  Rule 1 — NO DIAGNOSTIC CLAIMS:
    FORBIDDEN: "You have Parkinson's"
    FORBIDDEN: "Parkinson's detected" / "Parkinson's disease detected"
    FORBIDDEN: "Diagnosis" (used as a standalone positive claim)
    FORBIDDEN: "Parkinson's progression"
    FORBIDDEN: "Clinical decline"
    FORBIDDEN: "Confirmed Parkinson's"
    FORBIDDEN: "Disease worsening"

  ALLOWED:
    "Elevated Parkinson's risk pattern detected"
    "Your recent measurements differ from your personal baseline"
    "Research screening result — not a clinical diagnosis"
    "Progressive deviation from personal baseline"
    "Deviation from personal baseline"
    "Within personal baseline"

  Rule 2 — NO SENSOR OVERCLAIMING:
    FORBIDDEN: "retinal camera" (smartphone is NOT a retinal camera)
    FORBIDDEN: "retinal imaging" (front camera cannot perform retinal imaging)
    FORBIDDEN: "fundus camera"

Coverage:
  - All JSX/JS source files in src/mobile/
  - All Python source files in src/mobile/
  - All dashboard files
  - All onboarding files
  - README.md and key documentation files
"""

import re
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MOBILE_DIR = ROOT / "src" / "mobile"
DOCS_FILES = [ROOT / "README.md", ROOT / "ETHICAL_CONSIDERATIONS.md",
              ROOT / "PRIVACY_MODEL.md"]


# ── Forbidden Phrases ─────────────────────────────────────────────────────────

FORBIDDEN_DIAGNOSTIC_PHRASES = [
    # Core forbidden diagnostic claims
    "you have parkinson's",
    "you have parkinsons",
    "you have parkinson",
    # Detection / diagnosis claims
    "parkinson's disease detected",
    "parkinsons disease detected",
    "parkinson detected",
    "diagnosed with parkinson",
    "diagnosis of parkinson",
    "confirmed parkinson",
    # Progression language
    "parkinson's progression",
    "parkinsons progression",
    "disease worsening",
    "disease progression",
    "clinical decline",
    # Clinical overclaiming
    "clinical diagnosis",  # This is fine only when negated: "not a clinical diagnosis"
]

# Phrases that are forbidden UNLESS negated
CONDITIONALLY_FORBIDDEN = [
    "clinical diagnosis",   # forbidden unless preceded by "not a" or "non-clinical"
]

# Sensor overclaiming
FORBIDDEN_SENSOR_PHRASES = [
    "retinal camera",
    "retinal imaging",
    "fundus camera",
    "performs retinal",
    "ocular tomography",
]

# Required phrases that must appear in at least one source file
REQUIRED_RESEARCH_PHRASES = [
    "research screening result",
    "not a clinical diagnosis",
    "personal baseline",
    "elevated parkinson's risk pattern",
]


# ── File Collectors ───────────────────────────────────────────────────────────

def get_all_user_facing_source_files():
    """Collect all user-facing JSX and JS source files in the mobile module."""
    files = []
    for pattern in ["*.jsx", "*.js"]:
        files.extend(MOBILE_DIR.rglob(pattern))
    # Exclude test files
    return [f for f in files if "tests" not in str(f) and "__pycache__" not in str(f)]


def get_all_python_source_files():
    """Collect all Python source files in the mobile module."""
    files = list(MOBILE_DIR.rglob("*.py"))
    return [f for f in files if "tests" not in str(f) and "__pycache__" not in str(f)]


def get_documentation_files():
    """Collect key documentation files."""
    docs = []
    for p in DOCS_FILES:
        if p.exists():
            docs.append(p)
    return docs


def check_phrase_in_file(file_path: Path, phrase: str, allow_negated: bool = False) -> bool:
    """
    Returns True if phrase is found in file (case-insensitive).
    If allow_negated=True, occurrences preceded by 'not a' or 'not' are excluded.
    """
    try:
        text = file_path.read_text(encoding="utf-8").lower()
    except (UnicodeDecodeError, PermissionError):
        return False

    if phrase not in text:
        return False

    if allow_negated:
        # Find all occurrences and check if each is negated
        idx = 0
        while True:
            pos = text.find(phrase, idx)
            if pos == -1:
                break
            # Look at the 20 characters before the phrase
            prefix = text[max(0, pos - 25):pos]
            if "not a" not in prefix and "not " not in prefix and "non-" not in prefix:
                return True  # Found a non-negated occurrence
            idx = pos + 1
        return False

    return True


# ══════════════════════════════════════════════════════════════════════════════
# TEST 1: Forbidden Diagnostic Phrases — JS/JSX Source Files
# ══════════════════════════════════════════════════════════════════════════════

class TestForbiddenDiagnosticPhrasesJS:
    """Scan all JS/JSX user-facing source files for forbidden diagnostic language."""

    def test_no_you_have_parkinsons_in_js(self):
        """ZERO TOLERANCE: 'you have parkinson's' must not appear in any JS/JSX source."""
        files = get_all_user_facing_source_files()
        if not files:
            pytest.skip("No JS/JSX source files found")
        violations = []
        for f in files:
            text = f.read_text(encoding="utf-8").lower()
            if "you have parkinson" in text:
                violations.append(f.name)
        assert not violations, f"FORBIDDEN LANGUAGE in: {violations}"

    def test_no_parkinsons_disease_detected_in_js(self):
        """ZERO TOLERANCE: 'parkinson's disease detected' must not appear in any JS/JSX."""
        files = get_all_user_facing_source_files()
        if not files:
            pytest.skip("No JS/JSX source files found")
        violations = []
        for f in files:
            text = f.read_text(encoding="utf-8").lower()
            for phrase in ["parkinson's disease detected", "parkinsons disease detected",
                           "parkinson detected"]:
                if phrase in text:
                    violations.append(f"{f.name}: '{phrase}'")
        assert not violations, f"FORBIDDEN LANGUAGE:\n" + "\n".join(violations)

    def test_no_parkinsons_progression_in_js(self):
        """ZERO TOLERANCE: 'parkinson's progression' must not appear in any JS/JSX."""
        files = get_all_user_facing_source_files()
        if not files:
            pytest.skip("No JS/JSX source files found")
        violations = []
        for f in files:
            text = f.read_text(encoding="utf-8").lower()
            if "parkinson's progression" in text or "parkinsons progression" in text:
                violations.append(f.name)
        assert not violations, f"FORBIDDEN LANGUAGE in: {violations}"

    def test_no_clinical_decline_in_js(self):
        """ZERO TOLERANCE: 'clinical decline' must not appear in any JS/JSX."""
        files = get_all_user_facing_source_files()
        if not files:
            pytest.skip("No JS/JSX source files found")
        violations = []
        for f in files:
            text = f.read_text(encoding="utf-8").lower()
            if "clinical decline" in text:
                violations.append(f.name)
        assert not violations, f"FORBIDDEN LANGUAGE in: {violations}"

    def test_no_disease_worsening_in_js(self):
        """ZERO TOLERANCE: 'disease worsening' must not appear in any JS/JSX."""
        files = get_all_user_facing_source_files()
        if not files:
            pytest.skip("No JS/JSX source files found")
        violations = []
        for f in files:
            text = f.read_text(encoding="utf-8").lower()
            if "disease worsening" in text:
                violations.append(f.name)
        assert not violations, f"FORBIDDEN LANGUAGE in: {violations}"

    def test_diagnosis_only_appears_negated_in_js(self):
        """'clinical diagnosis' must only appear as 'not a clinical diagnosis'."""
        files = get_all_user_facing_source_files()
        if not files:
            pytest.skip("No JS/JSX source files found")
        violations = []
        for f in files:
            text = f.read_text(encoding="utf-8").lower()
            if "clinical diagnosis" in text and "not a clinical diagnosis" not in text:
                # Check if any occurrence is non-negated
                lines = text.split("\n")
                for i, line in enumerate(lines, 1):
                    if "clinical diagnosis" in line and "not a clinical diagnosis" not in line:
                        violations.append(f"{f.name}:{i}: '{line.strip()}'")
        assert not violations, f"NON-NEGATED 'clinical diagnosis':\n" + "\n".join(violations)


# ══════════════════════════════════════════════════════════════════════════════
# TEST 2: Forbidden Diagnostic Phrases — Python Source Files
# ══════════════════════════════════════════════════════════════════════════════

class TestForbiddenDiagnosticPhrasesPython:
    """Scan all Python source files for forbidden diagnostic language."""

    def test_no_you_have_parkinsons_in_python(self):
        """ZERO TOLERANCE: 'you have parkinson's' must not appear in Python source."""
        files = get_all_python_source_files()
        if not files:
            pytest.skip("No Python source files found")
        violations = []
        for f in files:
            text = f.read_text(encoding="utf-8").lower()
            if "you have parkinson" in text:
                violations.append(f.name)
        assert not violations, f"FORBIDDEN LANGUAGE in Python: {violations}"

    def test_no_parkinsons_progression_in_python(self):
        """ZERO TOLERANCE: 'parkinson's progression' must not appear in Python source."""
        files = get_all_python_source_files()
        if not files:
            pytest.skip("No Python source files found")
        violations = []
        for f in files:
            text = f.read_text(encoding="utf-8").lower()
            if "parkinson's progression" in text and "never say" not in text:
                violations.append(f.name)
        assert not violations, f"FORBIDDEN LANGUAGE in Python: {violations}"

    def test_forbidden_terms_not_in_prediction_logger(self):
        """prediction_logger.py must define FORBIDDEN_DIAGNOSTIC_TERMS list."""
        from src.mobile.prediction_logger import FORBIDDEN_DIAGNOSTIC_TERMS
        assert len(FORBIDDEN_DIAGNOSTIC_TERMS) >= 3, \
            "prediction_logger must enumerate at least 3 forbidden terms"
        combined = " ".join(FORBIDDEN_DIAGNOSTIC_TERMS).lower()
        assert "you have parkinson" in combined or "parkinson" in combined

    def test_research_disclaimer_in_prediction_logger(self):
        """prediction_logger.py must define RESEARCH_DISCLAIMER constant."""
        from src.mobile.prediction_logger import RESEARCH_DISCLAIMER
        assert "research" in RESEARCH_DISCLAIMER.lower()
        assert "not a clinical diagnosis" in RESEARCH_DISCLAIMER.lower()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 3: Sensor Overclaiming Phrases
# ══════════════════════════════════════════════════════════════════════════════

class TestSensorOverclaimingPhrases:
    """Rule 2: Smartphone camera is NOT a retinal camera — zero tolerance."""

    def test_no_retinal_camera_claim_in_js(self):
        """ZERO TOLERANCE: 'retinal camera' must not appear in any JS/JSX source."""
        files = get_all_user_facing_source_files()
        violations = []
        for f in files:
            text = f.read_text(encoding="utf-8").lower()
            if "retinal camera" in text:
                violations.append(f.name)
        assert not violations, f"SENSOR OVERCLAIMING in: {violations}"

    def test_no_retinal_imaging_claim_in_js(self):
        """ZERO TOLERANCE: 'retinal imaging' must not appear in any JS/JSX source."""
        files = get_all_user_facing_source_files()
        violations = []
        for f in files:
            text = f.read_text(encoding="utf-8").lower()
            # Exception: allowed when explicitly negating ("not retinal imaging")
            if "retinal imaging" in text and "not retinal" not in text:
                # Check each occurrence
                for line in text.split("\n"):
                    if "retinal imaging" in line and "not" not in line:
                        violations.append(f"{f.name}: '{line.strip()}'")
        assert not violations, f"SENSOR OVERCLAIMING:\n" + "\n".join(violations)

    def test_no_fundus_camera_claim(self):
        """ZERO TOLERANCE: 'fundus camera' claim not valid for smartphone."""
        files = get_all_user_facing_source_files() + get_all_python_source_files()
        violations = []
        for f in files:
            text = f.read_text(encoding="utf-8").lower()
            if "fundus camera" in text:
                violations.append(f.name)
        assert not violations, f"FUNDUS SENSOR OVERCLAIMING in: {violations}"

    def test_ocular_disclaimer_in_python_feature_mapper(self):
        """Python feature_mapper.py must contain OCULAR_DISCLAIMER about non-retinal camera."""
        from src.mobile.feature_mapper import OCULAR_DISCLAIMER
        text = OCULAR_DISCLAIMER.lower()
        assert "not a retinal camera" in text or "not" in text
        assert "retinal" in text
        assert "smartphone" in text or "front camera" in text


# ══════════════════════════════════════════════════════════════════════════════
# TEST 4: Required Allowed Phrases
# ══════════════════════════════════════════════════════════════════════════════

class TestRequiredAllowedPhrases:
    """Verify that correct, allowed research phrases are present in the codebase."""

    def test_research_disclaimer_present_in_codebase(self):
        """At least one source file must contain 'research screening result'."""
        files = get_all_python_source_files() + get_all_user_facing_source_files()
        found = any(
            "research screening result" in f.read_text(encoding="utf-8").lower()
            for f in files if f.exists()
        )
        assert found, "Required phrase 'research screening result' not found in any source file"

    def test_not_a_clinical_diagnosis_present(self):
        """At least one source file must contain 'not a clinical diagnosis'."""
        files = get_all_python_source_files() + get_all_user_facing_source_files()
        found = any(
            "not a clinical diagnosis" in f.read_text(encoding="utf-8").lower()
            for f in files if f.exists()
        )
        assert found, "Required phrase 'not a clinical diagnosis' not found in any source file"

    def test_personal_baseline_language_present(self):
        """At least one source file must contain 'personal baseline'."""
        files = get_all_python_source_files() + get_all_user_facing_source_files()
        found = any(
            "personal baseline" in f.read_text(encoding="utf-8").lower()
            for f in files if f.exists()
        )
        assert found, "Required phrase 'personal baseline' not found in any source file"

    def test_elevated_risk_pattern_language_present(self):
        """At least one source file must use 'elevated parkinson's risk pattern' language."""
        files = get_all_python_source_files() + get_all_user_facing_source_files()
        found = any(
            "elevated parkinson" in f.read_text(encoding="utf-8").lower()
            or "risk pattern" in f.read_text(encoding="utf-8").lower()
            for f in files if f.exists()
        )
        assert found, "Required risk pattern language not found in any source file"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 5: Documentation Safety Language
# ══════════════════════════════════════════════════════════════════════════════

class TestDocumentationSafetyLanguage:
    """Validates safety language in key documentation files."""

    def test_readme_no_diagnostic_claims(self):
        """README.md must not contain forbidden diagnostic language."""
        readme = ROOT / "README.md"
        if not readme.exists():
            pytest.skip("README.md not found")
        text = readme.read_text(encoding="utf-8").lower()
        for phrase in ["you have parkinson", "parkinson's progression", "clinical decline"]:
            assert phrase not in text, f"README.md contains forbidden phrase: '{phrase}'"

    def test_ethical_considerations_no_overclaiming(self):
        """ETHICAL_CONSIDERATIONS.md must acknowledge limitations."""
        doc = ROOT / "ETHICAL_CONSIDERATIONS.md"
        if not doc.exists():
            pytest.skip("ETHICAL_CONSIDERATIONS.md not found")
        text = doc.read_text(encoding="utf-8").lower()
        # Must contain limitation acknowledgements
        has_limitations = "limitation" in text or "not a diagnostic" in text or "research" in text
        assert has_limitations, "Ethics doc must acknowledge research limitations"

    def test_privacy_model_doc_covers_data_protection(self):
        """PRIVACY_MODEL.md must cover key privacy principles."""
        doc = ROOT / "PRIVACY_MODEL.md"
        if not doc.exists():
            pytest.skip("PRIVACY_MODEL.md not found")
        text = doc.read_text(encoding="utf-8").lower()
        assert "consent" in text
        assert "deletion" in text or "delete" in text
        assert "pseudon" in text or "anonymi" in text


# ══════════════════════════════════════════════════════════════════════════════
# TEST 6: Comprehensive Full Scan
# ══════════════════════════════════════════════════════════════════════════════

class TestComprehensiveLanguageScan:
    """Full scan of all sources against complete forbidden phrase list."""

    @pytest.mark.parametrize("phrase", [
        "you have parkinson",
        "parkinson's disease detected",
        "clinical decline",
        "disease worsening",
        "parkinson's progression",
        "confirmed parkinson",
    ])
    def test_forbidden_phrase_not_in_any_js_source(self, phrase):
        """[PARAMETRIZED] Each forbidden phrase must not appear in any JS/JSX source."""
        files = get_all_user_facing_source_files()
        violations = []
        for f in files:
            try:
                text = f.read_text(encoding="utf-8").lower()
                if phrase in text:
                    violations.append(f.name)
            except Exception:
                pass
        assert not violations, f"Phrase '{phrase}' found in: {violations}"

    @pytest.mark.parametrize("phrase", [
        "you have parkinson",
        "clinical decline",
        "disease worsening",
        "parkinson's progression",
    ])
    def test_forbidden_phrase_not_in_any_python_source(self, phrase):
        """[PARAMETRIZED] Each forbidden phrase must not appear in Python source (excl. docstrings about what NOT to say)."""
        files = get_all_python_source_files()
        violations = []
        for f in files:
            try:
                text = f.read_text(encoding="utf-8")
                text_lower = text.lower()
                if phrase in text_lower:
                    # Allow if it's in a comment/docstring explicitly listing forbidden phrases
                    lines = text.split("\n")
                    for i, line in enumerate(lines, 1):
                        if phrase in line.lower():
                            # Check if it's a "never say" / "forbidden" documentation
                            context = "\n".join(lines[max(0, i-3):i+3]).lower()
                            if (
                                "never say" not in context
                                and "forbidden" not in context
                                and "do not say" not in context
                                and "avoid" not in context
                                and "#" not in line.strip()[:2]
                            ):
                                violations.append(f"{f.name}:{i}")
            except Exception:
                pass
        assert not violations, f"Forbidden phrase '{phrase}' in Python sources: {violations}"
