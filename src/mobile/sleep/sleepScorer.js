/**
 * MPF Mobile Extension — Sleep & RBD Scorer (Phase 8)
 *
 * Computes standardized sleep health scores and longitudinal probable RBD indicators
 * from the short daily sleep questionnaire.
 *
 * CRITICAL NON-NEGOTIABLE COMPLIANCE RULES:
 * 1. NO DIAGNOSTIC CLAIMS:
 *    - Never make definitive diagnosis or disease progression claims.
 *    - Always say: "Self-reported sleep movement pattern noted", "Deviation from personal baseline",
 *                  "Research screening result — not a clinical diagnosis".
 * 2. DISTINCTION FROM CLINICAL RBD:
 *    - Self-report is NOT equivalent to polysomnography-confirmed RBD or video-confirmed dream enactment.
 *    - Strictly label all outputs as "Self-reported sleep behavior", "Questionnaire-based indicator",
 *      or "Probable RBD pattern (self-report)".
 * 3. SHORT QUESTIONNAIRE DESIGN:
 *    - 3-5 questions max; does NOT repeat long clinical questionnaires (e.g. 50-item PSQI).
 * 4. VERSIONED REPRODUCIBILITY:
 *    - questionnaire_version: "1.0"
 *    - scorer_version: "1.0"
 */

export const QUESTIONNAIRE_VERSION = '1.0';
export const SCORER_VERSION = '1.0';

// ── Standard Compliance Labels ────────────────────────────────────────────────
export const SLEEP_LABELS = {
  MOVEMENT_NOTED: 'Self-reported sleep movement pattern noted',
  NO_PATTERN: 'No pattern detected',
  PROVENANCE: 'Self-reported sleep behavior',
  INDICATOR: 'Questionnaire-based indicator',
  PROBABLE_RBD: 'Probable RBD pattern (self-report)',
  RESEARCH_DISCLAIMER: 'Research screening result — not a clinical diagnosis',
  BASELINE_DEVIATION: 'Progressive deviation from personal baseline',
};

// ── Movement Response Enums ───────────────────────────────────────────────────
export const MOVEMENT_RESPONSES = {
  YES: 'yes',
  NO: 'no',
  NOT_SURE: 'not_sure',
  DONT_KNOW: 'dont_know',
};

export const VALID_MOVEMENT_RESPONSES = Object.values(MOVEMENT_RESPONSES);

/**
 * Computes a standardized sleep score from 0 to 100.
 * Higher score = better sleep / lower concern.
 *
 * Subscore weights (Total = 100):
 * - Duration subscore: 0-30 points (optimal 7.0-9.0 hours)
 * - Quality subscore:  0-30 points (scale 1-5, linear)
 * - Movement subscore: 0-25 points (No=25, Not sure/Don't know=15, Yes=0)
 * - Daytime sleepiness:0-15 points (scale 1-5, inverted linear)
 *
 * @param {Object} params
 * @param {number} params.sleepDuration - Hours slept (0 - 14)
 * @param {number} params.sleepQuality - Rating 1 (Very poor) to 5 (Excellent)
 * @param {boolean|string} params.unusualMovement - Boolean or string ('yes', 'no', 'not_sure', 'dont_know')
 * @param {number} params.daytimeSleepiness - Rating 1 (Not at all) to 5 (Extremely)
 * @returns {Object} Score breakdown and composite score
 */
export function computeSleepScore({
  sleepDuration,
  sleepQuality,
  unusualMovement,
  daytimeSleepiness,
}) {
  const duration = Number(sleepDuration);
  const quality = Number(sleepQuality);
  const sleepiness = Number(daytimeSleepiness);

  if (Number.isNaN(duration) || duration < 0 || duration > 24) {
    throw new Error(`sleepDuration must be a number between 0 and 24; received: ${sleepDuration}`);
  }
  if (Number.isNaN(quality) || quality < 1 || quality > 5) {
    throw new Error(`sleepQuality must be a number between 1 and 5; received: ${sleepQuality}`);
  }
  if (Number.isNaN(sleepiness) || sleepiness < 1 || sleepiness > 5) {
    throw new Error(`daytimeSleepiness must be a number between 1 and 5; received: ${daytimeSleepiness}`);
  }

  // 1. Duration subscore (0-30 points)
  let durationScore = 0;
  if (duration >= 7.0 && duration <= 9.0) {
    durationScore = 30.0;
  } else if ((duration >= 6.5 && duration < 7.0) || (duration > 9.0 && duration <= 9.5)) {
    durationScore = 26.0;
  } else if ((duration >= 6.0 && duration < 6.5) || (duration > 9.5 && duration <= 10.0)) {
    durationScore = 22.0;
  } else if ((duration >= 5.0 && duration < 6.0) || (duration > 10.0 && duration <= 11.0)) {
    durationScore = 15.0;
  } else if ((duration >= 4.0 && duration < 5.0) || (duration > 11.0 && duration <= 12.0)) {
    durationScore = 8.0;
  } else {
    durationScore = 0.0;
  }

  // 2. Quality subscore (0-30 points)
  const qualityScore = Math.max(0, Math.min(30, ((quality - 1) / 4) * 30.0));

  // 3. Movement / Dream enactment subscore (0-25 points)
  let movementScore = 25.0;
  const isYes =
    unusualMovement === true ||
    (typeof unusualMovement === 'string' && unusualMovement.toLowerCase() === MOVEMENT_RESPONSES.YES);
  const isUncertain =
    typeof unusualMovement === 'string' &&
    (unusualMovement.toLowerCase() === MOVEMENT_RESPONSES.NOT_SURE ||
      unusualMovement.toLowerCase() === MOVEMENT_RESPONSES.DONT_KNOW);

  if (isYes) {
    movementScore = 0.0;
  } else if (isUncertain) {
    movementScore = 15.0;
  } else {
    movementScore = 25.0;
  }

  // 4. Daytime sleepiness subscore (0-15 points)
  const sleepinessScore = Math.max(0, Math.min(15, ((5 - sleepiness) / 4) * 15.0));

  // Composite score (0-100)
  const totalScore = Math.round((durationScore + qualityScore + movementScore + sleepinessScore) * 10) / 10;
  const clampedScore = Math.max(0, Math.min(100, totalScore));

  return {
    score: clampedScore,
    breakdown: {
      duration_score: durationScore,
      quality_score: Math.round(qualityScore * 10) / 10,
      movement_score: movementScore,
      sleepiness_score: Math.round(sleepinessScore * 10) / 10,
    },
    version: SCORER_VERSION,
    labels: {
      provenance: SLEEP_LABELS.PROVENANCE,
      disclaimer: SLEEP_LABELS.RESEARCH_DISCLAIMER,
    },
  };
}

/**
 * Evaluates longitudinal RBD-related concerns over a multi-day rolling window (e.g. 7 days).
 *
 * Rule:
 * If Q3 ("unusual movements, talking, shouting, or acting out dreams") is "Yes" on
 * multiple days (>= 2) within a 7-day period:
 * -> Flags "Self-reported sleep movement pattern noted".
 * -> Does NOT diagnose RBD.
 *
 * @param {Array<Object>} sessions - List of sleep session objects containing timestamp and movement response
 * @param {number} [windowDays=7] - Rolling window duration in days
 * @param {number} [thresholdCount=2] - Number of positive reports required to trigger the flag
 * @returns {Object} Longitudinal evaluation report
 */
export function evaluateRbdConcernWindow(sessions = [], windowDays = 7, thresholdCount = 2) {
  if (!Array.isArray(sessions)) {
    throw new Error('sessions must be an array.');
  }

  const now = new Date();
  const cutoff = new Date(now.getTime() - windowDays * 24 * 60 * 60 * 1000);

  // Filter valid sessions within the window
  const recentSessions = sessions.filter((s) => {
    if (!s || !s.timestamp) return false;
    const sessionTime = new Date(s.timestamp);
    return !Number.isNaN(sessionTime.getTime()) && sessionTime >= cutoff;
  });

  // Count positive reports (by distinct date if multiple on same day)
  const positiveDays = new Set();
  recentSessions.forEach((s) => {
    const isYes =
      s.unusual_movement_self_report === true ||
      (typeof s.movement_response === 'string' && s.movement_response.toLowerCase() === MOVEMENT_RESPONSES.YES);

    if (isYes) {
      const dateKey = new Date(s.timestamp).toISOString().split('T')[0];
      positiveDays.add(dateKey);
    }
  });

  const positiveCount = positiveDays.size;
  const isFlagged = positiveCount >= thresholdCount;

  return {
    flagged: isFlagged,
    positive_days_count: positiveCount,
    threshold: thresholdCount,
    window_days: windowDays,
    evaluated_sessions_count: recentSessions.length,
    label: isFlagged ? SLEEP_LABELS.MOVEMENT_NOTED : SLEEP_LABELS.NO_PATTERN,
    provenance: SLEEP_LABELS.PROBABLE_RBD,
    indicator_type: SLEEP_LABELS.INDICATOR,
    disclaimer: SLEEP_LABELS.RESEARCH_DISCLAIMER,
    clinical_distinction:
      'This evaluation is based solely on daily self-reported questionnaire answers. ' +
      'It does NOT substitute for polysomnography, video EEG, or formal neurological diagnosis.',
  };
}
