export type ScreenId = 'overview' | 'new-assessment' | 'results-dashboard' | 'explainability-shap';

export interface AssessmentData {
  cohortId: string;
  age: number;
  biologicalSex: 'Male' | 'Female' | 'Other';
  familyHistory: boolean;
  
  // Section A: Olfactory
  olfactoryMissing: boolean;
  olfactoryInstrument: 'UPSIT (40-item)' | 'Sniffin\' Sticks 16';
  olfactoryScore: number; // 0 - 40
  
  // Section B: Sleep / RBD
  sleepMissing: boolean;
  rbdsqScore: number; // 0 - 13
  dreamEnactmentBehavior: string;
  
  // Section C: Voice
  voiceMissing: boolean;
  voiceFileName: string;
  voiceDuration: number;
  voiceJitter: number;
  isVoiceUploaded: boolean;
  voiceFile?: File | null;
  
  // Section D: Motor
  motorMissing: boolean;
  tappingFrequency: number; // taps/s
  fatigueSlope: number; // s^-1
  rhythmIrregularity: number; // %
  motorFileName?: string;
  motorFile?: File | null;
  
  // Section E: Retinal OCT
  retinalMissing: boolean;
  retinalLayerQcPassed: boolean;
  retinalFileName?: string;
  retinalFile?: File | null;
}

export interface FusionResult {
  subjectId: string;
  completedAgo: string;
  integratedRiskScore: number; // 0.0 - 1.0
  riskClassification: 'Low Risk Pattern' | 'Intermediate Pattern' | 'Elevated Risk Pattern';
  uncertaintyMargin: number; // e.g., 0.06
  confidenceLevel: 'High Confidence' | 'Moderate Confidence' | 'Wider Variance';
  
  // Shifts
  olfactoryShift: number;
  rbdShift: number;
  voiceShift: number;
  motorShift: number;
  retinalShift: number;
  ageShift: number;
  
  retinalImputed: boolean;
  epistemicInflation: number;

  // Real backend metadata
  isBackendLive?: boolean;
  gateWeights?: Record<string, number>;
  backendRawResult?: any;
}

export interface CohortParticipant {
  id: string;
  visit: string;
  notes: string;
  riskIndex: number;
  riskClass: 'Low Risk Pattern' | 'Intermediate' | 'Elevated Pattern';
  avatarType: 'amber' | 'emerald' | 'gray';
  assessmentData: AssessmentData;
}

