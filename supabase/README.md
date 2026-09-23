# MPF Mobile Extension — Supabase Backend Architecture & Specifications

**Multimodal Prodromal Fusion for Parkinson's Disease (MPF-PD)**  
*Relational Data Model, Authentication, Row-Level Security (RLS), and Storage Configuration*  
*Module Version: 1.0.0 | Phase: PHASE 2 COMPLETE*

---

## 1. System Overview & Mandate Compliance

The Supabase backend for the MPF Mobile Extension serves as the secure, privacy-preserving ingestion, longitudinal baseline, and inference log repository. It is designed to strictly adhere to the project's non-negotiable core principles:

1. **NO DIAGNOSTIC CLAIMS:** Outputs recorded in `mpf_predictions` are labeled as research screening results ("Elevated Parkinson's risk pattern detected" / "Research screening result — not a clinical diagnosis").
2. **NO SENSOR OVERCLAIMING:** The visual task data stored in `visual_sessions` is strictly designated as the **Ocular/Visual Behavior Module** (fixation stability, blink rate, saccadic latency). It is explicitly **NOT** retinal imaging.
3. **PRIVACY FIRST:** Keystroke text, raw audio, raw video frames, passwords, and sensitive background sensor streams are **never** stored. Extracted timing dynamics and acoustic/kinematic features are uploaded exclusively over TLS.
4. **NO DATA FABRICATION:** Strict schema constraints, unique idempotency keys, and range checks reject invalid or malformed data.
5. **NO AUTOMATIC RETRAINING:** The `model_versions` table maintains read-only versioned checkpoints. Model inference is completely separated from model retraining.
6. **BASELINE-CENTRIC ANALYSIS:** Features in `daily_features` are evaluated against `personal_baselines` (14-day calibration), logging deviations to `daily_deviations`.
7. **VERSIONED REPRODUCIBILITY:** Every table maintains version fields (`feature_version`, `baseline_version`, `model_version`, `app_version`).

---

## 2. Directory Layout

```
supabase/
├── migrations/
│   ├── 001_create_participants.sql      # Pseudonymized participant registry
│   ├── 002_create_consent_records.sql   # Dynamic informed consent audit log
│   ├── 003_create_typing_sessions.sql   # Keystroke timing dynamics (no text)
│   ├── 004_create_voice_sessions.sql    # Acoustic voice features (no raw audio)
│   ├── 005_create_motor_sessions.sql    # Motor, gait, tapping & tremor features
│   ├── 006_create_visual_sessions.sql   # Ocular/Visual behavior features (no video)
│   ├── 007_create_sleep_sessions.sql    # Sleep duration, quality & RBD questionnaire
│   ├── 008_create_daily_features.sql    # Standardized daily multimodal feature vectors
│   ├── 009_create_personal_baselines.sql# 14-day calibration & rolling baselines
│   ├── 010_create_daily_deviations.sql  # Normalized statistical deviations (z-scores)
│   ├── 011_create_mpf_predictions.sql   # Adapter inference risk-screening audit log
│   ├── 012_create_model_versions.sql    # Checkpointed model weights & schema versions
│   └── 013_create_rls_policies.sql      # Row Level Security & storage policies
├── seed/
│   └── seed_model_versions.sql          # Seed verified model weights & configurations
├── tests/
│   ├── auth_service.py                  # Supabase Auth, JWT & session implementation
│   ├── test_auth_flow.py                # Authentication, token rotation & deletion tests
│   ├── test_rls_policies.py             # RLS policies 1-7 & storage isolation tests
│   └── test_schema_integrity.py         # Table structures, constraints & types tests
└── README.md                            # Documentation and architecture guide
```

---

## 3. Relational Schema Reference

### 3.1 `participants`
Pseudonymized participant registry. Primary key is a UUIDv4 matching `auth.uid()`.
- `id` (`UUID PRIMARY KEY DEFAULT gen_random_uuid()`): Unique participant identifier.
- `created_at` (`TIMESTAMPTZ NOT NULL DEFAULT NOW()`): Participant enrollment timestamp.
- `consent_version` (`TEXT NOT NULL DEFAULT '1.0.0'`): Active consent protocol version.
- `consent_timestamp` (`TIMESTAMPTZ NOT NULL DEFAULT NOW()`): Consent execution timestamp.
- `app_version` (`TEXT NOT NULL DEFAULT '1.0.0'`): Mobile application release version.
- `model_version` (`TEXT NOT NULL DEFAULT '1.0.0'`): MPF model version active at enrollment.
- `baseline_status` (`baseline_status_enum NOT NULL DEFAULT 'collecting'`): `'collecting'`, `'established'`, or `'adaptive'`.
- `pseudonymous_id` (`TEXT UNIQUE NOT NULL`): Cryptographic pseudonymous study code.

### 3.2 `consent_records`
Audit trail of informed consent grants and revocations.
- `id` (`UUID PRIMARY KEY`): Record UUID.
- `participant_id` (`UUID REFERENCES participants(id) ON DELETE CASCADE`): Participant FK.
- `consent_type` (`TEXT CHECK (consent_type IN ('data_collection', 'audio_storage', 'research_export', 'deletion'))`): Consent category.
- `consent_version` (`TEXT NOT NULL`): Version string of consent form presented.
- `granted` (`BOOLEAN NOT NULL DEFAULT TRUE`): Consent grant state.
- `timestamp` (`TIMESTAMPTZ NOT NULL DEFAULT NOW()`): Grant timestamp.
- `revoked_at` (`TIMESTAMPTZ`): Optional revocation timestamp.

### 3.3 Active Modality Session Tables
All session tables enforce unique `session_id` idempotency keys generated on mobile devices to prevent duplicate uploads during offline-sync retries.

- **`typing_sessions`**: Keystroke timing dynamics (`typing_speed`, `mean_inter_key_interval`, `std_inter_key_interval`, `pause_rate`, `correction_rate`, `rhythm_variability`, `quality_score`). Keystroke text is never recorded.
- **`voice_sessions`**: On-device extracted acoustic features (`signal_quality`, `jitter`, `shimmer`, `hnr`, `pitch_mean`, `pitch_std`, `mfcc_features` [13-40 coeffs], `spectral_features`, `quality_score`). Raw audio is discarded locally.
- **`motor_sessions`**: Kinematic motor and gait metrics (`cadence`, `stride_variability`, `movement_variability`, `tapping_rate`, `tapping_interval_variability`, `tremor_frequency`, `tremor_amplitude`, `quality_score`).
- **`visual_sessions`**: Ocular/Visual Behavior Module metrics (`blink_rate`, `blink_interval_variability`, `gaze_stability`, `reaction_time`, `quality_score`). Front-camera behavioral task only; **not retinal imaging**.
- **`sleep_sessions`**: Subjective sleep metrics and prodromal REM sleep behavior disorder questionnaire items (`sleep_duration`, `sleep_quality` [1-5], `unusual_movement_self_report`, `daytime_sleepiness` [1-5], `score`).

### 3.4 Longitudinal Aggregation & Inference Tables
- **`daily_features`**: Daily standardized packaging combining typing, voice, motor, visual, and sleep feature sets with quality scores (`UNIQUE(participant_id, date)`).
- **`personal_baselines`**: Normative individual baselines computed from 14-day calibration (`modality`, `feature_name`, `baseline_mean`, `baseline_median`, `baseline_std`, `baseline_mad`, `lower_bound`, `upper_bound`, `sample_count`).
- **`daily_deviations`**: Statistical deviation and trend tracking relative to personal baseline (`deviation_score`, `trend_score`, `quality_score`).
- **`mpf_predictions`**: Audit log of MPF risk-screening model inference outputs (`risk_score` [0-1], `available_modalities`, `missing_modalities`, `prediction_metadata`).
- **`model_versions`**: Checkpointed model weights, active status, and validation metrics (`UNIQUE(model_name, version)`). Read-only for participants.

---

## 4. Authentication Architecture

Supabase Auth provides the identity layer:
1. **Registration & Passwords:** Email and password registration is backed by PBKDF2-HMAC-SHA256 with cryptographically generated 16-byte random salts. Plain-text passwords are never stored in memory or persistent storage.
2. **Pseudonymous Mapping:** At registration, a cryptographically derived pseudonymous identifier (`ps_<sha256>`) is issued.
3. **JWT Tokens:** Authenticated clients receive signed JWT access tokens containing standard claims (`sub = user_id`, `role = authenticated`, `aud = authenticated`, `exp`, `iat`). Tokens expire within 1 hour.
4. **Session Lifecycle & Refresh:** Long-lived refresh tokens (30 days) use token rotation. Each refresh generates a new access token and invalidates the previous refresh token.
5. **Password Reset:** Generates a cryptographically random, single-use reset token with a 15-minute expiration. Upon completion, all active sessions are revoked.
6. **Account Deletion (GDPR "Right to Erasure"):** Cascading deletion purges the participant record and all associated records across all 11 child tables (`ON DELETE CASCADE`), ensuring zero residual or orphaned data.

---

## 5. Row Level Security (RLS) Implementation

Row Level Security is enabled across all 12 tables. The following policies are strictly enforced:

| Policy | Scope | Target Tables | Rule / Expression |
|---|---|---|---|
| **Policy 1** | Read Own Data | `participants` & all feature tables | `SELECT USING (auth.uid() = participant_id)` (or `id` on `participants`) |
| **Policy 2** | Insert Own Data | `participants` & all feature tables | `INSERT WITH CHECK (auth.uid() = participant_id)` |
| **Policy 3** | Update Own Data | `participants` & all feature tables | `UPDATE USING/WITH CHECK (auth.uid() = participant_id)` |
| **Policy 4** | Delete Own Data | `participants` & all feature tables | `DELETE USING (auth.uid() = participant_id)` |
| **Policy 5** | Cross-Participant Isolation | All tables | Access blocked if `auth.uid() != participant_id` |
| **Policy 6** | Research Export | `mpf_predictions`, exports | Service-role key bypasses RLS; participants cannot export cross-cohort data |
| **Policy 7** | Model Versions Read-Only | `model_versions` | `SELECT USING (true)` for authenticated users; modifications restricted to service-role |

---

## 6. Storage Configuration

Supabase Storage is configured with two private buckets:

1. **`consent-documents` (Participant-Scoped):**
   - **Access:** Authenticated participants can read and write files exclusively in their own folder (`(storage.foldername(name))[1] = auth.uid()::text`).
   - **MIME Types:** `application/pdf`, `image/png`, `image/jpeg`.
   - **Max File Size:** 10 MB.
2. **`research-exports` (Service-Role Only):**
   - **Access:** Authenticated and anonymous client access is prohibited (`no public policies`). Only backend pipelines utilizing the `service_role` key can read/write research export bundles.
   - **MIME Types:** `application/json`, `application/parquet`, `text/csv`.
   - **Max File Size:** 500 MB.
3. **Raw Sensor Stream Restriction:**
   - Supabase Storage rejects raw audio files, raw camera videos, or raw continuous sensor dumps by default. Feature extraction occurs strictly on the mobile client.

---

## 7. Automated Testing & Verification

The test suite validates schema integrity, foreign keys, unique idempotency constraints, RLS policies, and authentication flows.

### Running Tests

```bash
python -m pytest supabase/tests -v
```

### Test Coverage Summary

- `test_schema_integrity.py`:
  - Presence and syntax of all 13 migration files.
  - Presence of seed file `seed_model_versions.sql`.
  - Table existence and column completeness for all 12 tables.
  - Foreign key constraints and cascading deletions (`ON DELETE CASCADE`).
  - Unique idempotency key enforcement on `session_id`.
  - Daily features unique constraint on `(participant_id, date)`.
  - JSON/JSONB feature vector serialization and parsing.
  - Value boundary checks on `quality_score`, `risk_score`, and `sleep_quality`.
- `test_rls_policies.py`:
  - Participant self-access (read, insert, update, delete own data).
  - Cross-participant access prevention (zero leakage between Participant A and B).
  - Unauthenticated access rejection across all tables.
  - Model versions read-only enforcement for authenticated participants.
  - Service-role privileges for research export and model updates.
  - Storage bucket folder scoping for consent documents.
- `test_auth_flow.py`:
  - Password hashing security (PBKDF2-HMAC-SHA256, no plain text).
  - Pseudonymous ID generation.
  - JWT token issuance, signature verification, expiry, and tampering detection.
  - Refresh token rotation and session invalidation on logout.
  - One-time password reset token life-cycle and revocation.
  - GDPR cascading account deletion verifying zero orphaned records.
