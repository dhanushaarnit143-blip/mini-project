/**
 * MPF Mobile Extension — Sustained Deviation Detector (Phase 11)
 *
 * Detects persistent longitudinal shifts away from personal baseline:
 * - Identifies consecutive days where |z_score| > 2.0.
 * - Flags "Sustained deviation detected" when consecutive days >= 5.
 *
 * NON-NEGOTIABLE COMPLIANCE:
 * - NO DIAGNOSTIC CLAIMS: Sustained deviation means "persistent departure from personal baseline".
 * - Never claims disease progression or clinical deterioration.
 */

import {
  CATEGORY_SUSTAINED_DEVIATION,
  assertNonDiagnosticPhrasing,
  RESEARCH_DISCLAIMER,
} from './deviationClassifier.js';

export const SUSTAINED_Z_THRESHOLD = 2.0;
export const SUSTAINED_MIN_DAYS = 5;

/**
 * Calculates the current consecutive streak of days with |z| > threshold ending at the latest day.
 *
 * @param {Array<number|Object>} history - Chronologically ordered series of daily observations
 *   Can be numbers (z-scores) or objects { z_score, deviation_score, date, ... }
 * @param {Object} [options]
 * @param {number} [options.threshold=2.0] - Z-score magnitude threshold
 * @param {number} [options.minDays=5] - Minimum consecutive days to flag sustained deviation
 * @returns {Object} Sustained deviation assessment
 */
export function calculateSustainedDeviation(history, options = {}) {
  const threshold = typeof options.threshold === 'number' ? options.threshold : SUSTAINED_Z_THRESHOLD;
  const minDays = typeof options.minDays === 'number' ? options.minDays : SUSTAINED_MIN_DAYS;

  if (!Array.isArray(history) || history.length === 0) {
    return {
      consecutiveDays: 0,
      isSustained: false,
      threshold,
      minDays,
      status: 'No observations recorded',
      classification: null,
      disclaimer: RESEARCH_DISCLAIMER,
    };
  }

  // Extract z-score from each item (handles raw numbers or object rows)
  const zList = history.map((item) => {
    if (typeof item === 'number' && Number.isFinite(item)) {
      return item;
    }
    if (item && typeof item === 'object') {
      const z = item.z_score ?? item.deviation_score;
      if (typeof z === 'number' && Number.isFinite(z)) {
        return z;
      }
    }
    return null;
  });

  // Calculate current streak counting backwards from the most recent day (end of array)
  let consecutiveDays = 0;
  for (let i = zList.length - 1; i >= 0; i--) {
    const z = zList[i];
    if (z !== null && Math.abs(z) > threshold) {
      consecutiveDays += 1;
    } else {
      // Streak broken
      break;
    }
  }

  const isSustained = consecutiveDays >= minDays;
  const classification = isSustained ? CATEGORY_SUSTAINED_DEVIATION : null;
  if (classification) {
    assertNonDiagnosticPhrasing(classification);
  }

  return {
    consecutiveDays,
    isSustained,
    threshold,
    minDays,
    classification,
    status: isSustained
      ? `Sustained deviation detected: |z| > ${threshold} for ${consecutiveDays} consecutive days`
      : consecutiveDays > 0
        ? `Transient deviation: |z| > ${threshold} for ${consecutiveDays} consecutive days (below ${minDays}-day threshold)`
        : 'Measurements consistent with personal baseline envelope',
    disclaimer: RESEARCH_DISCLAIMER,
  };
}

/**
 * Analyzes an entire longitudinal sequence to detect all historical sustained deviation periods.
 *
 * @param {Array<Object>} dailyRecords - Chronologically ordered daily records with { date, z_score }
 * @param {Object} [options]
 * @returns {Object} Comprehensive sustained deviation profile
 */
export function analyzeSustainedRuns(dailyRecords, options = {}) {
  const threshold = typeof options.threshold === 'number' ? options.threshold : SUSTAINED_Z_THRESHOLD;
  const minDays = typeof options.minDays === 'number' ? options.minDays : SUSTAINED_MIN_DAYS;

  if (!Array.isArray(dailyRecords) || dailyRecords.length === 0) {
    return {
      currentStreak: 0,
      maxStreak: 0,
      sustainedPeriods: [],
      isCurrentlySustained: false,
      disclaimer: RESEARCH_DISCLAIMER,
    };
  }

  let currentRun = 0;
  let maxRun = 0;
  const sustainedPeriods = [];
  let periodStart = null;

  for (let i = 0; i < dailyRecords.length; i++) {
    const rec = dailyRecords[i];
    const z = typeof rec === 'number' ? rec : (rec.z_score ?? rec.deviation_score);
    const date = rec.date || `day_${i + 1}`;

    if (typeof z === 'number' && Number.isFinite(z) && Math.abs(z) > threshold) {
      if (currentRun === 0) {
        periodStart = date;
      }
      currentRun += 1;
      if (currentRun > maxRun) {
        maxRun = currentRun;
      }
    } else {
      if (currentRun >= minDays) {
        sustainedPeriods.push({
          startDate: periodStart,
          endDate: dailyRecords[i - 1]?.date || `day_${i}`,
          durationDays: currentRun,
          threshold,
        });
      }
      currentRun = 0;
      periodStart = null;
    }
  }

  // Check if final run reached threshold
  if (currentRun >= minDays) {
    sustainedPeriods.push({
      startDate: periodStart,
      endDate: dailyRecords[dailyRecords.length - 1]?.date || `day_${dailyRecords.length}`,
      durationDays: currentRun,
      threshold,
    });
  }

  const latestAssessment = calculateSustainedDeviation(dailyRecords, options);

  return {
    currentStreak: latestAssessment.consecutiveDays,
    maxStreak: maxRun,
    isCurrentlySustained: latestAssessment.isSustained,
    sustainedPeriods,
    threshold,
    minDays,
    classification: latestAssessment.classification,
    disclaimer: RESEARCH_DISCLAIMER,
  };
}

// Dual CommonJS / ES Module export
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    SUSTAINED_Z_THRESHOLD,
    SUSTAINED_MIN_DAYS,
    calculateSustainedDeviation,
    analyzeSustainedRuns,
  };
}
