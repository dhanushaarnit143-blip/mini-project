-- ============================================================================
-- Supabase Database Seed File: Model Versions & Reference Research Cohort
-- File: supabase/seed.sql
-- ============================================================================

-- 1. SEED MODEL VERSIONS
INSERT INTO public.model_versions (
    id,
    model_name,
    version,
    feature_schema_version,
    training_dataset_version,
    metrics,
    active,
    created_at
) VALUES 
(
    'a0000000-0000-0000-0000-000000000001',
    'gated_multimodal_fusion',
    'v1.0.0',
    '1.0.0',
    'mpf_multimodal_prodromal_v1',
    '{
        "auroc": 0.884,
        "sensitivity_at_90_spec": 0.742,
        "calibration_brier_score": 0.089,
        "modalities_supported": ["typing", "voice", "motor", "visual", "sleep"]
    }'::jsonb,
    true,
    NOW()
),
(
    'a0000000-0000-0000-0000-000000000002',
    'baseline_deviation_evaluator',
    'v1.0.0',
    '1.0.0',
    'normative_calibration_cohort_v1',
    '{
        "robust_estimator": "median_mad",
        "minimum_calibration_days": 14,
        "outlier_threshold_mad": 2.5
    }'::jsonb,
    true,
    NOW()
),
(
    'a0000000-0000-0000-0000-000000000003',
    'mobile_adapter_gating',
    'v1.0.0',
    '1.0.0',
    'mpf_synthetic_bench_v1',
    '{
        "imputation_strategy": "learned_latent_prior",
        "max_missing_modality_fraction": 0.60
    }'::jsonb,
    true,
    NOW()
)
ON CONFLICT (model_name, version) DO UPDATE SET
    feature_schema_version = EXCLUDED.feature_schema_version,
    training_dataset_version = EXCLUDED.training_dataset_version,
    metrics = EXCLUDED.metrics,
    active = EXCLUDED.active;

-- 2. SEED ACTIVE COHORT PARTICIPANTS (Initial longitudinal reference cohort)
INSERT INTO public.cohort_participants (
    id,
    cohort_code,
    visit_label,
    clinical_notes,
    risk_index,
    risk_class,
    avatar_color,
    demographics
) VALUES
(
    'b0000000-0000-0000-0000-000000000001',
    '#PD-7821',
    'Visit 3',
    'Olfactory drop + Mild REM atonia',
    0.74,
    'Elevated Pattern',
    'amber',
    '{"age": 67, "sex": "Female", "familyHistory": true, "subscores": {"olfactory": 15, "rbdsq": 10, "voiceJitter": 1.15, "tappingFrequency": 2.9, "retinalOcularDeficit": true}}'::jsonb
),
(
    'b0000000-0000-0000-0000-000000000002',
    '#PD-4419',
    'Visit 1 (Baseline)',
    'Isolated severe hyposmia, normative sleep',
    0.41,
    'Intermediate',
    'sky',
    '{"age": 61, "sex": "Male", "familyHistory": false, "subscores": {"olfactory": 14, "rbdsq": 3, "voiceJitter": 0.42, "tappingFrequency": 4.5, "retinalOcularDeficit": false}}'::jsonb
),
(
    'b0000000-0000-0000-0000-000000000003',
    '#CTRL-1092',
    'Annual Follow-up',
    'Healthy normosmic control',
    0.12,
    'Low Risk Pattern',
    'emerald',
    '{"age": 59, "sex": "Female", "familyHistory": false, "subscores": {"olfactory": 36, "rbdsq": 1, "voiceJitter": 0.31, "tappingFrequency": 5.1, "retinalOcularDeficit": false}}'::jsonb
),
(
    'b0000000-0000-0000-0000-000000000004',
    '#PD-9104',
    'Visit 2',
    'Active RBD + Subtle vocal tremor',
    0.83,
    'Elevated Pattern',
    'amber',
    '{"age": 72, "sex": "Male", "familyHistory": true, "subscores": {"olfactory": 19, "rbdsq": 11, "voiceJitter": 1.34, "tappingFrequency": 3.1, "retinalOcularDeficit": true}}'::jsonb
),
(
    'b0000000-0000-0000-0000-000000000005',
    '#PD-3205',
    'Visit 4',
    'Motor cadence variability + Normal Olfaction',
    0.58,
    'Intermediate',
    'sky',
    '{"age": 65, "sex": "Female", "familyHistory": false, "subscores": {"olfactory": 28, "rbdsq": 4, "voiceJitter": 0.62, "tappingFrequency": 3.4, "retinalOcularDeficit": false}}'::jsonb
),
(
    'b0000000-0000-0000-0000-000000000006',
    '#CTRL-8831',
    'Baseline Validation',
    'Normative control, unimpaired metrics',
    0.08,
    'Low Risk Pattern',
    'emerald',
    '{"age": 54, "sex": "Male", "familyHistory": false, "subscores": {"olfactory": 38, "rbdsq": 0, "voiceJitter": 0.28, "tappingFrequency": 5.4, "retinalOcularDeficit": false}}'::jsonb
)
ON CONFLICT (cohort_code) DO UPDATE SET
    visit_label = EXCLUDED.visit_label,
    clinical_notes = EXCLUDED.clinical_notes,
    risk_index = EXCLUDED.risk_index,
    risk_class = EXCLUDED.risk_class,
    avatar_color = EXCLUDED.avatar_color,
    demographics = EXCLUDED.demographics,
    updated_at = NOW();
