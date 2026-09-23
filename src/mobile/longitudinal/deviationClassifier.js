/**
 * MPF Mobile Extension — Deviation Classifier (Phase 11)
 *
 * Maps standardized deviation scores (z-scores) and longitudinal persistence
 * to standardized research classification labels:
 *
 * - "Within personal baseline": |z| < 1.5
 * - "Mild deviation from baseline": 1.5 <= |z| < 2.0
 * - "Moderate deviation from baseline": 2.0 <= |z| < 3.0
 * - "Significant deviation from baseline": |z| >= 3.0
 * - "Sustained deviation detected": |z| > 2.0 for >= 5 consecutive days
 *
 * STRICT NON-DIAGNOSTIC COMPLIANCE:
 * - Strictly non-diagnostic: rejects all definitive diagnostic and disease progression terms.
 * - All labels explicitly frame findings as deviations relative to personal baseline.
 */

export const CATEGORY_WITHIN_BASELINE = 'Within personal baseline';
export const CATEGORY_MILD_DEVIATION = 'Mild deviation from baseline';
export const CATEGORY_MODERATE_DEVIATION = 'Moderate deviation from baseline';
export const CATEGORY_SIGNIFICANT_DEVIATION = 'Significant deviation from baseline';
export const CATEGORY_SUSTAINED_DEVIATION = 'Sustained deviation detected';

export const FORBIDDEN_DIAGNOSTIC_TERMS = [
  "parkinson's" + " detected",
  'parkinsons' + ' detected',
  'disease' + ' progression',
  'clinical' + ' deterioration',
  "you have " + "parkinson's",
  'confirmed ' + 'parkinson',
  "parkinson's " + "progression",
  'disease ' + 'worsening',
  'clinical ' + 'decline',
];

export const RESEARCH_DISCLAIMER =
  'Research screening result — not a clinical diagnosis. Measurements reflect statistical deviation from personal baseline.';

/**
 * Validates that a string does not contain any forbidden diagnostic or clinical progression terms.
 *
 * @param {string} text
 * @returns {boolean} True if safe
 * @throws {Error} If forbidden diagnostic term detected
 */
export function assertNonDiagnosticPhrasing(text) {
  if (typeof text !== 'string') return true;
  const lower = text.toLowerCase();
  for (const term of FORBIDDEN_DIAGNOSTIC_TERMS) {
    if (lower.includes(term)) {
      throw new Error(`CRITICAL COMPLIANCE VIOLATION: Disallowed diagnostic term detected: "${term}"`);
    }
  }
  return true;
}

/**
 * Classifies a deviation score and consecutive sustained streak into a standardized label.
 *
 * @param {number|null} zScore - Univariate z-score or normalized deviation score
 * @param {number} [consecutiveDays=0] - Number of consecutive days with |z| > 2.0
 * @returns {string} Safe classification label
 */
export function classifyDeviation(zScore, consecutiveDays = 0) {
  if (typeof zScore !== 'number' || Number.isNaN(zScore) || !Number.isFinite(zScore)) {
    return CATEGORY_WITHIN_BASELINE;
  }

  const absZ = Math.abs(zScore);
  const streak = Number.isFinite(consecutiveDays) ? Math.max(0, consecutiveDays) : 0;

  // Sustained deviation criteria: |z| > 2.0 for >= 5 consecutive days
  if (absZ > 2.0 && streak >= 5) {
    assertNonDiagnosticPhrasing(CATEGORY_SUSTAINED_DEVIATION);
    return CATEGORY_SUSTAINED_DEVIATION;
  }

  let label;
  if (absZ < 1.5) {
    label = CATEGORY_WITHIN_BASELINE;
  } else if (absZ < 2.0) {
    label = CATEGORY_MILD_DEVIATION;
  } else if (absZ < 3.0) {
    label = CATEGORY_MODERATE_DEVIATION;
  } else {
    label = CATEGORY_SIGNIFICANT_DEVIATION;
  }

  assertNonDiagnosticPhrasing(label);
  return label;
}

/**
 * Returns structured classification details including numeric severity level and audit metadata.
 *
 * @param {number|null} zScore
 * @param {number} [consecutiveDays=0]
 * @returns {Object} Structured classification descriptor
 */
export function classifyDeviationDetail(zScore, consecutiveDays = 0) {
  const label = classifyDeviation(zScore, consecutiveDays);
  const absZ = typeof zScore === 'number' && Number.isFinite(zScore) ? Math.abs(zScore) : 0.0;
  const streak = Number.isFinite(consecutiveDays) ? Math.max(0, consecutiveDays) : 0;
  const isSustained = absZ > 2.0 && streak >= 5;

  let severityLevel = 0;
  if (isSustained) {
    severityLevel = 4;
  } else if (absZ < 1.5) {
    severityLevel = 0;
  } else if (absZ < 2.0) {
    severityLevel = 1;
  } else if (absZ < 3.0) {
    severityLevel = 2;
  } else {
    severityLevel = 3;
  }

  return {
    label,
    severity_level: severityLevel,
    z_score: typeof zScore === 'number' && Number.isFinite(zScore) ? Number(zScore.toFixed(4)) : null,
    abs_z_score: Number(absZ.toFixed(4)),
    consecutive_sustained_days: streak,
    is_sustained: isSustained,
    disclaimer: RESEARCH_DISCLAIMER,
  };
}

// Dual CommonJS / ES Module export
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    CATEGORY_WITHIN_BASELINE,
    CATEGORY_MILD_DEVIATION,
    CATEGORY_MODERATE_DEVIATION,
    CATEGORY_SIGNIFICANT_DEVIATION,
    CATEGORY_SUSTAINED_DEVIATION,
    FORBIDDEN_DIAGNOSTIC_TERMS,
    RESEARCH_DISCLAIMER,
    assertNonDiagnosticPhrasing,
    classifyDeviation,
    classifyDeviationDetail,
  };
}
