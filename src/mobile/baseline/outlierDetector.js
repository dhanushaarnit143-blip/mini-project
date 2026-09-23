/**
 * MPF Mobile Extension — Outlier Detector (Phase 10)
 *
 * Implements MAD-based outlier resistance for longitudinal monitoring:
 * - Computes distance in units of Median Absolute Deviation (MAD):
 *     mad_distance = |value - baseline_median| / MAD
 * - If mad_distance > 3.0 MAD:
 *     - Flagged as 'anomalous observation'
 *     - Rejected from baseline updating (prevents corruption)
 *     - Recorded in daily_deviations table for longitudinal audit
 *
 * NON-NEGOTIABLE COMPLIANCE:
 * - NO DIAGNOSTIC CLAIMS: An outlier is an "anomalous observation" or "divergence from personal baseline".
 * - BASELINE-CENTRIC: Evaluated strictly against the participant's own historical baseline.
 */

export const OUTLIER_MAD_THRESHOLD = 3.0;

/**
 * Normalizes MAD or provides standard deviation fallback if MAD is zero.
 * @param {Object} baseline
 * @returns {number}
 */
export function getEffectiveDispersion(baseline) {
  if (baseline && typeof baseline.baseline_mad === 'number' && baseline.baseline_mad > 0) {
    return baseline.baseline_mad;
  }
  if (baseline && typeof baseline.baseline_std === 'number' && baseline.baseline_std > 0) {
    // Normal distribution MAD ≈ 0.6745 * std
    return Number((baseline.baseline_std * 0.6745).toFixed(4));
  }
  return 0.001;
}

/**
 * Checks if a single observation is an extreme outlier (> 3 MAD) relative to personal baseline.
 *
 * @param {number} value New observation value
 * @param {Object} baseline Personal baseline profile
 * @param {Object} [options]
 * @param {number} [options.threshold=3.0] MAD multiplier threshold
 * @returns {Object} Outlier evaluation result
 */
export function detectOutlier(value, baseline, options = {}) {
  const threshold = options.threshold ?? OUTLIER_MAD_THRESHOLD;

  if (typeof value !== 'number' || Number.isNaN(value) || !Number.isFinite(value)) {
    return {
      isOutlier: false,
      madDistance: null,
      threshold,
      anomalyFlag: null,
      reason: 'Invalid or missing observation value',
      isInvalid: true,
    };
  }

  if (!baseline || baseline.baseline_median === null || baseline.baseline_median === undefined) {
    return {
      isOutlier: false,
      madDistance: null,
      threshold,
      anomalyFlag: null,
      reason: 'No established baseline available',
      isInvalid: false,
    };
  }

  const median = Number(baseline.baseline_median);
  const dispersion = getEffectiveDispersion(baseline);
  const absoluteDiff = Math.abs(value - median);
  const madDistance = Number((absoluteDiff / dispersion).toFixed(4));

  const isExtreme = madDistance > threshold;

  return {
    isOutlier: isExtreme,
    madDistance,
    threshold,
    anomalyFlag: isExtreme ? 'anomalous observation' : null,
    reason: isExtreme
      ? `Observation deviates by ${madDistance} MAD (> ${threshold} threshold) from personal baseline`
      : 'Observation within expected personal variance',
    isInvalid: false,
  };
}

/**
 * Computes deviation record suitable for daily_deviations table.
 *
 * @param {Object} params
 * @param {string} params.participantId
 * @param {string} params.date
 * @param {string} params.modality
 * @param {string} params.featureName
 * @param {number} params.value
 * @param {Object} params.baseline
 * @param {number} [params.qualityScore=1.0]
 * @param {string} [params.algorithmVersion='1.0.0']
 * @returns {Object} Structured record for daily_deviations table
 */
export function createDeviationRecord(params) {
  const {
    participantId,
    date,
    modality,
    featureName,
    value,
    baseline,
    qualityScore = 1.0,
    algorithmVersion = '1.0.0',
  } = params;

  const outlierCheck = detectOutlier(value, baseline);
  const median = baseline?.baseline_median ?? value;
  const dispersion = getEffectiveDispersion(baseline);

  // Robust normalized deviation score: (value - median) / (1.4826 * MAD)
  // which aligns with standard normal scale while remaining outlier-resistant
  const normalizedDevScore = dispersion > 0
    ? Number(((value - median) / (dispersion * 1.4826)).toFixed(4))
    : 0.0;

  // Trend score: directional difference relative to personal baseline median
  const trendScore = Number((value - median).toFixed(4));

  return {
    participant_id: participantId,
    date,
    modality,
    feature_name: featureName,
    value: Number(Number(value).toFixed(4)),
    baseline_value: Number(Number(median).toFixed(4)),
    deviation_score: normalizedDevScore,
    trend_score: trendScore,
    quality_score: Number(Math.max(0.0, Math.min(1.0, qualityScore)).toFixed(4)),
    algorithm_version: algorithmVersion,
    is_outlier: outlierCheck.isOutlier,
    anomaly_flag: outlierCheck.anomalyFlag,
    mad_distance: outlierCheck.madDistance,
    summary_text: outlierCheck.isOutlier
      ? 'Recent measurement differs notably from personal baseline (anomalous observation).'
      : 'Measurement consistent with personal baseline.',
  };
}

// Dual CommonJS / ES Module export
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    OUTLIER_MAD_THRESHOLD,
    getEffectiveDispersion,
    detectOutlier,
    createDeviationRecord,
  };
}
