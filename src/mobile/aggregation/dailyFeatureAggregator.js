/**
 * MPF Mobile Extension — Daily Feature Aggregator (Phase 9)
 *
 * Combines all modality sessions recorded within a single calendar day into
 * a standardized daily feature representation:
 * - Aggregates multiple daily sessions using Median (central tendency) and IQR (variability).
 * - Flags significant inter-session disagreements across multiple tests.
 * - Filters out sessions with quality_score < 0.50 using qualityFilter.
 * - Tracks missing modalities without imputation using missingnessTracker.
 *
 * NON-NEGOTIABLE COMPLIANCE:
 * - NO DIAGNOSTIC CLAIMS: Strictly longitudinal feature aggregation.
 * - NO SENSOR OVERCLAIMING: Visual module is ocular/visual behavioral tracking, not retinal imaging.
 * - NO DATA FABRICATION: Missing features remain null, never imputed.
 */

import { filterSessionsByQuality, evaluateModalityQuality, calculateOverallQuality, getSessionQualityScore } from './qualityFilter.js';
import { trackMissingness, TRACKED_MODALITIES } from './missingnessTracker.js';

export const DISAGREEMENT_CV_THRESHOLD = 0.35;
export const DISAGREEMENT_IQR_REL_THRESHOLD = 0.40;

/**
 * Computes median of a numeric array.
 *
 * @param {Array<number>} values
 * @returns {number|null} Median value or null if empty.
 */
export function computeMedian(values) {
  if (!Array.isArray(values) || values.length === 0) return null;
  const filtered = values
    .map(v => Number(v))
    .filter(v => typeof v === 'number' && !Number.isNaN(v))
    .sort((a, b) => a - b);

  if (filtered.length === 0) return null;
  const mid = Math.floor(filtered.length / 2);
  const med = filtered.length % 2 === 0
    ? (filtered[mid - 1] + filtered[mid]) / 2.0
    : filtered[mid];

  return Number(med.toFixed(4));
}

/**
 * Computes interquartile range (IQR = Q75 - Q25) of a numeric array.
 *
 * @param {Array<number>} values
 * @returns {number|null} IQR value or null if insufficient data.
 */
export function computeIQR(values) {
  if (!Array.isArray(values) || values.length < 2) return 0.0;
  const filtered = values
    .map(v => Number(v))
    .filter(v => typeof v === 'number' && !Number.isNaN(v))
    .sort((a, b) => a - b);

  if (filtered.length < 2) return 0.0;
  if (filtered.length === 2) {
    return Number(Math.abs(filtered[1] - filtered[0]).toFixed(4));
  }

  const mid = Math.floor(filtered.length / 2);
  const lowerHalf = filtered.slice(0, mid);
  const upperHalf = filtered.length % 2 === 0 ? filtered.slice(mid) : filtered.slice(mid + 1);

  const q25 = computeMedian(lowerHalf);
  const q75 = computeMedian(upperHalf);

  if (q25 === null || q75 === null) return 0.0;
  return Number(Math.max(0.0, q75 - q25).toFixed(4));
}

/**
 * Computes arithmetic mean and standard deviation.
 *
 * @param {Array<number>} values
 * @returns {{ mean: number, std: number, cv: number }}
 */
export function computeDispersion(values) {
  const filtered = values
    .map(v => Number(v))
    .filter(v => typeof v === 'number' && !Number.isNaN(v));

  if (filtered.length === 0) return { mean: 0, std: 0, cv: 0 };
  const mean = filtered.reduce((a, b) => a + b, 0) / filtered.length;
  if (filtered.length < 2) return { mean, std: 0, cv: 0 };

  const variance = filtered.reduce((acc, v) => acc + Math.pow(v - mean, 2), 0) / (filtered.length - 1);
  const std = Math.sqrt(variance);
  const cv = mean !== 0 ? Math.abs(std / mean) : 0;

  return { mean, std, cv };
}

/**
 * Detects whether multiple sessions disagree significantly on a given feature.
 *
 * @param {Array<number>} values
 * @param {string} featureName
 * @param {number} [cvThreshold=DISAGREEMENT_CV_THRESHOLD]
 * @param {number} [iqrRelThreshold=DISAGREEMENT_IQR_REL_THRESHOLD]
 * @returns {Object} Disagreement report
 */
export function detectDisagreement(
  values,
  featureName,
  cvThreshold = DISAGREEMENT_CV_THRESHOLD,
  iqrRelThreshold = DISAGREEMENT_IQR_REL_THRESHOLD
) {
  const filtered = values
    .map(v => Number(v))
    .filter(v => typeof v === 'number' && !Number.isNaN(v));

  if (filtered.length < 2) {
    return { disagree: false, feature: featureName, reason: null };
  }

  const { mean, std, cv } = computeDispersion(filtered);
  const median = computeMedian(filtered);
  const iqr = computeIQR(filtered);
  const iqrRel = median !== 0 && median !== null ? Math.abs(iqr / median) : 0;

  const minVal = Math.min(...filtered);
  const maxVal = Math.max(...filtered);
  const rangeRel = mean !== 0 ? (maxVal - minVal) / Math.abs(mean) : 0;

  const cvExcess = cv > cvThreshold;
  const iqrExcess = iqrRel > iqrRelThreshold;
  const rangeExcess = rangeRel > 0.50 && filtered.length === 2;

  if (cvExcess || iqrExcess || rangeExcess) {
    return {
      disagree: true,
      feature: featureName,
      session_count: filtered.length,
      cv: Number(cv.toFixed(4)),
      iqr: Number(iqr.toFixed(4)),
      iqr_relative: Number(iqrRel.toFixed(4)),
      values: filtered,
      reason: `Significant session disagreement in ${featureName}: CV=${cv.toFixed(2)}, relative IQR=${iqrRel.toFixed(2)}`
    };
  }

  return {
    disagree: false,
    feature: featureName,
    cv: Number(cv.toFixed(4)),
    iqr: Number(iqr.toFixed(4)),
    reason: null
  };
}

/**
 * Aggregates typing sessions for a single day.
 *
 * @param {Array<Object>} sessions
 * @returns {Object|null} Aggregated typing features or null
 */
export function aggregateTyping(sessions) {
  if (!Array.isArray(sessions) || sessions.length === 0) return null;

  const speeds = [];
  const intervals = [];
  const corrections = [];
  const qualities = [];

  for (const s of sessions) {
    // typing_speed can be typing_speed or typing_speed_cpm
    const spd = s.typing_speed ?? s.typing_speed_cpm ?? s.speed;
    if (spd !== undefined && spd !== null) speeds.push(spd);

    // interval variability can be interval_variability, std_inter_key_interval, rhythm_variability
    const iv = s.interval_variability ?? s.std_inter_key_interval ?? s.rhythm_variability ?? s.iki_cv_pct;
    if (iv !== undefined && iv !== null) intervals.push(iv);

    // correction_rate or error_correction_rate
    const cr = s.correction_rate ?? s.error_correction_rate;
    if (cr !== undefined && cr !== null) corrections.push(cr);

    const q = getSessionQualityScore(s);
    qualities.push(q);
  }

  const disagreementFlags = [];
  const spdDis = detectDisagreement(speeds, 'typing_speed');
  if (spdDis.disagree) disagreementFlags.push(spdDis);

  const ivDis = detectDisagreement(intervals, 'interval_variability');
  if (ivDis.disagree) disagreementFlags.push(ivDis);

  return {
    features: {
      typing_speed: computeMedian(speeds),
      interval_variability: computeMedian(intervals),
      correction_rate: computeMedian(corrections),
      quality_score: computeMedian(qualities),
    },
    iqr: {
      typing_speed: computeIQR(speeds),
      interval_variability: computeIQR(intervals),
      correction_rate: computeIQR(corrections),
    },
    disagreements: disagreementFlags,
    session_count: sessions.length,
  };
}

/**
 * Aggregates voice sessions for a single day.
 *
 * @param {Array<Object>} sessions
 * @returns {Object|null} Aggregated voice features or null
 */
export function aggregateVoice(sessions) {
  if (!Array.isArray(sessions) || sessions.length === 0) return null;

  const jitters = [];
  const shimmers = [];
  const hnrs = [];
  const pitchMeans = [];
  const qualities = [];

  for (const s of sessions) {
    if (s.jitter !== undefined && s.jitter !== null) jitters.push(s.jitter);
    if (s.shimmer !== undefined && s.shimmer !== null) shimmers.push(s.shimmer);
    if (s.hnr !== undefined && s.hnr !== null) hnrs.push(s.hnr);
    if (s.pitch_mean !== undefined && s.pitch_mean !== null) pitchMeans.push(s.pitch_mean);
    qualities.push(getSessionQualityScore(s));
  }

  const disagreementFlags = [];
  const jDis = detectDisagreement(jitters, 'voice_jitter');
  if (jDis.disagree) disagreementFlags.push(jDis);

  const sDis = detectDisagreement(shimmers, 'voice_shimmer');
  if (sDis.disagree) disagreementFlags.push(sDis);

  return {
    features: {
      jitter: computeMedian(jitters),
      shimmer: computeMedian(shimmers),
      hnr: computeMedian(hnrs),
      pitch_mean: computeMedian(pitchMeans),
      quality_score: computeMedian(qualities),
    },
    iqr: {
      jitter: computeIQR(jitters),
      shimmer: computeIQR(shimmers),
      hnr: computeIQR(hnrs),
      pitch_mean: computeIQR(pitchMeans),
    },
    disagreements: disagreementFlags,
    session_count: sessions.length,
  };
}

/**
 * Aggregates motor sessions (walking, tapping, tremor) for a single day.
 *
 * @param {Array<Object>} sessions
 * @returns {Object|null} Aggregated motor features or null
 */
export function aggregateMotor(sessions) {
  if (!Array.isArray(sessions) || sessions.length === 0) return null;

  const cadences = [];
  const strideVariabilities = [];
  const tappingRates = [];
  const tremorFrequencies = [];
  const qualities = [];

  for (const s of sessions) {
    // Cadence
    if (s.cadence !== undefined && s.cadence !== null) {
      cadences.push(s.cadence);
    }
    // Stride variability
    const sv = s.stride_variability ?? s.stride_interval_variability ?? s.stride_interval_cv_pct;
    if (sv !== undefined && sv !== null) {
      strideVariabilities.push(sv);
    }
    // Tapping rate
    if (s.tapping_rate !== undefined && s.tapping_rate !== null) {
      tappingRates.push(s.tapping_rate);
    }
    // Tremor frequency
    const tf = s.tremor_frequency ?? s.tremor_freq_dominant_hz;
    if (tf !== undefined && tf !== null) {
      tremorFrequencies.push(tf);
    }
    qualities.push(getSessionQualityScore(s));
  }

  const disagreementFlags = [];
  const cadDis = detectDisagreement(cadences, 'motor_cadence');
  if (cadDis.disagree) disagreementFlags.push(cadDis);

  const tapDis = detectDisagreement(tappingRates, 'motor_tapping_rate');
  if (tapDis.disagree) disagreementFlags.push(tapDis);

  const tremDis = detectDisagreement(tremorFrequencies, 'motor_tremor_frequency');
  if (tremDis.disagree) disagreementFlags.push(tremDis);

  return {
    features: {
      cadence: computeMedian(cadences),
      stride_variability: computeMedian(strideVariabilities),
      tapping_rate: computeMedian(tappingRates),
      tremor_frequency: computeMedian(tremorFrequencies),
      quality_score: computeMedian(qualities),
    },
    iqr: {
      cadence: computeIQR(cadences),
      stride_variability: computeIQR(strideVariabilities),
      tapping_rate: computeIQR(tappingRates),
      tremor_frequency: computeIQR(tremorFrequencies),
    },
    disagreements: disagreementFlags,
    session_count: sessions.length,
  };
}

/**
 * Aggregates visual behavior sessions (blink, tracking, reaction) for a single day.
 *
 * @param {Array<Object>} sessions
 * @returns {Object|null} Aggregated visual features or null
 */
export function aggregateVisual(sessions) {
  if (!Array.isArray(sessions) || sessions.length === 0) return null;

  const blinkRates = [];
  const gazeStabilities = [];
  const reactionTimes = [];
  const qualities = [];

  for (const s of sessions) {
    if (s.blink_rate !== undefined && s.blink_rate !== null) {
      blinkRates.push(s.blink_rate);
    }
    if (s.gaze_stability !== undefined && s.gaze_stability !== null) {
      gazeStabilities.push(s.gaze_stability);
    }
    const rt = s.reaction_time ?? s.reaction_time_mean ?? s.saccade_latency_mean_ms;
    if (rt !== undefined && rt !== null) {
      reactionTimes.push(rt);
    }
    qualities.push(getSessionQualityScore(s));
  }

  const disagreementFlags = [];
  const bDis = detectDisagreement(blinkRates, 'visual_blink_rate');
  if (bDis.disagree) disagreementFlags.push(bDis);

  const gDis = detectDisagreement(gazeStabilities, 'visual_gaze_stability');
  if (gDis.disagree) disagreementFlags.push(gDis);

  const rDis = detectDisagreement(reactionTimes, 'visual_reaction_time');
  if (rDis.disagree) disagreementFlags.push(rDis);

  return {
    features: {
      blink_rate: computeMedian(blinkRates),
      gaze_stability: computeMedian(gazeStabilities),
      reaction_time: computeMedian(reactionTimes),
      quality_score: computeMedian(qualities),
    },
    iqr: {
      blink_rate: computeIQR(blinkRates),
      gaze_stability: computeIQR(gazeStabilities),
      reaction_time: computeIQR(reactionTimes),
    },
    disagreements: disagreementFlags,
    session_count: sessions.length,
  };
}

/**
 * Aggregates sleep questionnaire sessions for a single day.
 *
 * @param {Array<Object>} sessions
 * @returns {Object|null} Aggregated sleep features or null
 */
export function aggregateSleep(sessions) {
  if (!Array.isArray(sessions) || sessions.length === 0) return null;

  const durations = [];
  const sleepQualities = [];
  const scores = [];

  for (const s of sessions) {
    if (s.sleep_duration !== undefined && s.sleep_duration !== null) {
      durations.push(s.sleep_duration);
    }
    if (s.sleep_quality !== undefined && s.sleep_quality !== null) {
      sleepQualities.push(s.sleep_quality);
    }
    if (s.score !== undefined && s.score !== null) {
      scores.push(s.score);
    }
  }

  return {
    features: {
      sleep_duration: computeMedian(durations),
      sleep_quality: computeMedian(sleepQualities),
      score: computeMedian(scores),
    },
    iqr: {
      sleep_duration: computeIQR(durations),
      sleep_quality: computeIQR(sleepQualities),
      score: computeIQR(scores),
    },
    disagreements: [],
    session_count: sessions.length,
  };
}

/**
 * Master aggregation engine: evaluates daily sessions across all modalities,
 * applies quality filtering, tracks missingness, aggregates values via median/IQR,
 * and compiles session disagreement alerts.
 *
 * @param {Object} params
 * @param {string} params.participantId - UUID of the participant
 * @param {string} params.date - Date in YYYY-MM-DD format
 * @param {Object} params.sessions - Map of modality -> Array<Session>
 * @param {Object} [params.options] - Optional config
 * @returns {Object} Complete aggregation output
 */
export function aggregateDay({ participantId, date, sessions = {}, options = {} }) {
  if (!participantId) {
    throw new Error('participantId is mandatory for daily aggregation.');
  }
  if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date)) {
    throw new Error(`date must be in YYYY-MM-DD format; got "${date}".`);
  }

  // 1. Evaluate quality and partition sessions for each modality
  const modalityEvaluations = {};
  const passedSessionsMap = {};

  for (const modality of TRACKED_MODALITIES) {
    const rawSessions = sessions[modality] || [];
    const evalResult = evaluateModalityQuality(rawSessions);
    modalityEvaluations[modality] = evalResult;

    if (evalResult.status === 'valid') {
      const { passedSessions } = filterSessionsByQuality(rawSessions);
      passedSessionsMap[modality] = passedSessions;
    } else {
      passedSessionsMap[modality] = [];
    }
  }

  // 2. Track missingness and availability
  const missingness = trackMissingness(modalityEvaluations);

  // 3. Aggregate each modality using ONLY passed sessions
  const typingAgg = missingness.available_modalities.includes('typing')
    ? aggregateTyping(passedSessionsMap.typing)
    : null;

  const voiceAgg = missingness.available_modalities.includes('voice')
    ? aggregateVoice(passedSessionsMap.voice)
    : null;

  const motorAgg = missingness.available_modalities.includes('motor')
    ? aggregateMotor(passedSessionsMap.motor)
    : null;

  const visualAgg = missingness.available_modalities.includes('visual')
    ? aggregateVisual(passedSessionsMap.visual)
    : null;

  const sleepAgg = missingness.available_modalities.includes('sleep')
    ? aggregateSleep(passedSessionsMap.sleep)
    : null;

  // 4. Collect quality scores
  const qualityMap = {
    typing_quality: modalityEvaluations.typing.quality_score,
    voice_quality: modalityEvaluations.voice.quality_score,
    motor_quality: modalityEvaluations.motor.quality_score,
    visual_quality: modalityEvaluations.visual.quality_score,
  };
  const overallQuality = calculateOverallQuality(qualityMap);

  // 5. Consolidate disagreement flags and session IQRs
  const allDisagreements = [
    ...(typingAgg?.disagreements || []),
    ...(voiceAgg?.disagreements || []),
    ...(motorAgg?.disagreements || []),
    ...(visualAgg?.disagreements || []),
    ...(sleepAgg?.disagreements || []),
  ];

  const iqrSummary = {
    typing: typingAgg?.iqr || null,
    voice: voiceAgg?.iqr || null,
    motor: motorAgg?.iqr || null,
    visual: visualAgg?.iqr || null,
    sleep: sleepAgg?.iqr || null,
  };

  return {
    participant_id: participantId,
    date,
    features: {
      typing: typingAgg?.features || null,
      voice: voiceAgg?.features || null,
      motor: motorAgg?.features || null,
      visual: visualAgg?.features || null,
      sleep: sleepAgg?.features || null,
    },
    quality: {
      typing_quality: qualityMap.typing_quality,
      voice_quality: qualityMap.voice_quality,
      motor_quality: qualityMap.motor_quality,
      visual_quality: qualityMap.visual_quality,
      overall_quality: overallQuality,
    },
    missingness,
    iqr: iqrSummary,
    disagreements: allDisagreements,
    has_disagreements: allDisagreements.length > 0,
  };
}

// Dual CommonJS / ES Module export
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    DISAGREEMENT_CV_THRESHOLD,
    DISAGREEMENT_IQR_REL_THRESHOLD,
    computeMedian,
    computeIQR,
    computeDispersion,
    detectDisagreement,
    aggregateTyping,
    aggregateVoice,
    aggregateMotor,
    aggregateVisual,
    aggregateSleep,
    aggregateDay,
  };
}
