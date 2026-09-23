/**
 * MPF Mobile Extension — Longitudinal Trend Detector (Phase 11)
 *
 * Computes multi-scale temporal trend and trajectory metrics over 7-day and 14-day windows:
 * - daily_value: today's measurement
 * - 7_day_average: rolling 7-day mean
 * - 7_day_variability: rolling 7-day sample standard deviation
 * - 14_day_trend: linear regression slope (ordinary least squares) over 14 days
 * - baseline_deviation: z-score vs personal baseline
 * - sustained_deviation: number of consecutive days with |z| > 2.0
 * - missingness: proportion of missing days in last 14 days ( (14 - count) / 14 )
 * - data_quality: average observation quality score over last 7 days
 *
 * Trend Classifications:
 * - "Progressive deviation from personal baseline": 14-day trend slope is significant AND moving away from baseline
 * - "Improving toward baseline": 14-day trend slope is significant AND moving back toward baseline
 * - "Stable within baseline": no significant trend slope or within baseline envelope
 *
 * STRICT NON-DIAGNOSTIC COMPLIANCE:
 * - NEVER uses "Parkinson's progression", "Disease worsening", "Clinical decline".
 */

import { calculateDeviation } from './deviationCalculator.js';
import { calculateSustainedDeviation } from './sustainedDeviationDetector.js';
import { assertNonDiagnosticPhrasing, RESEARCH_DISCLAIMER } from './deviationClassifier.js';

export const TREND_PROGRESSIVE_DEVIATION = 'Progressive deviation from personal baseline';
export const TREND_STABLE_BASELINE = 'Stable within baseline';
export const TREND_IMPROVING_TOWARD_BASELINE = 'Improving toward baseline';

export const DEFAULT_SLOPE_THRESHOLD = 0.01;
export const DEFAULT_WINDOW_DAYS_SHORT = 7;
export const DEFAULT_WINDOW_DAYS_LONG = 14;

/**
 * Computes ordinary least squares linear regression slope over (x, y) coordinates.
 *
 * @param {Array<{ x: number, y: number }>} points
 * @returns {number} Slope m (y = mx + c)
 */
export function calculateLinearSlope(points) {
  if (!Array.isArray(points) || points.length < 2) {
    return 0.0;
  }

  const n = points.length;
  let sumX = 0;
  let sumY = 0;
  let sumXY = 0;
  let sumXX = 0;

  for (let i = 0; i < n; i++) {
    const { x, y } = points[i];
    sumX += x;
    sumY += y;
    sumXY += x * y;
    sumXX += x * x;
  }

  const denominator = n * sumXX - sumX * sumX;
  if (Math.abs(denominator) < 1e-12) {
    return 0.0;
  }

  const slope = (n * sumXY - sumX * sumY) / denominator;
  return Number(slope.toFixed(4));
}

/**
 * Computes sample mean of array of numbers.
 *
 * @param {Array<number>} values
 * @returns {number|null}
 */
export function calculateMean(values) {
  if (!Array.isArray(values) || values.length === 0) return null;
  const sum = values.reduce((acc, v) => acc + v, 0);
  return Number((sum / values.length).toFixed(4));
}

/**
 * Computes sample standard deviation (ddof=1) of array of numbers.
 *
 * @param {Array<number>} values
 * @returns {number|null}
 */
export function calculateSampleStd(values) {
  if (!Array.isArray(values) || values.length === 0) return null;
  if (values.length === 1) return 0.0;

  const mean = values.reduce((acc, v) => acc + v, 0) / values.length;
  const sumSqDiff = values.reduce((acc, v) => acc + Math.pow(v - mean, 2), 0);
  const variance = sumSqDiff / (values.length - 1);
  return Number(Math.sqrt(variance).toFixed(4));
}

/**
 * Normalizes input daily history into a standardized 14-day array of daily slots.
 * Handles sparse arrays, date-keyed objects, or simple arrays of values.
 *
 * @param {Array<Object|number>} history
 * @param {number} windowDays
 * @returns {Array<{ dayIndex: number, date: string|null, value: number|null, quality: number|null }>}
 */
export function normalizeHistoryWindow(history, windowDays = DEFAULT_WINDOW_DAYS_LONG) {
  if (!Array.isArray(history)) return [];

  // Take the last `windowDays` items
  const sliced = history.slice(-windowDays);
  const normalized = [];

  for (let i = 0; i < sliced.length; i++) {
    const item = sliced[i];
    if (typeof item === 'number' && Number.isFinite(item)) {
      normalized.push({
        dayIndex: i,
        date: null,
        value: item,
        quality: 1.0,
      });
    } else if (item && typeof item === 'object') {
      const val = typeof item.value === 'number' && Number.isFinite(item.value)
        ? item.value
        : (typeof item.daily_value === 'number' ? item.daily_value : null);
      let q = null;
      if (typeof item.quality_score === 'number' && Number.isFinite(item.quality_score)) {
        q = item.quality_score;
      } else if (typeof item.quality === 'number' && Number.isFinite(item.quality)) {
        q = item.quality;
      } else if (val !== null && item.quality_score === undefined && item.quality === undefined) {
        q = 1.0;
      }

      normalized.push({
        dayIndex: i,
        date: item.date || item.feature_date || null,
        value: val,
        quality: q,
        z_score: item.z_score ?? item.deviation_score ?? null,
      });
    }
  }

  return normalized;
}

/**
 * Classifies trend pattern into one of the non-diagnostic categories:
 * - "Progressive deviation from personal baseline"
 * - "Improving toward baseline"
 * - "Stable within baseline"
 *
 * @param {number} slope - 14-day linear regression slope
 * @param {number} dailyValue - Today's measurement
 * @param {Object} baseline - Personal baseline
 * @param {Object} [options]
 * @param {number} [options.slopeThreshold=0.01] - Minimum slope to be deemed significant
 * @returns {string} Trend classification label
 */
export function classifyTrendDirection(slope, dailyValue, baseline, options = {}) {
  const slopeThreshold = typeof options.slopeThreshold === 'number'
    ? options.slopeThreshold
    : DEFAULT_SLOPE_THRESHOLD;

  if (typeof slope !== 'number' || Math.abs(slope) < slopeThreshold) {
    assertNonDiagnosticPhrasing(TREND_STABLE_BASELINE);
    return TREND_STABLE_BASELINE;
  }

  const baselineCenter = baseline?.baseline_mean ?? baseline?.baseline_median ?? dailyValue;
  const currentDiff = dailyValue - baselineCenter;

  // If daily value is above baseline:
  // - slope > 0 means moving further above (increasing deviation)
  // - slope < 0 means moving down towards baseline (improving)
  // If daily value is below baseline:
  // - slope < 0 means moving further below (increasing deviation)
  // - slope > 0 means moving up towards baseline (improving)
  const isMovingAway = (currentDiff >= 0 && slope > 0) || (currentDiff < 0 && slope < 0);
  const isMovingToward = (currentDiff > 0 && slope < 0) || (currentDiff < 0 && slope > 0);

  let label;
  if (isMovingAway) {
    label = TREND_PROGRESSIVE_DEVIATION;
  } else if (isMovingToward) {
    label = TREND_IMPROVING_TOWARD_BASELINE;
  } else {
    label = TREND_STABLE_BASELINE;
  }

  assertNonDiagnosticPhrasing(label);
  return label;
}

/**
 * Main Longitudinal Trend and Deviation Engine computation.
 *
 * Evaluates a sequence of daily observations against personal baseline and computes:
 * - daily_value
 * - 7_day_average
 * - 7_day_variability
 * - 14_day_trend
 * - baseline_deviation
 * - sustained_deviation
 * - missingness
 * - data_quality
 * - trend_label
 *
 * @param {Array<Object|number>} history - Observations up to 14 days (chronological)
 * @param {Object} baseline - Personal baseline record
 * @param {Object} [options]
 * @param {number} [options.slopeThreshold=0.01]
 * @returns {Object} Complete longitudinal trend and deviation metrics
 */
export function computeLongitudinalTrends(history, baseline, options = {}) {
  const normalized = normalizeHistoryWindow(history, DEFAULT_WINDOW_DAYS_LONG);

  if (normalized.length === 0) {
    return {
      daily_value: null,
      seven_day_average: null,
      seven_day_variability: null,
      fourteen_day_trend: 0.0,
      baseline_deviation: null,
      sustained_deviation: 0,
      missingness: 1.0,
      data_quality: 0.0,
      trend_label: TREND_STABLE_BASELINE,
      disclaimer: RESEARCH_DISCLAIMER,
    };
  }

  // Today's measurement is the latest entry
  const todayEntry = normalized[normalized.length - 1];
  const dailyValue = todayEntry.value;

  // 14-day missingness: based on DEFAULT_WINDOW_DAYS_LONG (14 days)
  const valid14Values = normalized.filter((item) => item.value !== null);
  const valid14Count = valid14Values.length;
  const missingness = Number(((DEFAULT_WINDOW_DAYS_LONG - valid14Count) / DEFAULT_WINDOW_DAYS_LONG).toFixed(4));

  // 7-day window: last 7 entries
  const last7 = normalized.slice(-DEFAULT_WINDOW_DAYS_SHORT);
  const valid7Values = last7.map((it) => it.value).filter((v) => v !== null);
  const sevenDayAverage = calculateMean(valid7Values);
  const sevenDayVariability = calculateSampleStd(valid7Values);

  // 7-day average data quality
  const valid7Qualities = last7.map((it) => it.quality).filter((q) => q !== null);
  const dataQuality = valid7Qualities.length > 0
    ? calculateMean(valid7Qualities)
    : 0.0;

  // 14-day trend: linear regression slope over valid points
  const pointsForSlope = valid14Values.map((it, idx) => ({
    x: it.dayIndex,
    y: it.value,
  }));
  const fourteenDayTrend = calculateLinearSlope(pointsForSlope);

  // Baseline deviation (z-score)
  const devResult = calculateDeviation(dailyValue, baseline);
  const baselineDeviation = devResult.deviation_score;

  // Sustained deviation: consecutive days with |z| > 2.0
  // Compute z-scores for all items in history
  const zHistory = normalized.map((it) => {
    if (it.z_score !== undefined && it.z_score !== null) {
      return it.z_score;
    }
    const d = calculateDeviation(it.value, baseline);
    return d.deviation_score;
  });
  const sustainedResult = calculateSustainedDeviation(zHistory);
  const sustainedDeviation = sustainedResult.consecutiveDays;

  // Trend pattern classification
  const trendLabel = classifyTrendDirection(fourteenDayTrend, dailyValue, baseline, options);

  return {
    daily_value: dailyValue !== null ? Number(dailyValue.toFixed(4)) : null,
    seven_day_average: sevenDayAverage,
    seven_day_variability: sevenDayVariability,
    fourteen_day_trend: fourteenDayTrend,
    baseline_deviation: baselineDeviation,
    sustained_deviation: sustainedDeviation,
    missingness: Math.max(0.0, Math.min(1.0, missingness)),
    data_quality: dataQuality !== null ? Math.max(0.0, Math.min(1.0, dataQuality)) : 0.0,
    trend_label: trendLabel,
    disclaimer: RESEARCH_DISCLAIMER,
  };
}

// Dual CommonJS / ES Module export
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    TREND_PROGRESSIVE_DEVIATION,
    TREND_STABLE_BASELINE,
    TREND_IMPROVING_TOWARD_BASELINE,
    DEFAULT_SLOPE_THRESHOLD,
    DEFAULT_WINDOW_DAYS_SHORT,
    DEFAULT_WINDOW_DAYS_LONG,
    calculateLinearSlope,
    calculateMean,
    calculateSampleStd,
    normalizeHistoryWindow,
    classifyTrendDirection,
    computeLongitudinalTrends,
  };
}
