/**
 * MPF Mobile Extension — Typing Feature Extractor
 * 
 * Extracts digital biomarker features from raw keystroke timing kinematics.
 * 
 * Features Extracted:
 * - typing_speed: Characters per second (keystroke count / session duration)
 * - mean_inter_key_interval: Average time between consecutive key presses (ms)
 * - std_inter_key_interval: Sample standard deviation of inter-key intervals (ms)
 * - pause_rate: Frequency of pauses > 500ms per minute
 * - correction_rate: Frequency of backspace/correction events per minute
 * - rhythm_variability: Coefficient of variation of inter-key intervals (std / mean)
 * - session_duration: Total task completion time (seconds)
 */

export const FEATURE_VERSION = "1.0.0";

export class TypingFeatureExtractor {
  /**
   * Extracts quantitative timing kinematics features from raw collector output.
   * @param {Object} rawSessionData
   * @param {Array<Object>} rawSessionData.timingEvents - Sequence of timing records
   * @param {number} rawSessionData.sessionDuration - Duration in seconds
   * @param {number} [rawSessionData.keystrokeCount] - Optional total count
   * @returns {Object} Extracted kinematics feature dictionary
   */
  static extractFeatures(rawSessionData) {
    if (!rawSessionData) {
      throw new Error("Invalid session data: cannot be null or undefined.");
    }

    const timingEvents = rawSessionData.timingEvents || [];
    const sessionDuration = Math.max(0, Number(rawSessionData.sessionDuration) || 0);
    const totalKeystrokes = timingEvents.length;

    // 1. Typing speed (characters per second)
    const typingSpeed = sessionDuration > 0
      ? Number((totalKeystrokes / sessionDuration).toFixed(3))
      : 0.0;

    // 2. Inter-Key Intervals (IKIs) for consecutive presses (eventIndex >= 2)
    // Note: the first keystroke does not have a preceding keystroke in this task
    const ikis = [];
    let pauseCount = 0;
    let correctionCount = 0;

    for (let i = 0; i < timingEvents.length; i++) {
      const event = timingEvents[i];
      
      if (i > 0) {
        const iki = Math.max(0, Number(event.interKeyInterval) || 0);
        ikis.push(iki);

        // Pause definition: latency > 500ms
        if (iki > 500) {
          pauseCount++;
        }
      }

      if (event.isCorrection) {
        correctionCount++;
      }
    }

    // 3. Mean & Standard Deviation of IKIs
    let meanIki = 0.0;
    let stdIki = 0.0;

    if (ikis.length > 0) {
      const sum = ikis.reduce((acc, val) => acc + val, 0);
      meanIki = Number((sum / ikis.length).toFixed(2));

      if (ikis.length > 1) {
        // Sample standard deviation (N-1)
        const varianceSum = ikis.reduce((acc, val) => acc + Math.pow(val - meanIki, 2), 0);
        stdIki = Number(Math.sqrt(varianceSum / (ikis.length - 1)).toFixed(2));
      } else {
        stdIki = 0.0;
      }
    }

    // 4. Pause Rate (pauses > 500ms per minute)
    const durationMinutes = sessionDuration / 60.0;
    const pauseRate = durationMinutes > 0
      ? Number((pauseCount / durationMinutes).toFixed(2))
      : 0.0;

    // 5. Correction Rate (backspaces/corrections per minute)
    const correctionRate = durationMinutes > 0
      ? Number((correctionCount / durationMinutes).toFixed(2))
      : 0.0;

    // 6. Rhythm Variability (Coefficient of Variation: std / mean)
    const rhythmVariability = meanIki > 0
      ? Number((stdIki / meanIki).toFixed(4))
      : 0.0;

    return {
      session_duration: Number(sessionDuration.toFixed(2)),
      typing_speed: typingSpeed,
      mean_inter_key_interval: meanIki,
      std_inter_key_interval: stdIki,
      pause_rate: pauseRate,
      correction_rate: correctionRate,
      rhythm_variability: rhythmVariability,
      keystroke_count: totalKeystrokes,
      pause_count: pauseCount,
      correction_count: correctionCount,
      feature_version: FEATURE_VERSION
    };
  }
}
