/**
 * MPF Mobile Extension — Visual Quality Scorer (Phase 7)
 *
 * Implements the standard 5-factor quality scoring rubric for ocular/visual tasks:
 *   1. Face detected throughout task:     +0.3
 *   2. Good lighting conditions:           +0.2
 *   3. Tracking confidence high:           +0.2
 *   4. Task completed:                     +0.2
 *   5. No excessive head movement:         +0.1
 *   Total maximum score:                    1.0
 *
 * SESSIONS WITH quality_score < 0.50 ARE FLAGGED AS INELIGIBLE FOR BASELINE CALCULATION.
 *
 * COMPLIANCE:
 *   - "Ocular/Visual Behavior Module" — NOT retinal imaging.
 *   - "Research screening result — not a clinical diagnosis."
 *   - "Deviation from personal baseline."
 */

export const MIN_BASELINE_QUALITY_THRESHOLD = 0.50;

// Standard task duration targets (in seconds)
export const TASK_DURATION_TARGETS = {
  tracking: 20, // 20s visual tracking
  blink:    30, // 30s natural blink observation
  reaction: 25, // 25s visual reaction time
};

export class VisualQualityScorer {
  /**
   * Scores an ocular/visual behavior session based on the 5-factor rubric.
   *
   * @param {Object} params
   * @param {string} params.taskType - 'tracking' | 'blink' | 'reaction'
   * @param {number} params.actualDurationSec - Duration of task in seconds
   * @param {number} [params.targetDurationSec] - Target duration in seconds
   * @param {number} params.faceDetectedRatio - Fraction of time face detected [0, 1]
   * @param {number} params.goodLightingRatio - Fraction of time lighting acceptable [0, 1]
   * @param {number} params.meanConfidence - Average tracking confidence [0, 1]
   * @param {number} params.headDisplacement - Normalized head movement displacement [0, 1]
   * @returns {Object} Quality score breakdown and baseline eligibility
   */
  static scoreSession({
    taskType = 'tracking',
    actualDurationSec = 0,
    targetDurationSec = null,
    faceDetectedRatio = 1.0,
    goodLightingRatio = 1.0,
    meanConfidence = 0.90,
    headDisplacement = 0.02,
  }) {
    const targetSec = targetDurationSec || TASK_DURATION_TARGETS[taskType] || 20;
    const breakdown = {
      face_detected: 0.0,
      good_lighting: 0.0,
      tracking_confidence: 0.0,
      task_completed: 0.0,
      head_stability: 0.0,
    };
    const rejectionReasons = [];

    // Factor 1: Face detected throughout task (+0.3)
    // Full credit if face detected >= 85% of frames; scaled proportionally
    if (faceDetectedRatio >= 0.85) {
      breakdown.face_detected = 0.3;
    } else if (faceDetectedRatio >= 0.50) {
      breakdown.face_detected = Number(((faceDetectedRatio / 0.85) * 0.3).toFixed(2));
      rejectionReasons.push(`Face lost during ${Math.round((1 - faceDetectedRatio) * 100)}% of the task`);
    } else {
      breakdown.face_detected = 0.0;
      rejectionReasons.push(`Face undetectable for majority of task (${Math.round((1 - faceDetectedRatio) * 100)}% lost)`);
    }

    // Factor 2: Good lighting conditions (+0.2)
    // Full credit if good lighting >= 80% of frames
    if (goodLightingRatio >= 0.80) {
      breakdown.good_lighting = 0.2;
    } else if (goodLightingRatio >= 0.50) {
      breakdown.good_lighting = Number(((goodLightingRatio / 0.80) * 0.2).toFixed(2));
      rejectionReasons.push('Suboptimal lighting detected (too dark or backlit)');
    } else {
      breakdown.good_lighting = 0.0;
      rejectionReasons.push('Poor lighting conditions (insufficient facial exposure)');
    }

    // Factor 3: Tracking confidence high (+0.2)
    // Full credit if mean confidence >= 0.70
    if (meanConfidence >= 0.70) {
      breakdown.tracking_confidence = 0.2;
    } else if (meanConfidence >= 0.40) {
      breakdown.tracking_confidence = Number(((meanConfidence / 0.70) * 0.2).toFixed(2));
      rejectionReasons.push(`Low landmark tracking confidence (${(meanConfidence * 100).toFixed(0)}%)`);
    } else {
      breakdown.tracking_confidence = 0.0;
      rejectionReasons.push('Unreliable facial landmark estimation');
    }

    // Factor 4: Task completed (+0.2)
    // Full credit if actual duration >= 85% of target
    const completionRatio = targetSec > 0 ? actualDurationSec / targetSec : 0;
    if (completionRatio >= 0.85) {
      breakdown.task_completed = 0.2;
    } else if (completionRatio >= 0.50) {
      breakdown.task_completed = Number(((completionRatio / 0.85) * 0.2).toFixed(2));
      rejectionReasons.push(`Task stopped early (${actualDurationSec.toFixed(1)}s of ${targetSec}s target)`);
    } else {
      breakdown.task_completed = 0.0;
      rejectionReasons.push(`Task severely truncated (${actualDurationSec.toFixed(1)}s recorded)`);
    }

    // Factor 5: No excessive head movement (+0.1)
    // Full credit if displacement <= 0.05 normalized screen units
    if (headDisplacement <= 0.05) {
      breakdown.head_stability = 0.1;
    } else if (headDisplacement <= 0.12) {
      breakdown.head_stability = 0.05;
      rejectionReasons.push('Moderate head movement detected during fixation');
    } else {
      breakdown.head_stability = 0.0;
      rejectionReasons.push('Excessive head motion contaminated eye tracking');
    }

    const rawScore = Object.values(breakdown).reduce((sum, v) => sum + v, 0);
    const qualityScore = Number(Math.min(1.0, Math.max(0.0, rawScore)).toFixed(2));
    const isBaselineEligible = qualityScore >= MIN_BASELINE_QUALITY_THRESHOLD;

    return {
      quality_score: qualityScore,
      is_baseline_eligible: isBaselineEligible,
      breakdown,
      rejection_reasons: rejectionReasons,
      disclaimer: 'Research screening result — not a clinical diagnosis.',
    };
  }
}
