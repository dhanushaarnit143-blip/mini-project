/**
 * MPF Mobile Extension — Baseline Module Index (Phase 10)
 *
 * Personal baseline engine learning individual normal behavior over 14 days,
 * then maintaining adaptive rolling baselines with outlier resistance.
 */

export * from './baselineCalculator.js';
export * from './outlierDetector.js';
export * from './baselineVersionManager.js';
export * from './adaptiveBaselineUpdater.js';
export * from './baselineEngine.js';

if (typeof module !== 'undefined' && module.exports) {
  const calc = require('./baselineCalculator.js');
  const outlier = require('./outlierDetector.js');
  const ver = require('./baselineVersionManager.js');
  const adapt = require('./adaptiveBaselineUpdater.js');
  const engine = require('./baselineEngine.js');

  module.exports = {
    ...calc,
    ...outlier,
    ...ver,
    ...adapt,
    ...engine,
  };
}
