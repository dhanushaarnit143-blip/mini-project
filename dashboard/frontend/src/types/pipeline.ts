/**
 * TypeScript Interfaces for MPF-PD API Data Models.
 * Strictly adheres to research prototype screening nomenclature.
 */

export interface Demographics {
  age: number;
  sex: 'female' | 'male';
}

export interface ModalityQuality {
  passed: boolean;
  issues: string[];
}

export interface IndividualModalityResult {
  available: boolean;
  status: 'success' | 'missing' | 'failed_qc' | 'error';
  risk_score: number | null;
  features: Record<string, any>;
  quality: ModalityQuality | null;
  warnings: string[];
}

export interface FusionResult {
  risk_score: number;
  risk_pattern: string;
  fused_embedding: number[];
  modality_presence: Record<string, boolean>;
  gate_weights: Record<string, number>;
  model_version: string;
  experiment_type: string;
  warnings: string[];
}

export interface ExplainabilityFeature {
  feature_name: string;
  feature_index: number;
  modality_group: string;
  shap_value: number;
  feature_value: number;
  direction: 'positive' | 'negative';
}

export interface ExplainabilityModality {
  modality: string;
  importance: number;
  percent_contribution: number;
  direction: string;
  missing: boolean;
}

export interface ExplainabilityResult {
  participant_id: string;
  risk_score: number;
  important_modalities: ExplainabilityModality[];
  important_features: ExplainabilityFeature[];
  positive_contributors: ExplainabilityFeature[];
  negative_contributors: ExplainabilityFeature[];
  missing_modalities: string[];
  missing_modality_notes: string[];
  modality_presence: Record<string, boolean>;
  gate_weights: Record<string, number>;
  shap_base_value: number;
  warnings: string[];
}

export interface AnalysisResponse {
  participant_id: string;
  demographics: Demographics;
  individual_modalities: Record<string, IndividualModalityResult>;
  fusion: FusionResult;
  explainability: ExplainabilityResult;
  missing_modalities: string[];
  warnings: string[];
}

export interface HealthResponse {
  status: string;
  version: string;
  models_loaded: Record<string, boolean>;
  message: string;
}
