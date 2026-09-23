-- Seed initial model versions for MPF risk-screening pipeline
-- Audit reproducibility registry

INSERT INTO model_versions (
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
