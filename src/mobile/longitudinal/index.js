/**
 * MPF Mobile Extension — Longitudinal Deviation and Trend Engine Index (Phase 11)
 *
 * Longitudinal monitoring module evaluating daily observations against personal baseline:
 * - deviationCalculator: Standardized z-score and MAD fallback
 * - trendDetector: Rolling 7-day and 14-day trends, variability, slope, and missingness
 * - sustainedDeviationDetector: Consecutive daily runs with |z| > 2.0 (>= 5 days)
 * - deviationClassifier: Standard non-diagnostic research classification labels
 */

export * from './deviationCalculator.js';
export * from './trendDetector.js';
export * from './sustainedDeviationDetector.js';
export * from './deviationClassifier.js';

if (typeof module !== 'undefined' && module.exports) {
  const calc = require('./deviationCalculator.js');
  const trend = require('./trendDetector.js');
  const sustained = require('./sustainedDeviationDetector.js');
  const classifier = require('./deviationClassifier.js');

  module.exports = {
    ...calc,
    ...trend,
    ...sustained,
    ...classifier,
  };
}
