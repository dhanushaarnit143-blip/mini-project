/**
 * MPF Mobile Extension — Motor Quality Scorer (Phase 6)
 *
 * Evaluates per-task session quality using task-specific standardized rubrics.
 * Each criterion contributes a fixed weight toward the total quality score (0-1).
 *
 * Walking rubric:
 *   Sensor available:            +0.3
 *   Task completed (full 30s):   +0.3
 *   Sufficient steps (> 10):     +0.2
 *   Signal quality acceptable:   +0.2
 *
 * Tapping rubric:
 *   Task completed:              +0.3
 *   Sufficient taps (> 10):      +0.3
 *   No abnormal interruptions:   +0.2
 *   Reasonable tap rate:         +0.2
 *
 * Tremor rubric:
 *   Task completed:              +0.3
 *   Phone held relatively still: +0.3
 *   Sufficient signal quality:   +0.2
 *   No excessive movement:       +0.2
 *
 * BASELINE GATING:
 *   Sessions with quality_score < 0.50 are flagged and NOT fed into personal baseline.
 */

export const MIN_BASELINE_QUALITY_THRESHOLD = 0.50;

// Walking thresholds
const WALKING_MIN_DURATION_SEC = 25;     // must complete at least 25 of 30 seconds
const WALKING_MIN_STEPS = 10;
const WALKING_MIN_CADENCE = 30;          // 30 steps/min minimum reasonable
const WALKING_MIN_REGULARITY = 0.3;     // autocorrelation-based

// Tapping thresholds
const TAPPING_MIN_DURATION_SEC = 8;     // at least 8 of 10-20 seconds
const TAPPING_MIN_TAPS = 10;
const TAPPING_MIN_RATE = 0.5;           // taps/sec — below this is near-absent
const TAPPING_MAX_RATE = 15;            // taps/sec — above this is implausible
const TAPPING_MAX_PAUSE_RATIO = 0.3;   // ITI variability proxy for interruptions

// Tremor thresholds
const TREMOR_MIN_DURATION_SEC = 8;      // at least 8 of 10 seconds
const TREMOR_MAX_MOVEMENT_AMPLITUDE = 2.0; // m/s² — above = not "held still"
const TREMOR_MAX_AMPLITUDE_MOVEMENT = 5.0; // artifact rejection ceiling

/**
 * Quality scorer for all three motor task types.
 */
export class MotorQualityScorer {
  /**
   * Compute quality score for a walking session.
   *
   * @param {Object} p
   * @param {boolean} p.sensorAvailable - Was DeviceMotion available?
   * @param {number}  p.durationSeconds - Actual task duration collected.
   * @param {number}  p.stepCount       - Number of steps detected.
   * @param {number|null} p.cadence     - Cadence in steps/min.
   * @param {number}  p.movementRegularity - Autocorrelation score (0-1).
   * @returns {Object} Scored quality result.
   */
  static scoreWalking({ sensorAvailable, durationSeconds, stepCount, cadence, movementRegularity }) {
    const breakdown = {
      sensor_available: 0,
      task_completed: 0,
      sufficient_steps: 0,
      signal_quality: 0,
    };
    const rejectionReasons = [];

    // 1. Sensor available: +0.3
    if (sensorAvailable) {
      breakdown.sensor_available = 0.3;
    } else {
      rejectionReasons.push('DeviceMotion sensor unavailable on this device/browser.');
    }

    // 2. Task completed (>= 25s): +0.3
    if (durationSeconds >= WALKING_MIN_DURATION_SEC) {
      breakdown.task_completed = 0.3;
    } else {
      rejectionReasons.push(`Task too short: ${durationSeconds.toFixed(1)}s < ${WALKING_MIN_DURATION_SEC}s required.`);
    }

    // 3. Sufficient steps detected (> 10): +0.2
    if (stepCount > WALKING_MIN_STEPS) {
      breakdown.sufficient_steps = 0.2;
    } else {
      rejectionReasons.push(`Insufficient steps detected: ${stepCount} <= ${WALKING_MIN_STEPS}.`);
    }

    // 4. Signal quality (cadence in plausible range AND regularity): +0.2
    const cadenceOk = cadence !== null && cadence >= WALKING_MIN_CADENCE && cadence <= 200;
    const regularityOk = movementRegularity !== null && movementRegularity >= WALKING_MIN_REGULARITY;
    if (cadenceOk && regularityOk) {
      breakdown.signal_quality = 0.2;
    } else {
      if (!cadenceOk) rejectionReasons.push(`Cadence out of range: ${cadence} steps/min.`);
      if (!regularityOk) rejectionReasons.push(`Low movement regularity: ${movementRegularity}.`);
    }

    return _buildResult('walking', breakdown, rejectionReasons);
  }

  /**
   * Compute quality score for a tapping session.
   *
   * @param {Object} p
   * @param {number}  p.durationSeconds          - Actual task duration.
   * @param {number}  p.tapCount                 - Total valid taps.
   * @param {number|null} p.tappingRate           - Taps per second.
   * @param {number|null} p.interTapIntervalVariability - CV of ITIs.
   * @returns {Object} Scored quality result.
   */
  static scoreTapping({ durationSeconds, tapCount, tappingRate, interTapIntervalVariability }) {
    const breakdown = {
      task_completed: 0,
      sufficient_taps: 0,
      no_abnormal_interruptions: 0,
      reasonable_tap_rate: 0,
    };
    const rejectionReasons = [];

    // 1. Task completed (>= 8s): +0.3
    if (durationSeconds >= TAPPING_MIN_DURATION_SEC) {
      breakdown.task_completed = 0.3;
    } else {
      rejectionReasons.push(`Tapping task too short: ${durationSeconds.toFixed(1)}s < ${TAPPING_MIN_DURATION_SEC}s.`);
    }

    // 2. Sufficient taps (> 10): +0.3
    if (tapCount > TAPPING_MIN_TAPS) {
      breakdown.sufficient_taps = 0.3;
    } else {
      rejectionReasons.push(`Insufficient taps: ${tapCount} <= ${TAPPING_MIN_TAPS}.`);
    }

    // 3. No abnormal interruptions (ITI variability not extreme): +0.2
    const noInterruptions = interTapIntervalVariability === null ||
      interTapIntervalVariability <= TAPPING_MAX_PAUSE_RATIO;
    if (noInterruptions) {
      breakdown.no_abnormal_interruptions = 0.2;
    } else {
      rejectionReasons.push(`High ITI variability (${interTapIntervalVariability?.toFixed(3)}) suggests interruptions.`);
    }

    // 4. Reasonable tap rate (0.5 – 15 taps/sec): +0.2
    const rateOk = tappingRate !== null &&
      tappingRate >= TAPPING_MIN_RATE &&
      tappingRate <= TAPPING_MAX_RATE;
    if (rateOk) {
      breakdown.reasonable_tap_rate = 0.2;
    } else {
      rejectionReasons.push(`Tap rate out of range: ${tappingRate?.toFixed(2)} taps/sec.`);
    }

    return _buildResult('tapping', breakdown, rejectionReasons);
  }

  /**
   * Compute quality score for a tremor hold session.
   *
   * @param {Object} p
   * @param {number}  p.durationSeconds   - Actual task duration.
   * @param {number|null} p.tremorAmplitude - RMS tremor amplitude (m/s²).
   * @param {number}  p.sampleCount       - Number of IMU samples collected.
   * @param {string}  p.extractionStatus  - Feature extractor status ('ok' or error).
   * @returns {Object} Scored quality result.
   */
  static scoreTremor({ durationSeconds, tremorAmplitude, sampleCount, extractionStatus }) {
    const breakdown = {
      task_completed: 0,
      phone_held_still: 0,
      sufficient_signal_quality: 0,
      no_excessive_movement: 0,
    };
    const rejectionReasons = [];

    // 1. Task completed (>= 8s): +0.3
    if (durationSeconds >= TREMOR_MIN_DURATION_SEC) {
      breakdown.task_completed = 0.3;
    } else {
      rejectionReasons.push(`Tremor task too short: ${durationSeconds.toFixed(1)}s < ${TREMOR_MIN_DURATION_SEC}s.`);
    }

    // 2. Phone held relatively still (amplitude <= 2.0 m/s²): +0.3
    if (tremorAmplitude !== null && tremorAmplitude <= TREMOR_MAX_MOVEMENT_AMPLITUDE) {
      breakdown.phone_held_still = 0.3;
    } else {
      rejectionReasons.push(
        tremorAmplitude !== null
          ? `Excessive movement detected: amplitude ${tremorAmplitude?.toFixed(3)} > ${TREMOR_MAX_MOVEMENT_AMPLITUDE} m/s².`
          : 'Tremor amplitude not extractable.'
      );
    }

    // 3. Sufficient signal quality (>= 50 samples): +0.2
    if (sampleCount >= 50 && extractionStatus === 'ok') {
      breakdown.sufficient_signal_quality = 0.2;
    } else {
      rejectionReasons.push(`Insufficient samples: ${sampleCount} or extraction error: ${extractionStatus}.`);
    }

    // 4. No excessive movement artifacts (amplitude <= 5.0 m/s²): +0.2
    if (tremorAmplitude !== null && tremorAmplitude <= TREMOR_MAX_AMPLITUDE_MOVEMENT) {
      breakdown.no_excessive_movement = 0.2;
    } else {
      rejectionReasons.push(`Movement artifact threshold exceeded: ${tremorAmplitude?.toFixed(3)} > ${TREMOR_MAX_AMPLITUDE_MOVEMENT} m/s².`);
    }

    return _buildResult('tremor_hold', breakdown, rejectionReasons);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Internal helpers
// ─────────────────────────────────────────────────────────────────────────────

function _buildResult(taskType, breakdown, rejectionReasons) {
  const totalScore = Number(
    Object.values(breakdown).reduce((s, v) => s + v, 0).toFixed(2)
  );
  const isBaselineEligible = totalScore >= MIN_BASELINE_QUALITY_THRESHOLD;

  return {
    task_type: taskType,
    quality_score: totalScore,
    is_baseline_eligible: isBaselineEligible,
    breakdown,
    rejection_reasons: rejectionReasons,
    summary: isBaselineEligible
      ? `Valid ${taskType} session (score: ${totalScore.toFixed(2)}) — eligible for baseline modeling`
      : `Gated ${taskType} session (score: ${totalScore.toFixed(2)} < ${MIN_BASELINE_QUALITY_THRESHOLD.toFixed(2)}) — excluded from personal baseline`,
  };
}
