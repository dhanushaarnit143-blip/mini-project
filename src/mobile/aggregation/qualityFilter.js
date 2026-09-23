/**
 * MPF Mobile Extension — Quality Filter Module (Phase 9)
 *
 * Implements strict quality gating for mobile sensor sessions:
 * - Only includes sessions with quality_score >= 0.50.
 * - Excludes low-quality sessions (< 0.50) from baseline and daily aggregation.
 * - If all sessions for a modality are low quality, marks modality as "low_quality".
 * - Computes overall daily quality index across valid modalities.
 *
 * COMPLIANCE RULES:
 * - No diagnostic claims or assumptions.
 * - Research data provenance strictly tracked.
 */

export const MIN_QUALITY_THRESHOLD = 0.50;

/**
 * Validates whether a single session meets the minimum quality threshold.
 *
 * @param {Object} session - Modality session object.
 * @param {number} [threshold=MIN_QUALITY_THRESHOLD] - Cutoff threshold (default 0.50).
 * @returns {boolean} True if session quality is >= threshold.
 */
export function isSessionQualityAcceptable(session, threshold = MIN_QUALITY_THRESHOLD) {
  if (!session || typeof session !== 'object') {
    return false;
  }

  // Check quality_score or fallback score fields
  let score = null;
  if (typeof session.quality_score === 'number' && !Number.isNaN(session.quality_score)) {
    score = session.quality_score;
  } else if (typeof session.score === 'number' && !Number.isNaN(session.score)) {
    // For sleep sessions where score is 0-100, normalize if needed or if already 0-1
    score = session.score > 1.0 ? session.score / 100.0 : session.score;
  } else if (typeof session.signal_quality === 'number' && !Number.isNaN(session.signal_quality)) {
    score = session.signal_quality;
  }

  if (score === null || score < 0.0) {
    return false;
  }

  return score >= threshold;
}

/**
 * Extracts normalized quality score from a session.
 *
 * @param {Object} session
 * @returns {number} Quality score clamped to [0.0, 1.0]
 */
export function getSessionQualityScore(session) {
  if (!session || typeof session !== 'object') return 0.0;
  if (typeof session.quality_score === 'number' && !Number.isNaN(session.quality_score)) {
    return Math.max(0.0, Math.min(1.0, session.quality_score));
  }
  if (typeof session.score === 'number' && !Number.isNaN(session.score)) {
    const s = session.score > 1.0 ? session.score / 100.0 : session.score;
    return Math.max(0.0, Math.min(1.0, s));
  }
  if (typeof session.signal_quality === 'number' && !Number.isNaN(session.signal_quality)) {
    return Math.max(0.0, Math.min(1.0, session.signal_quality));
  }
  return 0.0;
}

/**
 * Partitions sessions into passed (quality >= threshold) and rejected (quality < threshold).
 *
 * @param {Array<Object>} sessions - List of sessions for a single modality.
 * @param {number} [threshold=MIN_QUALITY_THRESHOLD]
 * @returns {{ passedSessions: Array<Object>, rejectedSessions: Array<Object> }}
 */
export function filterSessionsByQuality(sessions, threshold = MIN_QUALITY_THRESHOLD) {
  if (!Array.isArray(sessions) || sessions.length === 0) {
    return { passedSessions: [], rejectedSessions: [] };
  }

  const passedSessions = [];
  const rejectedSessions = [];

  for (const session of sessions) {
    if (isSessionQualityAcceptable(session, threshold)) {
      passedSessions.push(session);
    } else {
      rejectedSessions.push({
        session,
        quality_score: getSessionQualityScore(session),
        rejection_reason: `Quality score ${getSessionQualityScore(session).toFixed(3)} is below minimum threshold ${threshold}`
      });
    }
  }

  return { passedSessions, rejectedSessions };
}

/**
 * Evaluates the overall quality state of a single modality for a given day.
 *
 * @param {Array<Object>} sessions - Sessions recorded for the modality.
 * @param {number} [threshold=MIN_QUALITY_THRESHOLD]
 * @returns {Object} Evaluation report containing status, qualityScore, counts, and reasons.
 */
export function evaluateModalityQuality(sessions, threshold = MIN_QUALITY_THRESHOLD) {
  if (!Array.isArray(sessions) || sessions.length === 0) {
    return {
      status: 'missing',
      quality_score: null,
      passed_count: 0,
      total_count: 0,
      rejected_count: 0,
      reasons: ['No sessions recorded for modality on this day.']
    };
  }

  const { passedSessions, rejectedSessions } = filterSessionsByQuality(sessions, threshold);

  if (passedSessions.length === 0) {
    // All sessions failed quality threshold
    const scores = sessions.map(s => getSessionQualityScore(s));
    scores.sort((a, b) => a - b);
    const medianScore = scores.length % 2 === 0
      ? (scores[scores.length / 2 - 1] + scores[scores.length / 2]) / 2
      : scores[Math.floor(scores.length / 2)];

    return {
      status: 'low_quality',
      quality_score: Number(medianScore.toFixed(4)),
      passed_count: 0,
      total_count: sessions.length,
      rejected_count: rejectedSessions.length,
      reasons: rejectedSessions.map(r => r.rejection_reason)
    };
  }

  // At least one session passed
  const passedScores = passedSessions.map(s => getSessionQualityScore(s));
  passedScores.sort((a, b) => a - b);
  const medianPassedScore = passedScores.length % 2 === 0
    ? (passedScores[passedScores.length / 2 - 1] + passedScores[passedScores.length / 2]) / 2
    : passedScores[Math.floor(passedScores.length / 2)];

  return {
    status: 'valid',
    quality_score: Number(medianPassedScore.toFixed(4)),
    passed_count: passedSessions.length,
    total_count: sessions.length,
    rejected_count: rejectedSessions.length,
    reasons: []
  };
}

/**
 * Computes overall daily quality index across all modalities.
 * Arithmetic mean of quality scores for modalities with status 'valid'.
 *
 * @param {Object} modalityQualityMap - Map of modality -> quality score (or null)
 * @returns {number} Overall daily quality index [0.0, 1.0]
 */
export function calculateOverallQuality(modalityQualityMap = {}) {
  if (!modalityQualityMap || typeof modalityQualityMap !== 'object') {
    return 0.0;
  }

  const validScores = [];
  const trackedKeys = ['typing_quality', 'voice_quality', 'motor_quality', 'visual_quality'];

  for (const key of trackedKeys) {
    const val = modalityQualityMap[key];
    if (typeof val === 'number' && !Number.isNaN(val) && val >= 0.0) {
      validScores.push(val);
    }
  }

  if (validScores.length === 0) {
    return 0.0;
  }

  const sum = validScores.reduce((acc, v) => acc + v, 0);
  return Number((sum / validScores.length).toFixed(4));
}

// Dual CommonJS / ES Module export
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    MIN_QUALITY_THRESHOLD,
    isSessionQualityAcceptable,
    getSessionQualityScore,
    filterSessionsByQuality,
    evaluateModalityQuality,
    calculateOverallQuality,
  };
}
