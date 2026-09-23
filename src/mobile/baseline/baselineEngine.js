/**
 * MPF Mobile Extension — Personal Baseline Engine (Phase 10)
 *
 * Core coordinator for personal baseline establishment and adaptive tracking:
 * 1. DAYS 1-14: Baseline Establishment
 *    - Collects daily feature vectors over 14 calendar days
 *    - Applies quality gating (filters out observations with quality < 0.50)
 *    - Calculates robust and parametric baseline statistics:
 *      mean, median, standard deviation, MAD, Q1, Q3, CV, sample_count
 *    - Sets baseline_status = 'established'
 *
 * 2. DAY 15+: Adaptive Rolling Baseline
 *    - Applies EWMA (alpha = 0.1) on new quality-vetted observations
 *    - Outlier resistance: Rejects observations > 3 MAD from baseline
 *    - Outliers flagged as 'anomalous observation' and logged to daily_deviations
 *    - Increments baseline_version and records updated_at timestamp
 *
 * NON-NEGOTIABLE COMPLIANCE:
 * - NO DIAGNOSTIC CLAIMS: Non-diagnostic monitoring of individual baseline deviation.
 * - BASELINE-CENTRIC: Every evaluation is relative to personal baseline.
 * - NO AUTOMATIC RETRAINING: Operates strictly for feature calibration, not model retraining.
 */

import { calculateFeatureBaseline, MIN_BASELINE_DAYS } from './baselineCalculator.js';
import { updateAdaptiveBaseline, DEFAULT_EWMA_ALPHA, MIN_OBSERVATION_QUALITY } from './adaptiveBaselineUpdater.js';
import { detectOutlier, createDeviationRecord } from './outlierDetector.js';
import { createInitialBaselineVersion } from './baselineVersionManager.js';

export const TRACKED_MODALITIES = ['typing', 'voice', 'motor', 'visual', 'sleep'];

/**
 * Standard list of mobile features across modalities matching Mobile Data Schema.
 */
export const MODALITY_FEATURE_MAP = {
  typing: [
    'typing_speed',
    'mean_hold_duration',
    'interval_variability',
    'pause_rate',
    'correction_rate',
  ],
  voice: [
    'jitter',
    'shimmer',
    'hnr',
    'pitch_mean',
    'pause_ratio',
  ],
  motor: [
    'cadence',
    'stride_variability',
    'step_regularity',
    'tapping_rate',
    'tremor_frequency',
  ],
  visual: [
    'blink_rate',
    'saccade_velocity_proxy',
    'gaze_fixation_stability',
    'head_movement_smoothness',
  ],
  sleep: [
    'total_sleep_hours',
    'rbd_score',
    'dream_enactment_frequency',
    'motor_behaviors_score',
  ],
};

/**
 * Extracts all numeric feature observations from daily feature vectors grouped by feature key.
 *
 * @param {Array<Object>} dailyVectors List of daily feature vectors (or daily_features rows)
 * @param {number} [minQuality=0.50]
 * @returns {Map<string, { modality: string, featureName: string, values: Array<number>, dates: Array<string> }>}
 */
export function extractFeatureSeries(dailyVectors, minQuality = MIN_OBSERVATION_QUALITY) {
  const seriesMap = new Map();

  for (const day of dailyVectors) {
    const date = day.feature_date || day.date;
    const qualityScores = day.quality_scores || {};

    // Check each modality
    for (const modality of TRACKED_MODALITIES) {
      const modalityFeatures = day[modality] || day[`${modality}_features`] || {};
      const modQuality = typeof qualityScores[modality] === 'number'
        ? qualityScores[modality]
        : (day[`${modality}_quality`] ?? day.quality_score ?? 1.0);

      // Quality gating: Skip modality if below minQuality
      if (modQuality < minQuality) continue;

      for (const [featKey, featVal] of Object.entries(modalityFeatures)) {
        if (typeof featVal === 'number' && !Number.isNaN(featVal) && Number.isFinite(featVal)) {
          const mapKey = `${modality}:${featKey}`;
          if (!seriesMap.has(mapKey)) {
            seriesMap.set(mapKey, {
              modality,
              featureName: featKey,
              values: [],
              dates: [],
            });
          }
          const item = seriesMap.get(mapKey);
          item.values.push(featVal);
          item.dates.push(date);
        }
      }
    }
  }

  return seriesMap;
}

/**
 * Establishes personal baselines for all features across modalities for a 14-day calibration period.
 *
 * @param {Object} params
 * @param {string} params.participantId UUID of participant
 * @param {Array<Object>} params.dailyVectors Daily feature vectors for days 1-14
 * @param {string} [params.startDate] Start date of calibration
 * @param {string} [params.endDate] End date of calibration
 * @param {number} [params.minQuality=0.50] Quality filter cutoff
 * @param {number} [params.minDays=14] Minimum required days
 * @returns {Object} Establishment result with array of baseline records
 */
export function establishPersonalBaselines(params) {
  const {
    participantId,
    dailyVectors = [],
    startDate,
    endDate,
    minQuality = MIN_OBSERVATION_QUALITY,
    minDays = MIN_BASELINE_DAYS,
  } = params;

  if (!participantId) {
    throw new Error('participantId is required for baseline establishment');
  }

  // Extract dates from vectors if not explicitly passed
  const dates = dailyVectors
    .map(v => v.feature_date || v.date)
    .filter(Boolean)
    .sort();

  const effectiveStartDate = startDate || dates[0] || new Date().toISOString().slice(0, 10);
  const effectiveEndDate = endDate || dates[dates.length - 1] || new Date().toISOString().slice(0, 10);

  // Group features into time series
  const seriesMap = extractFeatureSeries(dailyVectors, minQuality);
  const baselines = [];

  for (const [, item] of seriesMap.entries()) {
    const stats = calculateFeatureBaseline(item.values, {
      featureName: item.featureName,
      modality: item.modality,
      startDate: effectiveStartDate,
      endDate: effectiveEndDate,
    });

    const isEstablished = item.values.length >= minDays;
    const versionMeta = createInitialBaselineVersion({
      sampleCount: item.values.length,
      createdAt: stats.created_at,
    });

    baselines.push({
      participant_id: participantId,
      modality: item.modality,
      feature_name: item.featureName,
      baseline_mean: stats.baseline_mean,
      baseline_median: stats.baseline_median,
      baseline_std: stats.baseline_std,
      baseline_mad: stats.baseline_mad,
      q1: stats.q1,
      q3: stats.q3,
      coefficient_of_variation: stats.coefficient_of_variation,
      lower_bound: stats.lower_bound,
      upper_bound: stats.upper_bound,
      sample_count: stats.sample_count,
      baseline_start_date: effectiveStartDate,
      baseline_end_date: effectiveEndDate,
      baseline_status: isEstablished ? 'established' : 'calibrating',
      baseline_version: versionMeta.baseline_version,
      algorithm_version: versionMeta.algorithm_version,
      baseline_created_at: versionMeta.baseline_created_at,
      baseline_updated_at: versionMeta.baseline_updated_at,
      created_at: stats.created_at,
      updated_at: stats.updated_at,
    });
  }

  const establishedCount = baselines.filter(b => b.baseline_status === 'established').length;
  const overallStatus = establishedCount > 0 && establishedCount === baselines.length
    ? 'established'
    : (baselines.length > 0 ? 'calibrating' : 'no_data');

  return {
    participantId,
    startDate: effectiveStartDate,
    endDate: effectiveEndDate,
    totalFeatures: baselines.length,
    establishedFeatures: establishedCount,
    overallStatus,
    baselines,
  };
}

/**
 * Evaluates and processes a new daily feature observation for Day 15+ adaptive maintenance.
 *
 * @param {Object} params
 * @param {string} params.participantId UUID of participant
 * @param {string} params.date Observation date
 * @param {Object} params.currentBaselines Map of existing baselines keyed by `${modality}:${feature_name}`
 * @param {Object} params.dailyObservation Daily observation features and quality
 * @param {Object} [params.options] Optional EWMA settings (alpha, outlierThreshold)
 * @returns {Object} Result containing updated baselines, deviation records, and outlier summaries
 */
export function processAdaptiveDay(params) {
  const {
    participantId,
    date,
    currentBaselines = {},
    dailyObservation = {},
    options = {},
  } = params;

  const alpha = options.alpha ?? DEFAULT_EWMA_ALPHA;
  const minQuality = options.minQuality ?? MIN_OBSERVATION_QUALITY;
  const outlierThreshold = options.outlierThreshold ?? 3.0;

  const updatedBaselines = [];
  const deviationRecords = [];
  const anomalies = [];
  let updatedCount = 0;
  let rejectedOutlierCount = 0;

  const qualityScores = dailyObservation.quality_scores || {};

  // Normalize baseline dictionary lookup
  const baselineLookup = new Map();
  if (Array.isArray(currentBaselines)) {
    for (const b of currentBaselines) {
      baselineLookup.set(`${b.modality}:${b.feature_name}`, b);
    }
  } else if (currentBaselines instanceof Map) {
    for (const [k, v] of currentBaselines.entries()) {
      baselineLookup.set(k, v);
    }
  } else if (typeof currentBaselines === 'object') {
    for (const [k, v] of Object.entries(currentBaselines)) {
      baselineLookup.set(k, v);
    }
  }

  // Iterate modalities
  for (const modality of TRACKED_MODALITIES) {
    const modFeatures = dailyObservation[modality] || dailyObservation[`${modality}_features`] || {};
    const modQuality = typeof qualityScores[modality] === 'number'
      ? qualityScores[modality]
      : (dailyObservation[`${modality}_quality`] ?? dailyObservation.quality_score ?? 1.0);

    for (const [featKey, featVal] of Object.entries(modFeatures)) {
      if (typeof featVal !== 'number' || Number.isNaN(featVal) || !Number.isFinite(featVal)) {
        continue;
      }

      const lookupKey = `${modality}:${featKey}`;
      const existingBaseline = baselineLookup.get(lookupKey);

      if (!existingBaseline) {
        // No established baseline yet
        continue;
      }

      const updateResult = updateAdaptiveBaseline(
        existingBaseline,
        {
          participant_id: participantId,
          date,
          value: featVal,
          quality_score: modQuality,
        },
        {
          alpha,
          minQuality,
          outlierThreshold,
          updatedAt: new Date().toISOString(),
        }
      );

      if (updateResult.deviationRecord) {
        deviationRecords.push(updateResult.deviationRecord);
      }

      if (updateResult.status === 'updated') {
        updatedBaselines.push(updateResult.updatedBaseline);
        updatedCount += 1;
      } else if (updateResult.status === 'rejected_outlier') {
        updatedBaselines.push(updateResult.updatedBaseline); // Keep existing uncorrupted
        rejectedOutlierCount += 1;
        anomalies.push({
          modality,
          featureName: featKey,
          value: featVal,
          madDistance: updateResult.madDistance,
          flag: updateResult.anomalyFlag,
          reason: updateResult.reason,
        });
      } else {
        // Rejected due to low quality
        updatedBaselines.push(updateResult.updatedBaseline);
      }
    }
  }

  return {
    participantId,
    date,
    totalEvaluated: updatedBaselines.length,
    updatedCount,
    rejectedOutlierCount,
    hasAnomalies: anomalies.length > 0,
    anomalies,
    updatedBaselines,
    deviationRecords,
  };
}

// Dual CommonJS / ES Module export
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    TRACKED_MODALITIES,
    MODALITY_FEATURE_MAP,
    extractFeatureSeries,
    establishPersonalBaselines,
    processAdaptiveDay,
  };
}
