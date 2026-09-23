/**
 * MPF Mobile Extension — Visual Feature Extractor (Phase 7)
 *
 * Extracts behavioral ocular and visual metrics from front-camera guided tasks:
 *   1. Visual tracking features (gaze stability, tracking accuracy, velocity, smoothness)
 *   2. Blink features (blink rate, interval variability, mean duration)
 *   3. Reaction features (reaction time mean, variability, missed targets)
 *
 * CRITICAL PRIVACY & CLINICAL COMPLIANCE:
 *   - "Ocular/Visual Behavior Module" — NOT retinal imaging.
 *   - ZERO raw frame pixels, images, or raw landmark coordinate streams are stored or returned.
 *   - Returns ONLY derived numeric scalar features and summary JSON.
 *   - Version stamped with CURRENT_FEATURE_VERSION = '1.0'.
 */

export const VISUAL_FEATURE_VERSION = '1.0';

// EAR threshold constants for blink segmentation
export const EAR_BLINK_THRESHOLD = 0.21;
export const MIN_BLINK_DURATION_MS = 50;   // below 50ms is sensor noise/flutter
export const MAX_BLINK_DURATION_MS = 600;  // above 600ms is prolonged closure

// Reaction time plausibility bounds
export const MIN_PLAUSIBLE_REACTION_MS = 100; // physiological limit for visual reaction
export const MAX_REACTION_TIMEOUT_MS   = 2500;

// Helper math utilities
function _mean(arr) {
  if (!arr || arr.length === 0) return 0;
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

function _std(arr) {
  if (!arr || arr.length < 2) return 0;
  const m = _mean(arr);
  return Math.sqrt(arr.reduce((sum, v) => sum + (v - m) ** 2, 0) / arr.length);
}

function _cv(arr) {
  const m = _mean(arr);
  return m > 0 ? _std(arr) / m : 0;
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. VISUAL TRACKING FEATURE EXTRACTION
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Extracts visual tracking features from gaze and target trajectories.
 *
 * @param {Array<{ t: number, gazeX: number, gazeY: number, targetX: number, targetY: number, confidence?: number }>} samples
 * @param {number} durationMs - Duration in milliseconds
 * @returns {Object} Extracted tracking features
 */
export function extractTrackingFeatures(samples, durationMs) {
  const durationSec = durationMs > 0 ? durationMs / 1000 : 0;

  if (!samples || samples.length < 10) {
    return {
      gaze_stability: null,
      tracking_accuracy: null,
      gaze_movement_features: null,
      sample_count: samples ? samples.length : 0,
      duration_seconds: durationSec,
      feature_version: VISUAL_FEATURE_VERSION,
    };
  }

  // 1. Gaze velocity and jitter computation
  const velocities = [];
  const errors = [];
  const accelerations = [];

  for (let i = 1; i < samples.length; i++) {
    const prev = samples[i - 1];
    const curr = samples[i];
    const dt = (curr.t - prev.t) / 1000; // in seconds

    if (dt > 0.005) {
      const dx = curr.gazeX - prev.gazeX;
      const dy = curr.gazeY - prev.gazeY;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const vel = dist / dt;
      velocities.push(vel);

      // Distance to target at curr sample
      const errX = curr.gazeX - curr.targetX;
      const errY = curr.gazeY - curr.targetY;
      errors.push(Math.sqrt(errX * errX + errY * errY));
    }
  }

  // Velocity second-derivative / acceleration for jitter/smoothness
  for (let i = 1; i < velocities.length; i++) {
    accelerations.push(Math.abs(velocities[i] - velocities[i - 1]));
  }

  const meanVelocity = velocities.length > 0 ? _mean(velocities) : 0;
  const maxVelocity  = velocities.length > 0 ? Math.max(...velocities) : 0;
  const jitter       = accelerations.length > 0 ? _mean(accelerations) : 0;

  // Gaze stability: bounded [0, 1] — higher value indicates steady tracking without excessive jitter
  // normalized jitter mapping
  const gazeStability = Math.max(0.0, Math.min(1.0, 1.0 / (1.0 + 0.15 * jitter)));

  // Tracking accuracy: bounded [0, 1] — based on RMSE between gaze and target
  const rmse = errors.length > 0 ? Math.sqrt(_mean(errors.map(e => e * e))) : 1.0;
  // Normalized on a unit canvas (max distance is sqrt(2) ~ 1.414)
  const trackingAccuracy = Math.max(0.0, Math.min(1.0, Math.exp(-2.5 * rmse)));

  // Smoothness: inverse of acceleration variability
  const smoothness = Math.max(0.0, Math.min(1.0, 1.0 / (1.0 + 0.1 * _std(velocities))));

  return {
    gaze_stability: Number(gazeStability.toFixed(4)),
    tracking_accuracy: Number(trackingAccuracy.toFixed(4)),
    gaze_movement_features: {
      mean_velocity: Number(meanVelocity.toFixed(4)),
      max_velocity: Number(maxVelocity.toFixed(4)),
      smoothness: Number(smoothness.toFixed(4)),
      tracking_error_mean: Number((errors.length > 0 ? _mean(errors) : 0).toFixed(4)),
      rmse: Number(rmse.toFixed(4)),
    },
    sample_count: samples.length,
    duration_seconds: Number(durationSec.toFixed(2)),
    feature_version: VISUAL_FEATURE_VERSION,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// 2. BLINK DYNAMICS FEATURE EXTRACTION
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Detects blink events and computes blink dynamics from Eye Aspect Ratio (EAR) samples.
 *
 * @param {Array<{ t: number, ear: number, confidence?: number }>} samples
 * @param {number} durationMs - Duration in milliseconds
 * @returns {Object} Extracted blink features
 */
export function extractBlinkFeatures(samples, durationMs) {
  const durationSec = durationMs > 0 ? durationMs / 1000 : 0;

  if (!samples || samples.length < 15) {
    return {
      blink_rate: null,
      blink_interval_variability: null,
      blink_duration_mean: null,
      blink_count: 0,
      duration_seconds: durationSec,
      feature_version: VISUAL_FEATURE_VERSION,
    };
  }

  // Detect blink episodes (temporal segments where EAR < EAR_BLINK_THRESHOLD)
  const blinks = [];
  let inBlink = false;
  let blinkStartT = 0;

  for (let i = 0; i < samples.length; i++) {
    const s = samples[i];
    if (s.ear < EAR_BLINK_THRESHOLD) {
      if (!inBlink) {
        inBlink = true;
        blinkStartT = s.t;
      }
    } else {
      if (inBlink) {
        inBlink = false;
        const duration = s.t - blinkStartT;
        if (duration >= MIN_BLINK_DURATION_MS && duration <= MAX_BLINK_DURATION_MS) {
          blinks.push({
            startT: blinkStartT,
            endT: s.t,
            duration,
          });
        }
      }
    }
  }

  // Edge case: blink in progress at very end of recording
  if (inBlink) {
    const lastT = samples[samples.length - 1].t;
    const duration = lastT - blinkStartT;
    if (duration >= MIN_BLINK_DURATION_MS && duration <= MAX_BLINK_DURATION_MS) {
      blinks.push({
        startT: blinkStartT,
        endT: lastT,
        duration,
      });
    }
  }

  const blinkCount = blinks.length;

  // Blink rate: blinks per minute
  const blinkRate = durationSec > 0 ? (blinkCount / durationSec) * 60 : 0;

  // Inter-blink intervals (IBI) in seconds
  const ibis = [];
  for (let i = 1; i < blinks.length; i++) {
    const ibi = (blinks[i].startT - blinks[i - 1].startT) / 1000;
    if (ibi > 0) {
      ibis.push(ibi);
    }
  }

  // Blink interval variability (CV = std / mean)
  const blinkIntervalVariability = ibis.length >= 2 ? _cv(ibis) : 0;

  // Mean blink duration in ms
  const blinkDurations = blinks.map(b => b.duration);
  const blinkDurationMean = blinkDurations.length > 0 ? _mean(blinkDurations) : null;

  return {
    blink_rate: Number(blinkRate.toFixed(2)),
    blink_interval_variability: Number(blinkIntervalVariability.toFixed(4)),
    blink_duration_mean: blinkDurationMean !== null ? Number(blinkDurationMean.toFixed(2)) : null,
    blink_count: blinkCount,
    duration_seconds: Number(durationSec.toFixed(2)),
    feature_version: VISUAL_FEATURE_VERSION,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// 3. VISUAL REACTION TIME FEATURE EXTRACTION
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Extracts visual reaction time features from stimulus presentation records.
 *
 * @param {Array<{ stimulusTimeMs: number, responseTimeMs?: number, tapped: boolean, timeout?: boolean }>} events
 * @param {number} durationMs - Duration in milliseconds
 * @returns {Object} Extracted reaction features
 */
export function extractReactionFeatures(events, durationMs) {
  const durationSec = durationMs > 0 ? durationMs / 1000 : 0;

  if (!events || events.length === 0) {
    return {
      reaction_time_mean: null,
      reaction_time_variability: null,
      missed_targets: 0,
      total_targets: 0,
      duration_seconds: durationSec,
      feature_version: VISUAL_FEATURE_VERSION,
    };
  }

  const validReactionTimes = [];
  let missedCount = 0;

  for (const ev of events) {
    if (!ev.tapped || ev.timeout || !ev.responseTimeMs) {
      missedCount++;
    } else {
      const rt = ev.responseTimeMs - ev.stimulusTimeMs;
      // Filter out physiological anticipatory taps / artifacts
      if (rt >= MIN_PLAUSIBLE_REACTION_MS && rt <= MAX_REACTION_TIMEOUT_MS) {
        validReactionTimes.push(rt);
      } else if (rt > MAX_REACTION_TIMEOUT_MS) {
        missedCount++;
      }
    }
  }

  const reactionTimeMean = validReactionTimes.length > 0 ? _mean(validReactionTimes) : null;
  const reactionTimeVariability = validReactionTimes.length >= 2 ? _cv(validReactionTimes) : 0;

  return {
    reaction_time_mean: reactionTimeMean !== null ? Number(reactionTimeMean.toFixed(2)) : null,
    reaction_time_variability: Number(reactionTimeVariability.toFixed(4)),
    missed_targets: missedCount,
    total_targets: events.length,
    valid_responses: validReactionTimes.length,
    duration_seconds: Number(durationSec.toFixed(2)),
    feature_version: VISUAL_FEATURE_VERSION,
  };
}
