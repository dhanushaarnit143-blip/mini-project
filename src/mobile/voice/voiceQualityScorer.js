/**
 * MPF Mobile Extension — Voice Quality Scorer (Phase 5)
 * 
 * Evaluates session recording quality across 4 standardized clinical criteria:
 * 1. Sufficient duration (> 3.0 seconds): +0.30
 * 2. Good signal-to-noise ratio (SNR >= 15 dB or signal_quality >= 0.50): +0.30
 * 3. No clipping detected (clipping_detected === false): +0.20
 * 4. Low silence ratio (< 30% silence): +0.20
 * 
 * BASELINE ENGINE GATING RULE:
 * Sessions with quality_score < 0.50 are strictly rejected from baseline updates.
 */

export const MIN_BASELINE_QUALITY_THRESHOLD = 0.50;
export const MIN_DURATION_SECONDS = 3.0;
export const MIN_SIGNAL_QUALITY_THRESHOLD = 0.50;
export const MAX_ALLOWED_SILENCE_RATIO = 0.30;

export class VoiceQualityScorer {
  /**
   * Computes standardized quality score and evaluates baseline eligibility.
   * 
   * @param {Object} params
   * @param {number} params.duration - Recording duration in seconds
   * @param {number} params.signal_quality - SNR / signal quality estimate 0.0 to 1.0
   * @param {boolean} params.clipping_detected - Whether amplitude clipping occurred
   * @param {number} params.silence_ratio - Proportion of silence in recording 0.0 to 1.0
   * @param {number} [params.hnr] - Harmonics-to-noise ratio (optional bonus/check)
   * @returns {Object} Quality breakdown, overall score, and gating recommendation
   */
  static calculateQualityScore(params) {
    if (!params) {
      return {
        quality_score: 0.0,
        is_baseline_eligible: false,
        breakdown: {
          sufficient_duration: 0.0,
          good_snr: 0.0,
          no_clipping: 0.0,
          low_silence: 0.0
        },
        rejection_reasons: ["Missing acoustic session metrics"]
      };
    }

    const {
      duration = 0.0,
      signal_quality = 0.0,
      clipping_detected = false,
      silence_ratio = 1.0
    } = params;

    const rejectionReasons = [];
    const breakdown = {
      sufficient_duration: 0.0,
      good_snr: 0.0,
      no_clipping: 0.0,
      low_silence: 0.0
    };

    // 1. Sufficient duration (> 3.0s): +0.30
    if (duration > MIN_DURATION_SECONDS) {
      breakdown.sufficient_duration = 0.30;
    } else {
      rejectionReasons.push(`Insufficient recording duration: ${duration.toFixed(1)}s <= ${MIN_DURATION_SECONDS}s`);
    }

    // 2. Good signal-to-noise ratio (signal_quality >= 0.50): +0.30
    if (signal_quality >= MIN_SIGNAL_QUALITY_THRESHOLD) {
      breakdown.good_snr = 0.30;
    } else {
      rejectionReasons.push(`Low signal-to-noise quality: ${(signal_quality * 100).toFixed(1)}% < ${(MIN_SIGNAL_QUALITY_THRESHOLD * 100)}%`);
    }

    // 3. No clipping: +0.20
    if (!clipping_detected) {
      breakdown.no_clipping = 0.20;
    } else {
      rejectionReasons.push("Audio clipping/saturation detected (microphone overloaded)");
    }

    // 4. Low silence ratio (< 30%): +0.20
    if (silence_ratio < MAX_ALLOWED_SILENCE_RATIO) {
      breakdown.low_silence = 0.20;
    } else {
      rejectionReasons.push(`Excessive silence in recording: ${(silence_ratio * 100).toFixed(1)}% >= ${(MAX_ALLOWED_SILENCE_RATIO * 100)}%`);
    }

    // Calculate total score
    const totalScore = Number(
      (
        breakdown.sufficient_duration +
        breakdown.good_snr +
        breakdown.no_clipping +
        breakdown.low_silence
      ).toFixed(2)
    );

    const isBaselineEligible = totalScore >= MIN_BASELINE_QUALITY_THRESHOLD;

    return {
      quality_score: totalScore,
      is_baseline_eligible: isBaselineEligible,
      breakdown,
      rejection_reasons: rejectionReasons,
      summary: isBaselineEligible
        ? `Valid voice session (score: ${totalScore.toFixed(2)}) — eligible for baseline modeling`
        : `Gated session (score: ${totalScore.toFixed(2)} < ${MIN_BASELINE_QUALITY_THRESHOLD.toFixed(2)}) — not fed into personal baseline`
    };
  }
}
