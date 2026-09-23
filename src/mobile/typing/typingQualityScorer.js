/**
 * MPF Mobile Extension — Typing Quality Scorer
 * 
 * Evaluates session validity and data fidelity across 5 standardized quality criteria:
 * 1. Task completed (+0.30)
 * 2. Sufficient keystroke sample size (> 20 keystrokes) (+0.20)
 * 3. No abnormal interruptions (no pause > 10,000ms) (+0.20)
 * 4. Reasonable typing speed (> 0.5 characters/sec) (+0.15)
 * 5. No excessive corrections (<= 50% error/correction rate) (+0.15)
 * 
 * BASELINE ENGINE GATING RULE:
 * Sessions with quality_score < 0.50 are strictly rejected from baseline updates.
 */

export const MIN_BASELINE_QUALITY_THRESHOLD = 0.50;
export const MIN_KEYSTROKE_COUNT = 20;
export const MIN_TYPING_SPEED_CPS = 0.50;
export const MAX_ALLOWED_INTERRUPTION_MS = 10000; // 10 seconds
export const MAX_ALLOWED_CORRECTION_RATIO = 0.50;

export class TypingQualityScorer {
  /**
   * Computes standardized quality score and evaluates baseline eligibility.
   * @param {Object} params
   * @param {boolean} params.completed - Whether task was fully completed
   * @param {Array<Object>} params.timingEvents - Sequence of timing records
   * @param {number} params.typingSpeed - Extracted typing speed (chars/sec)
   * @param {number} [params.keystrokeCount] - Total keystrokes
   * @param {number} [params.correctionCount] - Total backspaces/corrections
   * @returns {Object} Quality breakdown and overall score
   */
  static calculateQualityScore(params) {
    if (!params) {
      return {
        quality_score: 0.0,
        is_baseline_eligible: false,
        breakdown: {
          task_completed: 0.0,
          sufficient_samples: 0.0,
          no_abnormal_interruptions: 0.0,
          reasonable_speed: 0.0,
          no_excessive_corrections: 0.0
        },
        rejection_reasons: ["Missing session metrics"]
      };
    }

    const {
      completed = false,
      timingEvents = [],
      typingSpeed = 0.0,
      keystrokeCount = timingEvents.length,
      correctionCount = timingEvents.filter(e => e.isCorrection).length
    } = params;

    const rejectionReasons = [];
    const breakdown = {
      task_completed: 0.0,
      sufficient_samples: 0.0,
      no_abnormal_interruptions: 0.0,
      reasonable_speed: 0.0,
      no_excessive_corrections: 0.0
    };

    // 1. Task completed (+0.30)
    if (completed) {
      breakdown.task_completed = 0.30;
    } else {
      rejectionReasons.push("Task was not completed");
    }

    // 2. Sufficient samples: keystrokes > 20 (+0.20)
    if (keystrokeCount > MIN_KEYSTROKE_COUNT) {
      breakdown.sufficient_samples = 0.20;
    } else {
      rejectionReasons.push(`Insufficient keystrokes: ${keystrokeCount} <= ${MIN_KEYSTROKE_COUNT}`);
    }

    // 3. No abnormal interruptions (+0.20)
    // Check if any IKI or pause exceeds maximum acceptable threshold (10 seconds)
    const hasAbnormalInterruption = timingEvents.some(
      event => (event.interKeyInterval || 0) > MAX_ALLOWED_INTERRUPTION_MS
    );
    if (!hasAbnormalInterruption && keystrokeCount > 0) {
      breakdown.no_abnormal_interruptions = 0.20;
    } else if (hasAbnormalInterruption) {
      rejectionReasons.push("Abnormal interruption detected (pause > 10s)");
    }

    // 4. Reasonable typing speed > 0.5 chars/sec (+0.15)
    if (typingSpeed > MIN_TYPING_SPEED_CPS) {
      breakdown.reasonable_speed = 0.15;
    } else {
      rejectionReasons.push(`Typing speed too low: ${typingSpeed} <= ${MIN_TYPING_SPEED_CPS} chars/sec`);
    }

    // 5. No excessive corrections: <= 50% error rate (+0.15)
    const errorRatio = keystrokeCount > 0 ? (correctionCount / keystrokeCount) : 0;
    if (errorRatio <= MAX_ALLOWED_CORRECTION_RATIO && keystrokeCount > 0) {
      breakdown.no_excessive_corrections = 0.15;
    } else if (errorRatio > MAX_ALLOWED_CORRECTION_RATIO) {
      rejectionReasons.push(`Excessive error rate: ${(errorRatio * 100).toFixed(1)}% > 50%`);
    }

    // Compute aggregate quality score (0.0 to 1.0)
    const rawScore = 
      breakdown.task_completed +
      breakdown.sufficient_samples +
      breakdown.no_abnormal_interruptions +
      breakdown.reasonable_speed +
      breakdown.no_excessive_corrections;

    const qualityScore = Number(Math.min(1.0, Math.max(0.0, rawScore)).toFixed(3));
    const isBaselineEligible = qualityScore >= MIN_BASELINE_QUALITY_THRESHOLD;

    if (!isBaselineEligible && rejectionReasons.length === 0) {
      rejectionReasons.push(`Aggregate quality score ${qualityScore} is below baseline threshold ${MIN_BASELINE_QUALITY_THRESHOLD}`);
    }

    return {
      quality_score: qualityScore,
      is_baseline_eligible: isBaselineEligible,
      min_threshold: MIN_BASELINE_QUALITY_THRESHOLD,
      breakdown,
      rejection_reasons: rejectionReasons
    };
  }
}
