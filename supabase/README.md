# MPF-PD Mobile Extension — Supabase Architecture & Database Schema

**Project:** Multimodal Prodromal Fusion for Parkinson's Disease Risk Screening (MPF-PD)  
**Component:** Supabase Real-Time Backend & Data Engineering Layer  
**Phase:** PHASE A — Schema, Authentication, and Row Level Security (RLS)  
**Status:** Completed & Validated  
**Notice:** Research screening prototype only. Not for clinical diagnosis.

---

## 1. Architectural Overview & Compliance

The Supabase backend provides the secure, HIPAA/GDPR-aligned data engineering foundation for multimodal prodromal screening data collection:

1. **Non-Diagnostic Framing:** `mpf_predictions` records risk scores as research probabilities (0.0 to 1.0) with non-diagnostic metadata.
2. **Zero Raw Audio / Keystroke Text / Raw Video Storage:**
   - Keystroke dynamics store only inter-key intervals, flight times, and rhythm variability (no character codes or text).
   - Voice sessions store acoustic features (jitter, shimmer, HNR, MFCCs) — raw audio is never stored by default.
   - Visual sessions record ocular behavior metrics (blink rate, fixation stability, saccadic latency) — strictly behavioral, never retinal fundus imaging.
3. **Strict Idempotency:** Every session table contains a unique `session_id` preventing duplicate ingestion during network retries or offline sync.
4. **Longitudinal Personal Baselines:** 14-day calibration curves are stored in `personal_baselines` with median/MAD statistics; daily departures are recorded in `daily_deviations`.
5. **Frozen Checkpointed Models:** `model_versions` is strictly read-only for authenticated users, separating inference from offline model training.

---

## 2. Directory Layout

```
supabase/
├── migrations/
│   ├── 001_create_participants.sql      # Pseudonymized participant registry
│   ├── 002_create_consent_records.sql   # Dynamic informed consent audit log
│   ├── 003_create_session_tables.sql    # Typing, Voice, Motor, Visual, and Sleep sessions
│   ├── 004_create_daily_features.sql    # Daily multimodal feature aggregation vectors
│   ├── 005_create_personal_baselines.sql# 14-day calibration & rolling adaptive baselines
│   ├── 006_create_daily_deviations.sql  # Statistical z-score deviations from baseline
│   ├── 007_create_mpf_predictions.sql   # Research risk screening inference audit trail
│   ├── 008_create_model_versions.sql    # Checkpointed frozen model registry
│   └── 009_create_rls_policies.sql      # Complete RLS enforcement across all 12 tables
├── seed/
│   └── seed_model_versions.sql          # Seed records for frozen MPF model checkpoints
└── README.md                            # Documentation and schema guide
```

---

## 3. Database Schema (12 Tables)

### 3.1 `participants`
Pseudonymized participant registry. Primary key matches `auth.uid()`.
- `id` (UUID, PK, default `gen_random_uuid()`): Participant identifier.
- `created_at` (TIMESTAMPTZ, default `now()`): Account creation timestamp.
- `email` (TEXT, UNIQUE): Participant email for authentication.
- `pseudonymous_id` (TEXT, UNIQUE): Cryptographic pseudonym.
- `consent_version` (TEXT): Active informed consent version.
- `consent_timestamp` (TIMESTAMPTZ): Consent timestamp.
- `app_version` (TEXT): Client application version.
- `model_version` (TEXT): Model version assigned.
- `baseline_status` (TEXT): Status (`collecting`, `established`, `adaptive`).
- `is_active` (BOOLEAN, default `true`): Account activity status.

### 3.2 `consent_records`
Audit trail of all consent grants and revocations.
- `id` (UUID, PK, default `gen_random_uuid()`): Record identifier.
- `participant_id` (UUID, FK → `participants.id` ON DELETE CASCADE).
- `consent_type` (TEXT: `data_collection`, `audio_storage`, `research_export`).
- `consent_version` (TEXT): Version of consent document.
- `granted` (BOOLEAN): Consent granted state.
- `timestamp` (TIMESTAMPTZ, default `now()`): Action timestamp.
- `revoked_at` (TIMESTAMPTZ, nullable): Revocation timestamp.

### 3.3 `typing_sessions`
Keystroke timing dynamics (zero text or key codes).
- `id` (UUID, PK): Session record ID.
- `participant_id` (UUID, FK → `participants.id`).
- `session_id` (TEXT, UNIQUE): Client idempotency key.
- `timestamp` (TIMESTAMPTZ): Session completion time.
- `task_type` (TEXT): Typing test protocol.
- `duration` (NUMERIC): Task duration (seconds).
- `typing_speed` (NUMERIC): Keystrokes per second.
- `mean_inter_key_interval` (NUMERIC): Mean IKI (ms).
- `std_inter_key_interval` (NUMERIC): Standard deviation of IKI.
- `pause_rate` (NUMERIC): Pauses per second.
- `correction_rate` (NUMERIC): Backspace/delete rate.
- `rhythm_variability` (NUMERIC): Coefficient of variation.
- `quality_score` (NUMERIC, 0.0–1.0): Signal quality metric.
- `feature_version` (TEXT): Extraction pipeline version.
- `synced` (BOOLEAN, default `false`): Sync status flag.

### 3.4 `voice_sessions`
Acoustic feature vectors extracted on-device (zero raw audio).
- `id` (UUID, PK): Session record ID.
- `participant_id` (UUID, FK → `participants.id`).
- `session_id` (TEXT, UNIQUE): Client idempotency key.
- `timestamp` (TIMESTAMPTZ): Recording timestamp.
- `task_type` (TEXT): Sustained vowel or reading task.
- `duration` (NUMERIC): Audio length (seconds).
- `signal_quality` (NUMERIC): SNR / audio signal quality.
- `jitter` (NUMERIC): Local pitch perturbation.
- `shimmer` (NUMERIC): Local amplitude perturbation.
- `hnr` (NUMERIC): Harmonics-to-noise ratio (dB).
- `pitch_mean` (NUMERIC): Fundamental frequency mean (Hz).
- `pitch_std` (NUMERIC): Fundamental frequency standard deviation.
- `mfcc_features` (JSONB): 13 Mel-frequency cepstral coefficients.
- `quality_score` (NUMERIC, 0.0–1.0): Voice quality index.
- `feature_version` (TEXT): Acoustic extractor version.
- `synced` (BOOLEAN, default `false`): Sync status flag.

### 3.5 `motor_sessions`
Motor, gait, tapping, and postural tremor kinematics.
- `id` (UUID, PK): Record ID.
- `participant_id` (UUID, FK → `participants.id`).
- `session_id` (TEXT, UNIQUE): Client idempotency key.
- `timestamp` (TIMESTAMPTZ): Session timestamp.
- `task_type` (TEXT: `walking`, `tapping`, `tremor_hold`).
- `duration` (NUMERIC): Duration in seconds.
- `cadence` (NUMERIC, nullable): Steps per minute.
- `stride_variability` (NUMERIC, nullable): Gait irregularity.
- `tapping_rate` (NUMERIC, nullable): Taps per second.
- `tapping_interval_variability` (NUMERIC, nullable): Tapping variance.
- `tremor_frequency` (NUMERIC, nullable): Peak frequency (Hz).
- `tremor_amplitude` (NUMERIC, nullable): Tremor displacement.
- `quality_score` (NUMERIC, 0.0–1.0): Sensor quality score.
- `feature_version` (TEXT): Feature version tag.
- `synced` (BOOLEAN, default `false`): Sync flag.

### 3.6 `visual_sessions`
Ocular and visual behavior dynamics (explicitly NOT retinal imaging).
- `id` (UUID, PK): Record ID.
- `participant_id` (UUID, FK → `participants.id`).
- `session_id` (TEXT, UNIQUE): Client idempotency key.
- `timestamp` (TIMESTAMPTZ): Session timestamp.
- `task_type` (TEXT: `tracking`, `blink`, `reaction`).
- `duration` (NUMERIC): Duration in seconds.
- `blink_rate` (NUMERIC, nullable): Blinks per minute.
- `blink_interval_variability` (NUMERIC, nullable): Inter-blink interval variance.
- `gaze_stability` (NUMERIC, nullable): Fixation stability score.
- `reaction_time` (NUMERIC, nullable): Saccadic latency (ms).
- `quality_score` (NUMERIC, 0.0–1.0): Tracking quality index.
- `feature_version` (TEXT): Feature version tag.
- `synced` (BOOLEAN, default `false`): Sync flag.

### 3.7 `sleep_sessions`
Self-reported and passive sleep dynamics and RBD questionnaire.
- `id` (UUID, PK): Record ID.
- `participant_id` (UUID, FK → `participants.id`).
- `session_id` (TEXT, UNIQUE): Client idempotency key.
- `timestamp` (TIMESTAMPTZ): Log timestamp.
- `sleep_duration` (NUMERIC): Total sleep time (hours).
- `sleep_quality` (NUMERIC, 1–5): Likert sleep quality rating.
- `unusual_movement_self_report` (BOOLEAN): RBD dream-enactment report.
- `daytime_sleepiness` (NUMERIC, 1–5): Epworth-aligned sleepiness score.
- `questionnaire_version` (TEXT): Questionnaire schema version.
- `score` (NUMERIC): Computed sleep composite score.
- `synced` (BOOLEAN, default `false`): Sync flag.

### 3.8 `daily_features`
Standardized daily multimodal feature vectors.
- `id` (UUID, PK): Record ID.
- `participant_id` (UUID, FK → `participants.id`).
- `date` (DATE): Assessment calendar date.
- `typing_features` (JSONB): Daily aggregated typing metrics.
- `voice_features` (JSONB): Daily aggregated voice metrics.
- `motor_features` (JSONB): Daily aggregated motor metrics.
- `visual_features` (JSONB): Daily aggregated visual behavior metrics.
- `sleep_features` (JSONB): Daily aggregated sleep metrics.
- `data_quality` (JSONB): Multimodal quality validation report.
- `feature_version` (TEXT): Aggregation pipeline version.
- `created_at` (TIMESTAMPTZ): Record timestamp.
- `UNIQUE(participant_id, date)`: Enforces one summary per participant per day.

### 3.9 `personal_baselines`
Personalized normative baselines computed over a minimum 14-day calibration window.
- `id` (UUID, PK): Record ID.
- `participant_id` (UUID, FK → `participants.id`).
- `modality` (TEXT): Feature modality.
- `feature_name` (TEXT): Digital biomarker feature name.
- `baseline_mean` (NUMERIC): Robust baseline mean.
- `baseline_median` (NUMERIC): Robust baseline median.
- `baseline_std` (NUMERIC): Baseline standard deviation.
- `baseline_mad` (NUMERIC): Median Absolute Deviation.
- `lower_bound` (NUMERIC): Normal lower control bound.
- `upper_bound` (NUMERIC): Normal upper control bound.
- `sample_count` (INTEGER): Number of calibrated valid daily sessions (≥ 1).
- `baseline_start_date` (DATE): Calibration window start.
- `baseline_end_date` (DATE): Calibration window end.
- `baseline_version` (TEXT): Baseline algorithm version.
- `algorithm_version` (TEXT): Calibration engine version.
- `created_at` (TIMESTAMPTZ): Baseline creation timestamp.
- `updated_at` (TIMESTAMPTZ): Last update timestamp.
- `UNIQUE(participant_id, modality, feature_name)`: Enforces single baseline per feature.

### 3.10 `daily_deviations`
Statistical deviation scores comparing daily features to established personal baselines.
- `id` (UUID, PK): Record ID.
- `participant_id` (UUID, FK → `participants.id`).
- `date` (DATE): Calendar date.
- `modality` (TEXT): Biomarker modality.
- `feature_name` (TEXT): Feature name.
- `value` (NUMERIC): Current observed value.
- `baseline_value` (NUMERIC): Established personal baseline value.
- `deviation_score` (NUMERIC): Robust z-score deviation `(value - median) / (1.4826 * MAD)`.
- `trend_score` (NUMERIC): Multi-day longitudinal trend slope.
- `quality_score` (NUMERIC, 0.0–1.0): Data reliability gate score.
- `algorithm_version` (TEXT): Deviation computation version.
- `created_at` (TIMESTAMPTZ): Record creation timestamp.

### 3.11 `mpf_predictions`
Multimodal prodromal fusion screening risk audit log.
- `id` (UUID, PK): Record ID.
- `participant_id` (UUID, FK → `participants.id`).
- `timestamp` (TIMESTAMPTZ): Inference timestamp.
- `model_version` (TEXT): Model version used.
- `input_feature_version` (TEXT): Schema version of input features.
- `available_modalities` (TEXT[]): List of present modalities.
- `missing_modalities` (TEXT[]): List of absent modalities handled via gating/imputation.
- `risk_score` (NUMERIC, 0.0–1.0): Bounded risk probability.
- `prediction_metadata` (JSONB): Explainability attribution, SHAP summary, disclaimer.
- `created_at` (TIMESTAMPTZ): Audit log timestamp.

### 3.12 `model_versions`
Frozen checkpoint registry maintaining full provenance.
- `id` (UUID, PK): Model record ID.
- `model_name` (TEXT): Name of model (`gated_multimodal_fusion`, etc.).
- `version` (TEXT): Semantic model version (`v1.0.0`).
- `created_at` (TIMESTAMPTZ): Checkpoint registration timestamp.
- `feature_schema_version` (TEXT): Expected input schema version.
- `training_dataset_version` (TEXT): Provenance dataset version.
- `metrics` (JSONB): Validation metrics (AUROC, sensitivity, Brier score).
- `active` (BOOLEAN): Whether model is active for inference.

---

## 4. Row Level Security (RLS) Policies

All 12 tables have Row Level Security enabled (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY`).

| Policy | Target Tables | Operation | Rule Definition |
|---|---|---|---|
| **Users can view own data** | `participants` | SELECT | `USING (auth.uid() = id)` |
| **Users can insert own data** | `participants` | INSERT | `WITH CHECK (auth.uid() = id)` |
| **Users can update own data** | `participants` | UPDATE | `USING (auth.uid() = id)` |
| **Users can delete own data** | `participants` | DELETE | `USING (auth.uid() = id)` |
| **Users can view own data** | All 10 user data tables | SELECT | `USING (auth.uid() = participant_id)` |
| **Users can insert own data** | All 10 user data tables | INSERT | `WITH CHECK (auth.uid() = participant_id)` |
| **Users can update own data** | All 10 user data tables | UPDATE | `USING (auth.uid() = participant_id)` |
| **Users can delete own data** | All 10 user data tables | DELETE | `USING (auth.uid() = participant_id)` |
| **Anyone can read model versions**| `model_versions` | SELECT | `USING (auth.role() = 'authenticated')` |

Cross-participant access is strictly blocked at the PostgreSQL engine level.

---

## 5. Performance Indexes

```sql
CREATE INDEX idx_typing_participant ON typing_sessions(participant_id, timestamp);
CREATE INDEX idx_voice_participant ON voice_sessions(participant_id, timestamp);
CREATE INDEX idx_motor_participant ON motor_sessions(participant_id, timestamp);
CREATE INDEX idx_visual_participant ON visual_sessions(participant_id, timestamp);
CREATE INDEX idx_sleep_participant ON sleep_sessions(participant_id, timestamp);
CREATE INDEX idx_daily_features_participant ON daily_features(participant_id, date);
CREATE INDEX idx_baselines_participant ON personal_baselines(participant_id, modality);
CREATE INDEX idx_deviations_participant ON daily_deviations(participant_id, date);
CREATE INDEX idx_predictions_participant ON mpf_predictions(participant_id, timestamp);
```

---

## 6. Python Client Wrapper

Located at `src/mobile/supabase_client.py`:

```python
from src.mobile.supabase_client import init_supabase, get_client, test_connection

# Initialize client
client = init_supabase()

# Retrieve cached client singleton
client = get_client()

# Check connectivity
is_healthy = test_connection(client)
print(f"Supabase connection status: {is_healthy}")
```
