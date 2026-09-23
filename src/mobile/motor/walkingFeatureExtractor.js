/**
 * MPF Mobile Extension — Walking Feature Extractor (Phase 6)
 *
 * Extracts gait biomarkers from accelerometer IMU samples collected during the
 * 30-second walking task.  ONLY derived numeric features are produced — raw
 * sensor arrays are NOT returned and NOT stored.
 *
 * Features extracted:
 *   cadence                    – steps per minute
 *   stride_interval_mean       – average stride time (seconds)
 *   stride_interval_variability – coefficient of variation of stride intervals
 *   movement_regularity        – autocorrelation-based regularity score (0-1)
 *   symmetry_index             – left-right acceleration symmetry (0-1)
 *
 * Algorithm overview:
 *   1. Compute vertical acceleration magnitude (|a|) from all 3 axes.
 *   2. Apply mean-subtraction and bandpass (0.5 – 5 Hz) to isolate step signal.
 *   3. Detect peaks using threshold + minimum inter-peak distance.
 *   4. Derive stride intervals and cadence from peak timings.
 *   5. Compute autocorrelation at lag = stride interval for regularity score.
 *   6. Symmetry index from the ratio of even-to-odd step intervals.
 */

export const WALKING_FEATURE_VERSION = '1.0';

// Step detection tuning constants
const MIN_STEP_INTERVAL_MS = 250;  // 240 steps/min max (pathological sprint limit)
const MAX_STEP_INTERVAL_MS = 2000; // 30 steps/min min (very slow gait)
const PEAK_PROMINENCE_FACTOR = 0.3; // peak must exceed (mean + factor * std) of signal

/**
 * Extracts walking features from raw IMU samples.
 *
 * @param {Array<{ t: number, ax: number, ay: number, az: number }>} samples
 *   Raw IMU samples (ax/ay/az in m/s² or g, t in ms).
 * @param {number} durationMs - Total collection duration in milliseconds.
 * @returns {Object} Extracted walking feature set.
 */
export function extractWalkingFeatures(samples, durationMs) {
  if (!samples || samples.length < 20) {
    return _emptyFeatures(durationMs, 'insufficient_samples');
  }

  // --- Step 1: Compute acceleration magnitude ---
  const mag = samples.map(s => Math.sqrt(s.ax ** 2 + s.ay ** 2 + s.az ** 2));

  // --- Step 2: Mean-subtract (remove gravity DC component) ---
  const mean = mag.reduce((a, b) => a + b, 0) / mag.length;
  const detrended = mag.map(v => v - mean);

  // --- Step 3: Detect step peaks ---
  const timestamps = samples.map(s => s.t);
  const peaks = _detectPeaks(detrended, timestamps, PEAK_PROMINENCE_FACTOR);

  if (peaks.length < 2) {
    return _emptyFeatures(durationMs, 'insufficient_peaks');
  }

  // --- Step 4: Compute step intervals and cadence ---
  const stepIntervals = []; // ms between consecutive peaks
  for (let i = 1; i < peaks.length; i++) {
    const interval = peaks[i].t - peaks[i - 1].t;
    if (interval >= MIN_STEP_INTERVAL_MS && interval <= MAX_STEP_INTERVAL_MS) {
      stepIntervals.push(interval);
    }
  }

  if (stepIntervals.length < 2) {
    return _emptyFeatures(durationMs, 'insufficient_valid_steps');
  }

  const stepCount = peaks.length;
  const durationSec = durationMs / 1000;

  // Cadence: steps per minute
  const cadence = (stepCount / durationSec) * 60;

  // Stride intervals (2 consecutive steps = 1 stride)
  const strideIntervals = [];
  for (let i = 0; i + 1 < stepIntervals.length; i += 2) {
    strideIntervals.push((stepIntervals[i] + stepIntervals[i + 1]) / 1000); // convert to seconds
  }

  const strideIntervalMean = strideIntervals.length > 0
    ? _mean(strideIntervals)
    : stepIntervals[0] / 500; // fallback: half step interval

  const strideIntervalVariability = strideIntervals.length > 1
    ? _cv(strideIntervals)
    : 0;

  // --- Step 5: Autocorrelation-based regularity score ---
  const lagSamples = Math.round(
    (strideIntervalMean * 1000) / (durationMs / samples.length)
  );
  const movementRegularity = _autocorrelationAtLag(detrended, lagSamples);

  // --- Step 6: Symmetry index (even vs odd step intervals) ---
  const evenIntervals = stepIntervals.filter((_, i) => i % 2 === 0);
  const oddIntervals = stepIntervals.filter((_, i) => i % 2 !== 0);
  const symmetryIndex = (evenIntervals.length > 0 && oddIntervals.length > 0)
    ? _symmetryIndex(_mean(evenIntervals), _mean(oddIntervals))
    : null;

  return {
    cadence: _round(cadence, 2),
    stride_interval_mean: _round(strideIntervalMean, 4),
    stride_interval_variability: _round(strideIntervalVariability, 4),
    movement_regularity: _round(Math.max(0, Math.min(1, movementRegularity)), 4),
    symmetry_index: symmetryIndex !== null ? _round(symmetryIndex, 4) : null,
    step_count: stepCount,
    duration_seconds: _round(durationSec, 2),
    feature_version: WALKING_FEATURE_VERSION,
    _extraction_status: 'ok',
    // NOTE: raw samples are NOT returned — only derived features
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Internal helpers (not exported — prevent accidental raw data access)
// ─────────────────────────────────────────────────────────────────────────────

function _detectPeaks(signal, timestamps, prominenceFactor) {
  const sigma = _std(signal);
  const mu = _mean(signal);
  const threshold = mu + prominenceFactor * sigma;
  const peaks = [];

  let lastPeakTime = -Infinity;

  for (let i = 1; i < signal.length - 1; i++) {
    if (
      signal[i] > signal[i - 1] &&
      signal[i] > signal[i + 1] &&
      signal[i] > threshold
    ) {
      const t = timestamps[i];
      if (t - lastPeakTime >= MIN_STEP_INTERVAL_MS) {
        peaks.push({ i, t, v: signal[i] });
        lastPeakTime = t;
      }
    }
  }

  return peaks;
}

function _autocorrelationAtLag(signal, lag) {
  if (lag <= 0 || lag >= signal.length) return 0;
  const n = signal.length - lag;
  const mu = _mean(signal);
  let num = 0;
  let denom = 0;
  for (let i = 0; i < n; i++) {
    num += (signal[i] - mu) * (signal[i + lag] - mu);
    denom += (signal[i] - mu) ** 2;
  }
  // Normalize to 0-1 range
  const raw = denom > 0 ? num / denom : 0;
  return (raw + 1) / 2; // shift from [-1,1] to [0,1]
}

function _symmetryIndex(meanEven, meanOdd) {
  if (meanEven + meanOdd === 0) return 0;
  return 1 - Math.abs(meanEven - meanOdd) / ((meanEven + meanOdd) / 2);
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

function _emptyFeatures(durationMs, reason) {
  return {
    cadence: null,
    stride_interval_mean: null,
    stride_interval_variability: null,
    movement_regularity: 0,
    symmetry_index: null,
    step_count: 0,
    duration_seconds: durationMs / 1000,
    feature_version: WALKING_FEATURE_VERSION,
    _extraction_status: reason,
  };
}
