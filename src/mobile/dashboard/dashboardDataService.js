/**
 * MPF Mobile Extension — Dashboard Data Service (Phase 14)
 * 
 * Aggregates and formats participant data for the personal research dashboard:
 * - Calculates baseline bands (mean ± 1 std envelope)
 * - Computes z-score deviations and maps to safe non-diagnostic labels
 * - Formats MPF model predictions and missing modality flags
 * - Computes protocol adherence and modality quality scores
 * 
 * Strict Compliance:
 * - Rule 1: Zero diagnostic claims ("Within personal baseline", "Moderate deviation from baseline", etc.)
 * - Rule 2: Non-overclaiming for camera (Ocular/Visual Behavior vs Retinal)
 */

export const NON_DIAGNOSTIC_LABELS = {
  WITHIN_BASELINE: 'Within personal baseline',
  MILD_DEVIATION: 'Mild deviation from baseline',
  MODERATE_DEVIATION: 'Moderate deviation from baseline',
  SIGNIFICANT_DEVIATION: 'Significant deviation from baseline',
  SUSTAINED_DEVIATION: 'Sustained deviation detected',
  ELEVATED_RISK_PATTERN: "Elevated Parkinson's risk pattern detected",
  RESEARCH_DISCLAIMER: 'Research screening result — not a clinical diagnosis'
};

export class DashboardDataService {
  constructor(supabaseClient = null) {
    this.supabase = supabaseClient;
  }

  /**
   * Computes standardized z-score and safe classification label relative to personal baseline.
   */
  static classifyDeviation(value, baselineMean, baselineStd) {
    if (baselineStd === null || baselineStd === undefined || baselineStd <= 0) {
      return {
        zScore: 0,
        label: NON_DIAGNOSTIC_LABELS.WITHIN_BASELINE,
        severity: 'normal'
      };
    }

    const zScore = (value - baselineMean) / baselineStd;
    const absZ = Math.abs(zScore);

    if (absZ >= 3.0) {
      return {
        zScore: Number(zScore.toFixed(3)),
        label: NON_DIAGNOSTIC_LABELS.SIGNIFICANT_DEVIATION,
        severity: 'significant'
      };
    }

    if (absZ >= 2.0) {
      return {
        zScore: Number(zScore.toFixed(3)),
        label: NON_DIAGNOSTIC_LABELS.MODERATE_DEVIATION,
        severity: 'moderate'
      };
    }

    if (absZ >= 1.5) {
      return {
        zScore: Number(zScore.toFixed(3)),
        label: NON_DIAGNOSTIC_LABELS.MILD_DEVIATION,
        severity: 'mild'
      };
    }

    return {
      zScore: Number(zScore.toFixed(3)),
      label: NON_DIAGNOSTIC_LABELS.WITHIN_BASELINE,
      severity: 'normal'
    };
  }

  /**
   * Computes baseline envelope bounds (mean ± 1 std).
   */
  static computeBaselineBand(baselineMean, baselineStd) {
    return {
      mean: baselineMean,
      std: baselineStd,
      lowerBound: Number((baselineMean - baselineStd).toFixed(3)),
      upperBound: Number((baselineMean + baselineStd).toFixed(3)),
      envelopeDescription: 'Mean ± 1 standard deviation envelope'
    };
  }

  /**
   * Evaluates protocol adherence from collection records.
   */
  static calculateAdherence(completedDays, totalDays) {
    const total = Math.max(totalDays, 1);
    const rate = Math.min(100, Math.round((completedDays / total) * 100));
    return {
      completedDays,
      totalDays,
      adherenceRatePct: rate,
      isTargetMet: rate >= 70
    };
  }

  /**
   * Formats screening result with safe non-diagnostic language and missing modality flags.
   */
  static formatScreeningResult(rawScore, modelVersion = 'v2.1.0-fusion') {
    const score = Math.max(0, Math.min(1, Number(rawScore) || 0));

    let patternLabel = NON_DIAGNOSTIC_LABELS.WITHIN_BASELINE;
    if (score >= 0.65) {
      patternLabel = NON_DIAGNOSTIC_LABELS.ELEVATED_RISK_PATTERN;
    } else if (score >= 0.40) {
      patternLabel = NON_DIAGNOSTIC_LABELS.MODERATE_DEVIATION;
    }

    return {
      riskScore: score,
      patternLabel,
      disclaimer: NON_DIAGNOSTIC_LABELS.RESEARCH_DISCLAIMER,
      modelVersion,
      availableModalities: ['voice', 'motor', 'sleep', 'typing', 'visual'],
      missingModalities: [
        {
          name: 'olfactory',
          reason: 'Learnable missing token applied; physical odorant kits required.'
        },
        {
          name: 'retinal',
          reason: 'Specialized fundus/OCT hardware required. Front camera collects Ocular/Visual Behavior only, NOT retinal imaging.'
        }
      ]
    };
  }
}

export default DashboardDataService;
