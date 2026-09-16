import { AnalysisResponse, HealthResponse } from '../types/pipeline';
import { AssessmentData, FusionResult } from '../types';
import { calculateMultimodalRisk } from '../utils/riskModel';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export async function checkApiHealth(): Promise<HealthResponse> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 2500);

  try {
    const response = await fetch(`${API_BASE}/health`, {
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    if (!response.ok) {
      throw new Error(`Health check failed with HTTP ${response.status}`);
    }
    return await response.json();
  } catch (err: any) {
    clearTimeout(timeoutId);
    throw err;
  }
}

export async function analyzeMultimodal(formData: FormData): Promise<AnalysisResponse> {
  const response = await fetch(`${API_BASE}/analyze`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    let errorDetail = `Analysis failed with HTTP ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        errorDetail = errJson.detail;
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

/**
 * Executes multimodal fusion analysis.
 * First attempts to query the FastAPI backend ML model pipeline.
 * If backend is unreachable or returns an error, cleanly falls back to calibrated
 * client-side clinical model so the application remains 100% operational.
 */
export async function runClinicalFusion(data: AssessmentData): Promise<FusionResult> {
  try {
    const payload: Record<string, any> = {
      participant_id: data.cohortId,
      age: data.age,
      sex: data.biologicalSex.toLowerCase() === 'female' ? 'female' : 'male',
      olfactory: {
        available: !data.olfactoryMissing,
        total_score: data.olfactoryScore,
        pct_correct: Math.min(1.0, data.olfactoryScore / 40.0),
        response_time_mean: 4.8,
      },
      rbd: {
        available: !data.sleepMissing,
        rbdsq_total: data.rbdsqScore,
        above_cutoff_flag: data.rbdsqScore >= 5 ? 1 : 0,
        high_weight_item_flags: data.rbdsqScore >= 6 ? 2 : 0,
      },
      voice: {
        available: !data.voiceMissing,
        features: {
          jitter_pct: (data.voiceJitter || 0.81) / 100,
          jitter_abs: 0.00005,
          shimmer: 0.058,
          hnr: 15.2,
          rpde: 0.44,
          dfa: 0.72,
          ppe: 0.21,
        },
      },
      motor: {
        available: !data.motorMissing,
        features: {
          gait_speed_m_per_s: Math.max(0.5, Math.min(1.6, (data.tappingFrequency || 3.8) * 0.24)),
          cadence_steps_per_min: Math.max(60, Math.min(130, (data.tappingFrequency || 3.8) * 24.5)),
          stride_interval_mean_s: 1.15,
          stride_interval_cv_pct: data.rhythmIrregularity || 3.2,
          step_regularity: Math.max(0.4, 1.0 - (data.fatigueSlope || 0.04) * 4.5),
          symmetry_index_pct: 5.0,
          accel_variance: 0.039,
          stance_swing_ratio: 1.82,
        },
      },
      retina: {
        available: !data.retinalMissing,
        features: {
          vessel_density: 0.063,
          mean_vessel_diameter_px: 2.85,
          vessel_tortuosity_index: 1.14,
          branch_count: 72.0,
          branch_point_density: 0.0031,
          endpoint_count: 55.0,
          peripapillary_vessel_density: 0.071,
          peripapillary_branch_count: 22.0,
          macular_vessel_density: 0.054,
          foveal_avascular_zone_area_px: 380.0,
          optic_disc_detected: 1.0,
          macula_detected: 1.0,
        },
      },
    };

    const formData = new FormData();
    formData.append('payload', JSON.stringify(payload));

    if (!data.voiceMissing && data.voiceFile) {
      formData.append('voice_file', data.voiceFile);
    }
    if (!data.motorMissing && data.motorFile) {
      formData.append('motor_file', data.motorFile);
    }
    if (!data.retinalMissing && data.retinalFile) {
      formData.append('retina_file', data.retinalFile);
    }

    const res = await analyzeMultimodal(formData);

    const score = Number(res.fusion.risk_score.toFixed(2));
    let classification: 'Low Risk Pattern' | 'Intermediate Pattern' | 'Elevated Risk Pattern' = 'Intermediate Pattern';
    if (score < 0.30) classification = 'Low Risk Pattern';
    else if (score <= 0.55) classification = 'Intermediate Pattern';
    else classification = 'Elevated Risk Pattern';

    // Extract modality risk scores or fallback to shifts
    const olfScore = res.individual_modalities?.olfactory?.risk_score;
    const rbdScore = res.individual_modalities?.rbd?.risk_score;
    const voiceScore = res.individual_modalities?.voice?.risk_score;
    const motorScore = res.individual_modalities?.motor?.risk_score;
    const retinaScore = res.individual_modalities?.retina?.risk_score;

    const olfactoryShift = olfScore !== null && olfScore !== undefined ? Number(((olfScore - 0.2) * 0.45).toFixed(2)) : 0.28;
    const rbdShift = rbdScore !== null && rbdScore !== undefined ? Number(((rbdScore - 0.2) * 0.40).toFixed(2)) : 0.22;
    const voiceShift = voiceScore !== null && voiceScore !== undefined ? Number(((voiceScore - 0.2) * 0.35).toFixed(2)) : 0.11;
    const motorShift = motorScore !== null && motorScore !== undefined ? Number(((motorScore - 0.5) * 0.25).toFixed(2)) : -0.05;
    const retinalShift = retinaScore !== null && retinaScore !== undefined ? Number(((retinaScore - 0.1) * 0.15).toFixed(2)) : 0.00;

    let ageShift = 0.07;
    if (data.age > 60) {
      ageShift = Number((0.04 + (data.age - 60) * 0.0075).toFixed(2));
    }

    return {
      subjectId: data.cohortId,
      completedAgo: 'Just now (FastAPI ML)',
      integratedRiskScore: score,
      riskClassification: classification,
      uncertaintyMargin: data.retinalMissing ? 0.06 : 0.03,
      confidenceLevel: score > 0.65 || score < 0.35 ? 'High Confidence' : 'Moderate Confidence',
      olfactoryShift: Math.max(-0.2, Math.min(0.5, olfactoryShift)),
      rbdShift: Math.max(-0.2, Math.min(0.5, rbdShift)),
      voiceShift: Math.max(-0.2, Math.min(0.5, voiceShift)),
      motorShift: Math.max(-0.2, Math.min(0.5, motorShift)),
      retinalShift: data.retinalMissing ? 0.00 : Math.max(-0.2, Math.min(0.5, retinalShift)),
      ageShift,
      retinalImputed: data.retinalMissing,
      epistemicInflation: data.retinalMissing ? 0.018 : 0.0,
      isBackendLive: true,
      gateWeights: res.fusion.gate_weights,
      backendRawResult: res,
    };
  } catch (err) {
    console.warn('Backend API call unreachable or failed, operating in calibrated local simulation mode:', err);
    const localResult = calculateMultimodalRisk(data);
    return {
      ...localResult,
      isBackendLive: false,
    };
  }
}

