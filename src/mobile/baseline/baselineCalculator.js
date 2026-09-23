/**
 * MPF Mobile Extension — Baseline Calculator (Phase 10)
 *
 * Computes robust and classical parametric/non-parametric statistics
 * for individual 14-day baseline calibration:
 * - mean
 * - median
 * - standard deviation (sample std, ddof=1)
 * - median absolute deviation (MAD)
 * - lower quantile (Q1, 25th percentile)
 * - upper quantile (Q3, 75th percentile)
 * - coefficient of variation (CV = std / mean)
 * - sample count
 *
 * NON-NEGOTIABLE COMPLIANCE:
 * - NO DIAGNOSTIC CLAIMS: Measures normative individual variation.
 * - BASELINE-CENTRIC: Baseline captures the user's personal normal distribution.
 * - NO DATA FABRICATION: Only computes on validated, un-imputed feature observations.
 */

export const ALGORITHM_VERSION = '1.0.0';
export const MIN_BASELINE_DAYS = 14;

/**
 * Filters and sorts numeric array in ascending order.
 * @param {Array<number>} values
 * @returns {Array<number>}
 */
export function sanitizeAndSort(values) {
  if (!Array.isArray(values)) return [];
  return values
    .map(v => (typeof v === 'number' ? v : Number(v)))
    .filter(v => typeof v === 'number' && !Number.isNaN(v) && Number.isFinite(v))
    .sort((a, b) => a - b);
}

/**
 * Computes arithmetic mean of a numeric array.
 * @param {Array<number>} values
 * @returns {number|null}
 */
export function computeMean(values) {
  const clean = sanitizeAndSort(values);
  if (clean.length === 0) return null;
  const sum = clean.reduce((acc, v) => acc + v, 0);
  return Number((sum / clean.length).toFixed(4));
}

/**
 * Computes median (50th percentile) of a numeric array.
 * @param {Array<number>} values
 * @returns {number|null}
 */
export function computeMedian(values) {
  const clean = sanitizeAndSort(values);
  if (clean.length === 0) return null;
  const mid = Math.floor(clean.length / 2);
  const med = clean.length % 2 === 0
    ? (clean[mid - 1] + clean[mid]) / 2.0
    : clean[mid];
  return Number(med.toFixed(4));
}

/**
 * Computes sample standard deviation (ddof = 1) of a numeric array.
 * If N < 2, returns 0.0.
 * @param {Array<number>} values
 * @returns {number|null}
 */
export function computeStandardDeviation(values) {
  const clean = sanitizeAndSort(values);
  if (clean.length === 0) return null;
  if (clean.length === 1) return 0.0;
  const mean = clean.reduce((acc, v) => acc + v, 0) / clean.length;
  const variance = clean.reduce((acc, v) => acc + Math.pow(v - mean, 2), 0) / (clean.length - 1);
  return Number(Math.sqrt(variance).toFixed(4));
}

/**
 * Computes quantile using standard linear interpolation (matching numpy method='linear').
 * @param {Array<number>} values
 * @param {number} q Quantile between 0.0 and 1.0
 * @returns {number|null}
 */
export function computeQuantile(values, q) {
  if (q < 0 || q > 1) {
    throw new RangeError(`Quantile q must be between 0.0 and 1.0, got ${q}`);
  }
  const clean = sanitizeAndSort(values);
  if (clean.length === 0) return null;
  if (clean.length === 1) return clean[0];

  const index = (clean.length - 1) * q;
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  const fraction = index - lower;

  const result = clean[lower] + fraction * (clean[upper] - clean[lower]);
  return Number(result.toFixed(4));
}

/**
 * Computes Lower Quantile (Q1 - 25th percentile).
 * @param {Array<number>} values
 * @returns {number|null}
 */
export function computeQ1(values) {
  return computeQuantile(values, 0.25);
}

/**
 * Computes Upper Quantile (Q3 - 75th percentile).
 * @param {Array<number>} values
 * @returns {number|null}
 */
export function computeQ3(values) {
  return computeQuantile(values, 0.75);
}

/**
 * Computes Interquartile Range (IQR = Q3 - Q1).
 * @param {Array<number>} values
 * @returns {number|null}
 */
export function computeIQR(values) {
  const q1 = computeQ1(values);
  const q3 = computeQ3(values);
  if (q1 === null || q3 === null) return null;
  return Number((q3 - q1).toFixed(4));
}

/**
 * Computes Median Absolute Deviation (MAD):
 * MAD = median(|x_i - median(x)|)
 * @param {Array<number>} values
 * @returns {number|null}
 */
export function computeMAD(values) {
  const clean = sanitizeAndSort(values);
  if (clean.length === 0) return null;
  const med = computeMedian(clean);
  const absoluteDeviations = clean.map(v => Math.abs(v - med));
  return computeMedian(absoluteDeviations);
}

/**
 * Computes Coefficient of Variation (CV = std / mean).
 * If mean is 0 or std is 0, returns 0.0.
 * @param {Array<number>} values
 * @returns {number|null}
 */
export function computeCoefficientOfVariation(values) {
  const clean = sanitizeAndSort(values);
  if (clean.length === 0) return null;
  const std = computeStandardDeviation(clean);
  const mean = computeMean(clean);
  if (mean === null || std === null || mean === 0) return 0.0;
  return Number((Math.abs(std / mean)).toFixed(4));
}

/**
 * Calculates complete 14-day calibration baseline statistics for a feature.
 *
 * @param {Array<number>} observations Valid numeric daily values
 * @param {Object} options Configuration and metadata
 * @param {string} options.featureName Name of the feature
 * @param {string} options.modality Modality name ('typing'|'voice'|'motor'|'visual'|'sleep')
 * @param {string} [options.startDate] First observation date
 * @param {string} [options.endDate] Last observation date
 * @param {string} [options.algorithmVersion] Baseline algorithm version
 * @returns {Object} Complete baseline statistical profile
 */
export function calculateFeatureBaseline(observations, options = {}) {
  const clean = sanitizeAndSort(observations);
  const count = clean.length;

  const {
    featureName = 'unknown_feature',
    modality = 'motor',
    startDate = new Date().toISOString().slice(0, 10),
    endDate = new Date().toISOString().slice(0, 10),
    algorithmVersion = ALGORITHM_VERSION,
  } = options;

  if (count === 0) {
    return {
      feature_name: featureName,
      modality,
      sample_count: 0,
      baseline_mean: null,
      baseline_median: null,
      baseline_std: null,
      baseline_mad: null,
      q1: null,
      q3: null,
      coefficient_of_variation: null,
      lower_bound: null,
      upper_bound: null,
      baseline_status: 'insufficient_data',
      baseline_start_date: startDate,
      baseline_end_date: endDate,
      baseline_version: '1.0.0',
      algorithm_version: algorithmVersion,
    };
  }

  const mean = computeMean(clean);
  const median = computeMedian(clean);
  const std = computeStandardDeviation(clean);
  const mad = computeMAD(clean);
  const q1 = computeQ1(clean);
  const q3 = computeQ3(clean);
  const cv = computeCoefficientOfVariation(clean);

  // Robust bounds: median ± 3 * MAD (with fallback to 3 * std if MAD is 0)
  const dispersionUnit = mad > 0 ? mad : (std > 0 ? std : 0.001);
  const lowerBound = Number((median - 3.0 * dispersionUnit).toFixed(4));
  const upperBound = Number((median + 3.0 * dispersionUnit).toFixed(4));

  const baselineStatus = count >= MIN_BASELINE_DAYS ? 'established' : 'calibrating';

  return {
    feature_name: featureName,
    modality,
    sample_count: count,
    baseline_mean: mean,
    baseline_median: median,
    baseline_std: std,
    baseline_mad: mad,
    q1,
    q3,
    coefficient_of_variation: cv,
    lower_bound: lowerBound,
    upper_bound: upperBound,
    baseline_status: baselineStatus,
    baseline_start_date: startDate,
    baseline_end_date: endDate,
    baseline_version: '1.0.0',
    algorithm_version: algorithmVersion,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
}

// Dual CommonJS / ES Module export
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    ALGORITHM_VERSION,
    MIN_BASELINE_DAYS,
    sanitizeAndSort,
    computeMean,
    computeMedian,
    computeStandardDeviation,
    computeQuantile,
    computeQ1,
    computeQ3,
    computeIQR,
    computeMAD,
    computeCoefficientOfVariation,
    calculateFeatureBaseline,
  };
}
