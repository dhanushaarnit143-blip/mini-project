import { supabase } from './supabase';
import { CohortParticipant, AssessmentData, FusionResult } from '../types';
import { activeCohortList, initialAssessmentData } from '../data/mockCohort';

/**
 * Fetch all cohort participants from Supabase.
 * Falls back gracefully to seeded reference cohort if offline or unauthenticated.
 */
export async function fetchCohortParticipants(): Promise<CohortParticipant[]> {
  try {
    const { data, error } = await supabase
      .from('cohort_participants')
      .select('*')
      .order('risk_index', { ascending: false });

    if (error || !data || data.length === 0) {
      return activeCohortList;
    }

    return data.map((row) => ({
      id: row.cohort_code,
      visit: row.visit_label || 'Visit 1',
      notes: row.clinical_notes || '',
      riskIndex: Number(row.risk_index) || 0.0,
      riskClass: row.risk_class || 'Intermediate',
      avatarType: row.avatar_color || 'emerald',
      assessmentData: {
        ...initialAssessmentData,
        cohortId: row.cohort_code.replace('#', ''),
        age: row.demographics?.age ?? 65,
        biologicalSex: row.demographics?.sex ?? 'Male',
        familyHistory: row.demographics?.familyHistory ?? false,
        olfactoryScore: row.demographics?.subscores?.olfactory ?? 25,
        rbdsqScore: row.demographics?.subscores?.rbdsq ?? 4,
        voiceJitter: row.demographics?.subscores?.voiceJitter ?? 0.81,
        tappingFrequency: row.demographics?.subscores?.tappingFrequency ?? 3.8,
        retinalMissing: !(row.demographics?.subscores?.retinalOcularDeficit),
      },
    }));
  } catch (e) {
    console.warn('Failed to query Supabase cohort, falling back to local cohort cache:', e);
    return activeCohortList;
  }
}

/**
 * Create a new cohort participant in Supabase.
 */
export async function createCohortParticipant(participant: {
  cohortCode: string;
  visitLabel: string;
  notes?: string;
  riskIndex?: number;
  riskClass?: 'Low Risk Pattern' | 'Intermediate' | 'Elevated Pattern';
  avatarColor?: string;
  demographics?: Record<string, any>;
}): Promise<boolean> {
  try {
    const { data: sessionData } = await supabase.auth.getSession();
    const userId = sessionData?.session?.user?.id || null;

    const { error } = await supabase.from('cohort_participants').insert([
      {
        user_id: userId,
        cohort_code: participant.cohortCode.startsWith('#') ? participant.cohortCode : `#${participant.cohortCode}`,
        visit_label: participant.visitLabel,
        clinical_notes: participant.notes || '',
        risk_index: participant.riskIndex ?? 0.25,
        risk_class: participant.riskClass ?? 'Low Risk Pattern',
        avatar_color: participant.avatarColor ?? 'emerald',
        demographics: participant.demographics || {},
      },
    ]);

    if (error) throw error;
    return true;
  } catch (err) {
    console.error('Error inserting cohort participant into Supabase:', err);
    return false;
  }
}

/**
 * Delete a cohort participant from Supabase.
 */
export async function deleteCohortParticipant(cohortCode: string): Promise<boolean> {
  try {
    const formattedCode = cohortCode.startsWith('#') ? cohortCode : `#${cohortCode}`;
    const { error } = await supabase
      .from('cohort_participants')
      .delete()
      .eq('cohort_code', formattedCode);

    if (error) throw error;
    return true;
  } catch (err) {
    console.error('Error deleting cohort participant from Supabase:', err);
    return false;
  }
}

/**
 * Save an assessment record into Supabase.
 */
export async function saveAssessmentRecord(data: AssessmentData): Promise<string | null> {
  try {
    const { data: sessionData } = await supabase.auth.getSession();
    const userId = sessionData?.session?.user?.id || null;

    const { data: record, error } = await supabase
      .from('assessments')
      .insert([
        {
          user_id: userId,
          cohort_id: data.cohortId,
          age: data.age,
          biological_sex: data.biologicalSex,
          family_history: data.familyHistory,
          olfactory_data: {
            missing: data.olfactoryMissing,
            instrument: data.olfactoryInstrument,
            score: data.olfactoryScore,
          },
          sleep_data: {
            missing: data.sleepMissing,
            rbdsq_score: data.rbdsqScore,
            dream_enactment: data.dreamEnactmentBehavior,
          },
          voice_data: {
            missing: data.voiceMissing,
            file_name: data.voiceFileName,
            duration: data.voiceDuration,
            jitter: data.voiceJitter,
          },
          motor_data: {
            missing: data.motorMissing,
            tapping_frequency: data.tappingFrequency,
            fatigue_slope: data.fatigueSlope,
            rhythm_irregularity: data.rhythmIrregularity,
          },
          retinal_data: {
            missing: data.retinalMissing,
            qc_passed: data.retinalLayerQcPassed,
          },
          status: 'analyzed',
        },
      ])
      .select('id')
      .single();

    if (error) throw error;
    return record?.id || null;
  } catch (err) {
    console.warn('Could not persist assessment to Supabase:', err);
    return null;
  }
}

/**
 * Persist fusion analysis results and SHAP explanations into Supabase.
 */
export async function saveFusionResultRecord(
  assessmentId: string,
  result: FusionResult
): Promise<boolean> {
  try {
    const { data: sessionData } = await supabase.auth.getSession();
    const userId = sessionData?.session?.user?.id || null;

    const { error } = await supabase.from('fusion_results').insert([
      {
        assessment_id: assessmentId,
        user_id: userId,
        risk_score: result.integratedRiskScore,
        risk_category: result.riskClassification,
        radar_scores: {
          olfactory: result.olfactoryShift,
          rbd: result.rbdShift,
          voice: result.voiceShift,
          motor: result.motorShift,
          retinal: result.retinalShift,
          age: result.ageShift,
        },
        modality_contributions: result.gateWeights || {},
        shap_explanations: result.backendRawResult?.local_explanation || {},
        gate_weights: result.gateWeights || {},
        missing_modalities: result.backendRawResult?.missing_modalities || [],
      },
    ]);

    if (error) throw error;
    return true;
  } catch (err) {
    console.warn('Could not persist fusion result to Supabase:', err);
    return false;
  }
}

/**
 * Upload clinical audio, sensor, or ocular files to Supabase Storage.
 */
export async function uploadClinicalFile(
  file: File,
  category: 'voice' | 'motor' | 'ocular'
): Promise<string | null> {
  try {
    const { data: sessionData } = await supabase.auth.getSession();
    const userId = sessionData?.session?.user?.id || 'anonymous';
    const filePath = `${userId}/${category}/${Date.now()}_${file.name}`;

    const { error } = await supabase.storage
      .from('uploads')
      .upload(filePath, file, { upsert: true });

    if (error) throw error;

    const { data: publicData } = supabase.storage
      .from('uploads')
      .getPublicUrl(filePath);

    return publicData.publicUrl;
  } catch (err) {
    console.warn('Supabase storage upload failed:', err);
    return null;
  }
}
