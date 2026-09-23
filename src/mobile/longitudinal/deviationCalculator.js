/**
 * MPF Mobile Extension — Longitudinal Deviation Calculator (Phase 11)
 *
 * Computes standardized and robust z-score deviations of daily feature observations
 * relative to personal calibrated baseline:
 *
 * 1. Parametric z-score (standard):
 *    z = (today_value - baseline_mean) / baseline_std
 *
 * 2. MAD-resilient z-score (fallback when baseline_std is 0 or very small):
 *    z = 0.6745 * (today_value - baseline_median) / baseline_mad
 *    (Note: 0.6745 ≈ 1 / 1.4826, mapping MAD to standard normal distribution units)
 *
 * 3. Zero dispersion safety:
 *    When both baseline_std and baseline_mad are zero or near-zero, zero difference yields
 *    z = 0.0, and non-zero difference is handled gracefully with epsilon dispersion.
 *
 * NON-NEGOTIABLE COMPLIANCE:
 * - NO DIAGNOSTIC CLAIMS: Computes statistical deviation from personal baseline only.
 * - BASELINE-CENTRIC: Every computation evaluates strictly against the participant's own baseline.
 * - NO DATA FABRICATION: Operates strictly on supplied feature observations.
 */

export const MIN_DISPERSION_EPSILON = 1e-6;
export const MAD_TO_NORMAL_FACTOR = 0.6745;

/**
 * Calculates standardized deviation (z-score) between a daily feature value and personal baseline.
 *
 * @param {number} todayValue - Daily feature observation
 * @param {Object} baseline - Personal baseline object
 * @param {number} [baseline.baseline_mean] - Calibration mean
 * @param {number} [baseline.baseline_std] - Calibration standard deviation
 * @param {number} [baseline.baseline_median] - Calibration median
 * @param {number} [baseline.baseline_mad] - Calibration median absolute deviation
 * @returns {Object} Deviation result with z_score, method, and numerical components
 */
export function calculateDeviation(todayValue, baseline) {
  if (typeof todayValue !== 'number' || Number.isNaN(todayValue) || !Number.isFinite(todayValue)) {
    return {
      z_score: null,
      deviation_score: null,
      method: 'invalid_value',
      today_value: null,
      baseline_value: null,
      diff: null,
      isValid: false,
    };
  }

  if (!baseline || typeof baseline !== 'object') {
    return {
      z_score: null,
      deviation_score: null,
      method: 'missing_baseline',
      today_value: todayValue,
      baseline_value: null,
      diff: null,
      isValid: false,
    };
  }

  const mean = typeof baseline.baseline_mean === 'number' && Number.isFinite(baseline.baseline_mean)
    ? baseline.baseline_mean
    : null;
  const std = typeof baseline.baseline_std === 'number' && Number.isFinite(baseline.baseline_std)
    ? baseline.baseline_std
    : 0;
  const median = typeof baseline.baseline_median === 'number' && Number.isFinite(baseline.baseline_median)
    ? baseline.baseline_median
    : mean;
  const mad = typeof baseline.baseline_mad === 'number' && Number.isFinite(baseline.baseline_mad)
    ? baseline.baseline_mad
    : 0;

  // Decide whether to use standard parametric z-score or MAD-based fallback
  const isStdViable = std > MIN_DISPERSION_EPSILON && mean !== null;

  if (isStdViable) {
    const diff = todayValue - mean;
    const rawZ = diff / std;
    const zScore = Number(rawZ.toFixed(4));

    return {
      z_score: zScore,
      deviation_score: zScore,
      method: 'parametric_std',
      today_value: Number(todayValue.toFixed(4)),
      baseline_value: Number(mean.toFixed(4)),
      diff: Number(diff.toFixed(4)),
      dispersion: Number(std.toFixed(4)),
      isValid: true,
    };
  }

  // Fallback to MAD-based z-score
  const effectiveMedian = median !== null ? median : 0;
  const diff = todayValue - effectiveMedian;

  if (mad > MIN_DISPERSION_EPSILON) {
    const rawZ = (MAD_TO_NORMAL_FACTOR * diff) / mad;
    const zScore = Number(rawZ.toFixed(4));

    return {
      z_score: zScore,
      deviation_score: zScore,
      method: 'mad_fallback',
      today_value: Number(todayValue.toFixed(4)),
      baseline_value: Number(effectiveMedian.toFixed(4)),
      diff: Number(diff.toFixed(4)),
      dispersion: Number(mad.toFixed(4)),
      isValid: true,
    };
  }

  // Edge case: both std and mad are zero / near-zero
  if (Math.abs(diff) < MIN_DISPERSION_EPSILON) {
    return {
      z_score: 0.0,
      deviation_score: 0.0,
      method: 'zero_dispersion',
      today_value: Number(todayValue.toFixed(4)),
      baseline_value: Number(effectiveMedian.toFixed(4)),
      diff: 0.0,
      dispersion: 0.0,
      isValid: true,
    };
  }

  // Non-zero difference with zero dispersion: safe epsilon calculation capped at +-10
  const sign = diff >= 0 ? 1 : -1;
  const safeZ = sign * 10.0;
  return {
    z_score: safeZ,
    deviation_score: safeZ,
    method: 'zero_dispersion_extreme',
    today_value: Number(todayValue.toFixed(4)),
    baseline_value: Number(effectiveMedian.toFixed(4)),
    diff: Number(diff.toFixed(4)),
    dispersion: 0.0,
    isValid: true,
  };
}

/**
 * Builds a record suitable for direct insertion into public.daily_deviations table.
 *
 * @param {Object} params
 * @param {string} params.participantId - UUID of participant
 * @param {string} params.date - Date in YYYY-MM-DD
 * @param {string} params.modality - 'typing' | 'voice' | 'motor' | 'visual' | 'sleep'
 * @param {string} params.featureName - Feature identifier (e.g. 'typing_speed')
 * @param {number} params.value - Today's measurement
 * @param {Object} params.baseline - Personal baseline record
 * @param {number} [params.qualityScore=1.0] - Measurement quality [0.0 - 1.0]
 * @param {string} [params.algorithmVersion='1.1.0'] - Module algorithm version
 * @param {number} [params.trendScore=0.0] - Optional trend score / slope
 * @returns {Object} Database row format for daily_deviations
 */
export function buildDeviationRecord(params) {
  const {
    participantId,
    date,
    modality,
    featureName,
    value,
    baseline,
    qualityScore = 1.0,
    algorithmVersion = '1.1.0',
    trendScore = 0.0,
  } = params;

  const dev = calculateDeviation(value, baseline);

  return {
    participant_id: participantId,
    date,
    modality,
    feature_name: featureName,
    value: dev.today_value !== null ? dev.today_value : value,
    baseline_value: dev.baseline_value !== null ? dev.baseline_value : 0.0,
    deviation_score: dev.deviation_score !== null ? dev.deviation_score : 0.0,
    trend_score: Number(trendScore.toFixed(4)),
    quality_score: Number(Math.max(0.0, Math.min(1.0, qualityScore)).toFixed(4)),
    algorithm_version: algorithmVersion,
  };
}

// Dual CommonJS / ES Module export
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    MIN_DISPERSION_EPSILON,
    MAD_TO_NORMAL_FACTOR,
    calculateDeviation,
    buildDeviationRecord,
  };
}
