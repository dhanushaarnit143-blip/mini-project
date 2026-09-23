/**
 * MPF Mobile Extension — Adaptive Baseline Updater (Phase 10)
 *
 * Implements longitudinal adaptive rolling baseline updates for Day 15+:
 * - Uses Exponentially Weighted Moving Average (EWMA) with configurable alpha (default: 0.1).
 * - Applies strict quality filtering (rejects observations < 0.50 quality).
 * - Outlier resistance: Rejects observations deviating > 3 MAD from baseline.
 * - Flags outliers as 'anomalous observation' and logs to daily_deviations without corrupting baseline.
 * - Increments baseline_version and updates baseline_updated_at on successful update.
 *
 * NON-NEGOTIABLE COMPLIANCE:
 * - NO DIAGNOSTIC CLAIMS: An outlier is an "anomalous observation", never "Parkinson's detected".
 * - BASELINE-CENTRIC: Continuous adaptation to the individual's personal physiological drift.
 */

import { detectOutlier, createDeviationRecord } from './outlierDetector.js';
import { updateBaselineVersion } from './baselineVersionManager.js';

export const DEFAULT_EWMA_ALPHA = 0.1;
export const MIN_OBSERVATION_QUALITY = 0.50;

/**
 * Applies an adaptive rolling update to an existing baseline with a new daily observation.
 *
 * @param {Object} currentBaseline The established personal baseline record
 * @param {Object} observation New daily observation { value, quality_score, date, participant_id }
 * @param {Object} [options] Configuration overrides
 * @param {number} [options.alpha=0.1] EWMA smoothing factor
 * @param {number} [options.minQuality=0.50] Minimum quality threshold
 * @param {number} [options.outlierThreshold=3.0] Outlier MAD threshold
 * @param {string|Date} [options.updatedAt] Timestamp for update
 * @returns {Object} Update result with { status, updatedBaseline, deviationRecord, reason }
 */
export function updateAdaptiveBaseline(currentBaseline, observation, options = {}) {
  const alpha = options.alpha ?? DEFAULT_EWMA_ALPHA;
  const minQuality = options.minQuality ?? MIN_OBSERVATION_QUALITY;
  const outlierThreshold = options.outlierThreshold ?? 3.0;

  if (!currentBaseline || typeof currentBaseline !== 'object') {
    throw new Error('Current baseline must be a valid object');
  }

  if (!observation || typeof observation !== 'object' || observation.value === undefined || observation.value === null) {
    throw new Error('Observation must contain a valid numeric value');
  }

  const rawValue = Number(observation.value);
  const quality = typeof observation.quality_score === 'number' ? observation.quality_score : 1.0;
  const obsDate = observation.date || new Date().toISOString().slice(0, 10);
  const participantId = observation.participant_id || currentBaseline.participant_id;

  // 1. QUALITY FILTERING
  if (quality < minQuality) {
    return {
      status: 'rejected_low_quality',
      reason: `Quality score ${quality.toFixed(2)} is below minimum threshold ${minQuality.toFixed(2)}`,
      updatedBaseline: currentBaseline,
      deviationRecord: null,
      wasBaselineUpdated: false,
    };
  }

  // 2. OUTLIER DETECTION (MAD > 3.0)
  const outlierEval = detectOutlier(rawValue, currentBaseline, { threshold: outlierThreshold });
  const deviationRecord = createDeviationRecord({
    participantId,
    date: obsDate,
    modality: currentBaseline.modality,
    featureName: currentBaseline.feature_name,
    value: rawValue,
    baseline: currentBaseline,
    qualityScore: quality,
    algorithmVersion: currentBaseline.algorithm_version || '1.0.0',
  });

  if (outlierEval.isOutlier) {
    // Extreme outlier (> 3 MAD): DO NOT UPDATE BASELINE.
    // Flag as "anomalous observation" and keep baseline completely unchanged.
    return {
      status: 'rejected_outlier',
      reason: outlierEval.reason,
      anomalyFlag: outlierEval.anomalyFlag,
      madDistance: outlierEval.madDistance,
      updatedBaseline: { ...currentBaseline },
      deviationRecord,
      wasBaselineUpdated: false,
    };
  }

  // 3. ADAPTIVE EWMA UPDATE (Observation Accepted)
  const oldMean = Number(currentBaseline.baseline_mean);
  const oldMedian = Number(currentBaseline.baseline_median);
  const oldStd = Number(currentBaseline.baseline_std);
  const oldMad = Number(currentBaseline.baseline_mad);

  // EWMA on Mean: μ_new = α * x + (1 - α) * μ_old
  const newMean = Number((alpha * rawValue + (1.0 - alpha) * oldMean).toFixed(4));

  // EWMA on Median (robust rolling center): m_new = α * x + (1 - α) * m_old
  const newMedian = Number((alpha * rawValue + (1.0 - alpha) * oldMedian).toFixed(4));

  // EWMA on Variance: σ^2_new = α * (x - μ_new)^2 + (1 - α) * σ^2_old
  const oldVar = Math.pow(oldStd, 2);
  const instVar = Math.pow(rawValue - newMean, 2);
  const newVar = Math.max(0, alpha * instVar + (1.0 - alpha) * oldVar);
  const newStd = Number(Math.sqrt(newVar).toFixed(4));

  // EWMA on MAD: mad_new = α * |x - m_new| + (1 - α) * mad_old
  const instMad = Math.abs(rawValue - newMedian);
  const newMad = Number((alpha * instMad + (1.0 - alpha) * oldMad).toFixed(4));

  // Coefficient of Variation
  const newCv = newMean !== 0 ? Number(Math.abs(newStd / newMean).toFixed(4)) : 0.0;

  // Dispersion bounds (median ± 3 * MAD)
  const effectiveDisp = newMad > 0 ? newMad : (newStd > 0 ? newStd : 0.001);
  const newLowerBound = Number((newMedian - 3.0 * effectiveDisp).toFixed(4));
  const newUpperBound = Number((newMedian + 3.0 * effectiveDisp).toFixed(4));

  // Approximate Q1 / Q3 update
  const newQ1 = Number((newMedian - 0.6745 * effectiveDisp).toFixed(4));
  const newQ3 = Number((newMedian + 0.6745 * effectiveDisp).toFixed(4));

  // Update Version Metadata
  const newVersionMeta = updateBaselineVersion(currentBaseline, {
    updatedAt: options.updatedAt,
    incrementSamples: 1,
  });

  const updatedBaseline = {
    ...currentBaseline,
    baseline_mean: newMean,
    baseline_median: newMedian,
    baseline_std: newStd,
    baseline_mad: newMad,
    q1: newQ1,
    q3: newQ3,
    coefficient_of_variation: newCv,
    lower_bound: newLowerBound,
    upper_bound: newUpperBound,
    baseline_status: 'adaptive_updated',
    baseline_version: newVersionMeta.baseline_version,
    baseline_updated_at: newVersionMeta.baseline_updated_at,
    sample_count: newVersionMeta.sample_count,
    updated_at: newVersionMeta.baseline_updated_at,
  };

  return {
    status: 'updated',
    reason: `Baseline updated using EWMA (alpha = ${alpha}) with new observation`,
    updatedBaseline,
    deviationRecord,
    wasBaselineUpdated: true,
  };
}

// Dual CommonJS / ES Module export
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    DEFAULT_EWMA_ALPHA,
    MIN_OBSERVATION_QUALITY,
    updateAdaptiveBaseline,
  };
}
