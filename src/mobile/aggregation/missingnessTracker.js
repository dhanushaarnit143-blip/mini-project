/**
 * MPF Mobile Extension — Missingness Tracker Module (Phase 9)
 *
 * Implements strict tracking of modality availability and enforces the NON-IMPUTATION rule:
 * - Tracks 5 mobile modalities: 'typing', 'voice', 'motor', 'visual', 'sleep'
 * - If a modality has no sessions, marks it as 'missing'
 * - If all sessions for a modality are below quality threshold, marks it as 'low_quality'
 *   and excludes it from available_modalities (includes in missing_modalities)
 * - NEVER imputes missing values with population averages, defaults, or fabricated numbers.
 *
 * NON-NEGOTIABLE COMPLIANCE:
 * - NO DATA FABRICATION: Missing modality features remain null.
 * - BASELINE-CENTRIC: Missingness must be transparent for subsequent baseline calculations.
 */

export const TRACKED_MODALITIES = ['typing', 'voice', 'motor', 'visual', 'sleep'];

export const MODALITY_STATUS = {
  AVAILABLE: 'available',
  MISSING: 'missing',
  LOW_QUALITY: 'low_quality',
};

/**
 * Tracks availability and missingness of modalities for a given day.
 *
 * @param {Object} modalityEvaluations - Map of modality -> quality evaluation result.
 *   e.g. { typing: { status: 'valid', ... }, visual: { status: 'missing', ... } }
 * @returns {Object} Missingness report containing available, missing, and low_quality lists.
 */
export function trackMissingness(modalityEvaluations = {}) {
  const availableModalities = [];
  const missingModalities = [];
  const lowQualityModalities = [];
  const modalityStatus = {};

  for (const modality of TRACKED_MODALITIES) {
    const evaluation = modalityEvaluations[modality];
    const status = evaluation ? evaluation.status : MODALITY_STATUS.MISSING;

    if (status === 'valid') {
      availableModalities.push(modality);
      modalityStatus[modality] = MODALITY_STATUS.AVAILABLE;
    } else if (status === 'low_quality') {
      lowQualityModalities.push(modality);
      missingModalities.push(modality); // Excluded from usable daily features
      modalityStatus[modality] = MODALITY_STATUS.LOW_QUALITY;
    } else {
      missingModalities.push(modality);
      modalityStatus[modality] = MODALITY_STATUS.MISSING;
    }
  }

  const completenessRatio = Number(
    (availableModalities.length / TRACKED_MODALITIES.length).toFixed(2)
  );

  return {
    available_modalities: availableModalities,
    missing_modalities: missingModalities,
    low_quality_modalities: lowQualityModalities,
    modality_status: modalityStatus,
    completeness_ratio: completenessRatio,
    total_modalities: TRACKED_MODALITIES.length,
    available_count: availableModalities.length,
    missing_count: missingModalities.length,
  };
}

/**
 * Validates that a daily feature vector strictly adheres to the NO IMPUTATION rule.
 * For every modality marked in missing_modalities, its feature block MUST be null.
 *
 * @param {Object} featureVector - The generated daily feature vector.
 * @returns {{ valid: boolean, errors: Array<string> }}
 */
export function validateNoImputation(featureVector) {
  const errors = [];
  if (!featureVector || typeof featureVector !== 'object') {
    return { valid: false, errors: ['Invalid feature vector: must be a non-null object.'] };
  }

  const missing = Array.isArray(featureVector.missing_modalities)
    ? featureVector.missing_modalities
    : [];

  const available = Array.isArray(featureVector.available_modalities)
    ? featureVector.available_modalities
    : [];

  // Check overlap
  const overlap = available.filter(m => missing.includes(m));
  if (overlap.length > 0) {
    errors.push(`Modality cannot be both available and missing: ${overlap.join(', ')}`);
  }

  // Check missing modalities are null
  for (const modality of missing) {
    const val = featureVector[modality];
    if (val !== null && val !== undefined) {
      errors.push(
        `Violation of NO IMPUTATION rule: modality "${modality}" is marked as missing but contains non-null data: ${JSON.stringify(val)}`
      );
    }
  }

  // Check available modalities have non-null feature block
  for (const modality of available) {
    const val = featureVector[modality];
    if (val === null || val === undefined) {
      errors.push(
        `Modality "${modality}" is marked as available but its feature block is null or undefined.`
      );
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

// Dual CommonJS / ES Module export
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    TRACKED_MODALITIES,
    MODALITY_STATUS,
    trackMissingness,
    validateNoImputation,
  };
}
