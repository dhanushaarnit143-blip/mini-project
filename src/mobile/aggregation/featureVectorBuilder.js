/**
 * MPF Mobile Extension — Feature Vector Builder (Phase 9)
 *
 * Assembles the standardized daily feature vector from aggregated modality features.
 * Enforces exact structural conformance to the MPF Mobile Data Schema.
 *
 * Standard Daily Feature Vector Specification:
 * {
 *   "participant_id": "...",
 *   "date": "YYYY-MM-DD",
 *   "typing": { "typing_speed": ..., "interval_variability": ..., "correction_rate": ..., "quality_score": ... },
 *   "voice": { "jitter": ..., "shimmer": ..., "hnr": ..., "pitch_mean": ..., "quality_score": ... },
 *   "motor": { "cadence": ..., "stride_variability": ..., "tapping_rate": ..., "tremor_frequency": ..., "quality_score": ... },
 *   "visual": { "blink_rate": ..., "gaze_stability": ..., "reaction_time": ..., "quality_score": ... },
 *   "sleep": { "sleep_duration": ..., "sleep_quality": ..., "score": ... },
 *   "quality": { "typing_quality": ..., "voice_quality": ..., "motor_quality": ..., "visual_quality": ..., "overall_quality": ... },
 *   "feature_version": "1.0",
 *   "available_modalities": [...],
 *   "missing_modalities": [...]
 * }
 */

import { aggregateDay } from './dailyFeatureAggregator.js';
import { validateNoImputation } from './missingnessTracker.js';

export const CURRENT_FEATURE_VERSION = '1.0';

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const DATE_REGEX = /^\d{4}-\d{2}-\d{2}$/;

const DISALLOWED_DIAGNOSTIC_TERMS = [
  'parkinson\'s' + ' detected',
  'you have ' + 'parkinson\'s',
  'diagnosed ' + 'parkinson',
  'confirmed ' + 'parkinson',
  'parkinson\'s ' + 'progression',
];

/**
 * Builds a standardized daily feature vector from pre-aggregated outputs or raw sessions.
 *
 * @param {Object} params
 * @param {string} params.participantId - UUID of participant
 * @param {string} params.date - Date (YYYY-MM-DD)
 * @param {Object} [params.sessions] - Raw session collections by modality
 * @param {Object} [params.aggregationResult] - Pre-computed aggregation result from aggregateDay()
 * @param {string} [params.featureVersion=CURRENT_FEATURE_VERSION]
 * @returns {Object} Standardized daily feature vector
 */
export function buildDailyFeatureVector({
  participantId,
  date,
  sessions = null,
  aggregationResult = null,
  featureVersion = CURRENT_FEATURE_VERSION,
}) {
  if (!participantId || !UUID_REGEX.test(participantId)) {
    throw new Error(`participantId must be a valid UUID; received "${participantId}".`);
  }
  if (!date || !DATE_REGEX.test(date)) {
    throw new Error(`date must be in YYYY-MM-DD format; received "${date}".`);
  }

  const agg = aggregationResult || aggregateDay({ participantId, date, sessions: sessions || {} });

  const vector = {
    participant_id: participantId,
    date,
    typing: agg.features.typing,
    voice: agg.features.voice,
    motor: agg.features.motor,
    visual: agg.features.visual,
    sleep: agg.features.sleep,
    quality: {
      typing_quality: agg.quality.typing_quality,
      voice_quality: agg.quality.voice_quality,
      motor_quality: agg.quality.motor_quality,
      visual_quality: agg.quality.visual_quality,
      overall_quality: agg.quality.overall_quality,
    },
    feature_version: featureVersion,
    available_modalities: agg.missingness.available_modalities,
    missing_modalities: agg.missingness.missing_modalities,
  };

  // Optional audit metadata attached without modifying core vector keys
  if (agg.has_disagreements) {
    vector.disagreement_flags = agg.disagreements;
  }
  if (agg.missingness.low_quality_modalities.length > 0) {
    vector.low_quality_modalities = agg.missingness.low_quality_modalities;
  }

  return vector;
}

/**
 * Transforms a daily feature vector into a payload suitable for Supabase `daily_features` table.
 *
 * @param {Object} vector - Daily feature vector
 * @returns {Object} Database insertion record
 */
export function toSupabaseRecord(vector) {
  if (!vector || typeof vector !== 'object') {
    throw new Error('Valid daily feature vector is required.');
  }

  return {
    participant_id: vector.participant_id,
    date: vector.date,
    typing_features: vector.typing || null,
    voice_features: vector.voice || null,
    motor_features: vector.motor || null,
    visual_features: vector.visual || null,
    sleep_features: vector.sleep || null,
    data_quality: {
      ...vector.quality,
      available_modalities: vector.available_modalities,
      missing_modalities: vector.missing_modalities,
      low_quality_modalities: vector.low_quality_modalities || [],
      disagreement_flags: vector.disagreement_flags || [],
    },
    feature_version: vector.feature_version || CURRENT_FEATURE_VERSION,
  };
}

/**
 * Validates a daily feature vector against schema, ranges, and compliance rules.
 *
 * @param {Object} vector
 * @returns {{ valid: boolean, errors: Array<string> }}
 */
export function validateDailyFeatureVector(vector) {
  const errors = [];

  if (!vector || typeof vector !== 'object') {
    return { valid: false, errors: ['Vector must be a non-null object.'] };
  }

  // 1. Participant UUID
  if (!vector.participant_id || !UUID_REGEX.test(vector.participant_id)) {
    errors.push(`Invalid participant_id: must be a valid UUID; got "${vector.participant_id}".`);
  }

  // 2. Date
  if (!vector.date || !DATE_REGEX.test(vector.date)) {
    errors.push(`Invalid date: must be YYYY-MM-DD; got "${vector.date}".`);
  }

  // 3. Feature Version
  if (!vector.feature_version || typeof vector.feature_version !== 'string') {
    errors.push('feature_version is mandatory and must be a string.');
  }

  // 4. Modality arrays
  if (!Array.isArray(vector.available_modalities)) {
    errors.push('available_modalities must be an array.');
  }
  if (!Array.isArray(vector.missing_modalities)) {
    errors.push('missing_modalities must be an array.');
  }

  // 5. Non-imputation check
  const nonImputationCheck = validateNoImputation(vector);
  if (!nonImputationCheck.valid) {
    errors.push(...nonImputationCheck.errors);
  }

  // 6. Quality block validation
  if (!vector.quality || typeof vector.quality !== 'object') {
    errors.push('quality object is required.');
  } else {
    const oq = vector.quality.overall_quality;
    if (typeof oq !== 'number' || oq < 0.0 || oq > 1.0) {
      errors.push(`overall_quality must be between 0.0 and 1.0; got "${oq}".`);
    }
  }

  // 7. Disallowed diagnostic terminology check
  const vectorStr = JSON.stringify(vector).toLowerCase();
  for (const disallowed of DISALLOWED_DIAGNOSTIC_TERMS) {
    if (vectorStr.includes(disallowed)) {
      errors.push(`Diagnostic claim violation: contains disallowed phrase "${disallowed}".`);
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
    CURRENT_FEATURE_VERSION,
    buildDailyFeatureVector,
    toSupabaseRecord,
    validateDailyFeatureVector,
  };
}
