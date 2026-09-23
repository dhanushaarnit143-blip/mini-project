/**
 * MPF Mobile Extension — Tapping Feature Extractor (Phase 6)
 *
 * Extracts finger-tapping biomarkers from touchscreen tap event timestamps
 * collected during the alternating finger-tapping task (10–20 seconds).
 *
 * Features extracted:
 *   tap_count                    – total number of taps
 *   tapping_rate                 – taps per second
 *   inter_tap_interval_mean      – average interval between taps (ms)
 *   inter_tap_interval_variability – coefficient of variation of ITIs
 *   decline_slope                – rate of slowing across the task (ms/tap)
 *
 * Algorithm:
 *   1. Sort tap events by timestamp.
 *   2. Compute inter-tap intervals (ITI) between consecutive taps.
 *   3. Filter physiologically implausible ITIs (< 50ms or > 2000ms).
 *   4. Compute mean, SD, CV of valid ITIs.
 *   5. Fit a linear regression of ITI vs tap index to get the decline slope.
 *
 * NOTE: Only timestamp values are consumed — NO keystroke text, finger geometry,
 *       or pressure data is stored or returned.
 */

export const TAPPING_FEATURE_VERSION = '1.0';

// Physiological plausibility gates
const MIN_ITI_MS = 50;   // < 50ms physically impossible for voluntary tapping
const MAX_ITI_MS = 2000; // > 2s indicates a pause, not a slow tap

/**
 * Extracts tapping features from a list of tap event timestamps.
 *
 * @param {number[]} tapTimestamps - Array of tap event times in milliseconds
 *   (e.g., from Date.now() or performance.now()). Must be sorted ascending.
 * @param {number} taskDurationMs - Total task window duration in milliseconds.
 * @returns {Object} Extracted tapping feature set.
 */
export function extractTappingFeatures(tapTimestamps, taskDurationMs) {
  if (!tapTimestamps || tapTimestamps.length < 3) {
    return _emptyFeatures(taskDurationMs, 'insufficient_taps');
  }

  // Ensure sorted
  const sorted = [...tapTimestamps].sort((a, b) => a - b);
  const durationSec = taskDurationMs / 1000;

  // --- Step 1: Compute inter-tap intervals ---
  const rawITI = [];
  for (let i = 1; i < sorted.length; i++) {
    rawITI.push(sorted[i] - sorted[i - 1]);
  }

  // --- Step 2: Filter physiologically implausible intervals ---
  const validITI = rawITI.filter(iti => iti >= MIN_ITI_MS && iti <= MAX_ITI_MS);

  if (validITI.length < 2) {
    return _emptyFeatures(taskDurationMs, 'insufficient_valid_intervals');
  }

  const tapCount = sorted.length;
  const tappingRate = durationSec > 0 ? tapCount / durationSec : 0;
  const itiMean = _mean(validITI);
  const itiCV = _cv(validITI);

  // --- Step 3: Decline slope via linear regression (ITI vs tap index) ---
  // Positive slope → slowing down (fatigue / motor deficit signal)
  const declineSlope = _linearRegressionSlope(validITI);

  return {
    tap_count: tapCount,
    tapping_rate: _round(tappingRate, 3),
    inter_tap_interval_mean: _round(itiMean, 2),
    inter_tap_interval_variability: _round(itiCV, 4),
    decline_slope: _round(declineSlope, 4),
    duration_seconds: _round(durationSec, 2),
    feature_version: TAPPING_FEATURE_VERSION,
    _extraction_status: 'ok',
    // NOTE: raw timestamps NOT returned — only derived numeric features
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Internal helpers
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Ordinary least-squares slope: dy/dx where x = tap index (0, 1, 2, ...).
 * Returns slope in ms per tap (positive = slowing).
 */
function _linearRegressionSlope(values) {
  const n = values.length;
  if (n < 2) return 0;
  const xMean = (n - 1) / 2;
  const yMean = _mean(values);
  let num = 0;
  let denom = 0;
  for (let i = 0; i < n; i++) {
    num += (i - xMean) * (values[i] - yMean);
    denom += (i - xMean) ** 2;
  }
  return denom !== 0 ? num / denom : 0;
}

function _mean(arr) {
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

function _std(arr) {
  const m = _mean(arr);
  return Math.sqrt(arr.reduce((a, b) => a + (b - m) ** 2, 0) / arr.length);
}

function _cv(arr) {
  const m = _mean(arr);
  if (m === 0) return 0;
  return _std(arr) / m;
}

function _round(val, dp) {
  return Math.round(val * 10 ** dp) / 10 ** dp;
}

function _emptyFeatures(taskDurationMs, reason) {
  return {
    tap_count: 0,
    tapping_rate: null,
    inter_tap_interval_mean: null,
    inter_tap_interval_variability: null,
    decline_slope: null,
    duration_seconds: taskDurationMs / 1000,
    feature_version: TAPPING_FEATURE_VERSION,
    _extraction_status: reason,
  };
}
