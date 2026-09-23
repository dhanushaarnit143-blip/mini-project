# MPF Mobile Extension — 16-Phase Implementation Plan & Roadmap

**Multimodal Prodromal Fusion for Parkinson's Disease (MPF-PD)**  
*Engineering Roadmap, Dependency Graphs, Risk Assessment, and Approval Gates*  
*Document Version: 1.0.0 | Status: APPROVED ENGINEERING PLAN*

---

> [!IMPORTANT]
> ### PHASED EXECUTION & APPROVAL GATE RULES
> 1. **STRICT PHASE GATING:** No phase may begin until the preceding dependent phase has passed its automated acceptance criteria, completed its phase report, and received explicit stakeholder approval.
> 2. **NO SHORTCUTS OR CODE MERGES AHEAD OF GATES:** Application code is written strictly within its designated phase.
> 3. **CONTINUOUS TESTING:** Every phase includes automated unit and integration tests using synthetic test fixtures. Zero fabricated clinical data is allowed.

---

## 1. Master 16-Phase Roadmap & Milestones

```mermaid
gantt
    title MPF Mobile Extension — 16-Phase Implementation Roadmap
    dateFormat  YYYY-MM-DD
    section Foundation
    Phase 1: Architecture & Setup          :done,    p1, 2026-09-24, 2d
    Phase 2: Supabase & Security DDL        :active,  p2, after p1, 3d
    Phase 3: Mobile Core & Consent          :         p3, after p2, 4d
    section Digital Biomarker Modules
    Phase 4: Typing Dynamics Module         :         p4, after p3, 4d
    Phase 5: Voice Acoustic Module          :         p5, after p3, 5d
    Phase 6: Motor & Gait Module            :         p6, after p3, 5d
    Phase 7: Ocular/Visual Behavior Module  :         p7, after p3, 6d
    Phase 8: Sleep & RBDSQ Module           :         p8, after p3, 3d
    section Aggregation & Baselines
    Phase 9: Daily Packaging & QC           :         p9, after p4 p5 p6 p7 p8, 4d
    Phase 10: 14-Day Baseline Engine        :         p10, after p9, 5d
    Phase 11: Longitudinal Deviation Engine :         p11, after p10, 4d
    section Cloud & Adapter Integration
    Phase 12: Supabase Sync & Offline Queue :         p12, after p9 p11, 4d
    Phase 13: MPF Adapter Service (Mapping) :         p13, after p12, 5d
    Phase 14: End-to-End Pipeline Inference :         p14, after p13, 4d
    section User Experience & Delivery
    Phase 15: Mobile Research Dashboard     :         p15, after p14, 5d
    Phase 16: System Verification & Release :         p16, after p15, 5d
```

---

## 2. Detailed Phase Specifications

### Phase 1: Architecture Analysis & Project Setup *(Current Phase)*
- **Objective:** Deep inspection of existing MPF models, feature schemas, missing-modality mechanisms, and delivery of core design documents.
- **Deliverables:** `ARCHITECTURE.md`, `MOBILE_DATA_SCHEMA.md`, `SUPABASE_SCHEMA.md`, `MPF_ADAPTER_SPEC.md`, `PRIVACY_MODEL.md`, `IMPLEMENTATION_PLAN.md`.
- **Status:** **COMPLETE**.
- **Gate 1 Approval:** Stakeholder review of design documents before any coding begins.

---

### Phase 2: Supabase Infrastructure & Security Setup
- **Objective:** Deploy PostgreSQL schema, table definitions, constraints, indexes, and Row Level Security (RLS) policies on Supabase.
- **Key Tasks:**
  - Create Supabase project and configure PostgreSQL 15+.
  - Apply `001_initial_schema.sql` (12 tables, indexes, triggers).
  - Test RLS policies with simulated user JWTs to verify zero cross-participant leakage.
  - Implement automated daily WAL backups and point-in-time recovery testing.
- **Effort Estimate:** 3 Days.
- **Testing:** Automated SQL migration tests, RLS negative permission unit tests.
- **Gate 2 Approval:** Verified zero data access across distinct participant UUIDs.

---

### Phase 3: Mobile Client Core & Consent Framework
- **Objective:** Initialize Flutter cross-platform mobile project with clean architecture, encrypted local database, and granular consent engine.
- **Key Tasks:**
  - Initialize Flutter project structure (`lib/core`, `lib/features`).
  - Configure `sqflite_sqlcipher` with hardware keystore-derived AES-256 keys.
  - Build interactive, multi-tiered consent onboarding flow (Rule 1 & Rule 3 compliance).
  - Implement offline participant session token handling.
- **Effort Estimate:** 4 Days.
- **Testing:** Widget tests for consent toggles, database encryption verification tests.
- **Gate 3 Approval:** Legal/ethical review of plain-language consent screens.

---

### Phase 4: Typing Dynamics Module (Privacy-Preserving Keystroke Timing)
- **Objective:** Implement keyboard timing event interceptor measuring hold and flight latencies without recording characters.
- **Key Tasks:**
  - Build custom text input listener capturing `down_time_ms` and `up_time_ms`.
  - Enforce zero-character logging (verify character codes are never stored in memory or disk).
  - Implement statistical extraction: `hold_time_mean`, `flight_time_mean`, `iki_cv_pct`, `typing_entropy`.
  - Local QC check: filter out automated inputs and sessions with $< 50$ keystrokes.
- **Effort Estimate:** 4 Days.
- **Testing:** Unit tests verifying timing calculation accuracy; privacy audit confirming zero string leaks.
- **Gate 4 Approval:** Security audit confirming impossible text reconstruction from timing data.

---

### Phase 5: Voice Biomarker Module (On-Device Acoustic DSP)
- **Objective:** Guided 5-second `/a/` phonation recorder with real-time audio QC and edge spectral DSP.
- **Key Tasks:**
  - Integrate native audio recorder with 44.1 kHz 16-bit PCM uncompressed sampling.
  - Edge DSP implementation: Pitch period detection, local jitter calculation, shimmer quotients, HNR, NHR.
  - Audio QC gate: Reject audio if SNR $< 15\text{ dB}$ or duration $< 3\text{ s}$.
  - Memory security: Immediate purging of raw audio buffer post-extraction.
- **Effort Estimate:** 5 Days.
- **Testing:** Compare mobile DSP outputs against Praat reference values on synthetic audio wav fixtures.
- **Gate 5 Approval:** Acoustic feature concordance with desktop DSP library ($r > 0.98$).

---

### Phase 6: Motor & Gait Biomarker Module (Sensor Dynamics)
- **Objective:** Guided linear walk (20s), postural tremor (10s), and alternating finger tapping tests.
- **Key Tasks:**
  - High-frequency (100 Hz) accelerometer and gyroscope sampling.
  - Gait step detection, cadence autocorrelation, stride interval mean and CV calculation.
  - Tremor spectral analysis: 3.5–7.0 Hz Parkinsonian band power ratio calculation.
  - Capacitive two-target finger tapping timing analysis.
- **Effort Estimate:** 5 Days.
- **Testing:** Benchmark gait cadence and step counting against calibrated synthetic IMU traces.
- **Gate 6 Approval:** Kinematic extraction accuracy validated on calibrated motion data.

---

### Phase 7: Ocular / Visual Behavior Module (Gaze & Saccade Tracking)
- **Objective:** Front-camera gaze fixation (3s) and pro-saccadic tracking tasks.
- **Key Tasks:**
  - Front camera frame streaming at 30 fps using Google ML Kit Face Mesh.
  - Extract gaze fixation dispersion (BCEA) and horizontal saccade latency and peak velocity.
  - Strict labeling enforcement: Formally designated as Ocular/Visual Behavior (Rule 2).
  - Ephemeral memory handling: Zero video frames written to persistent flash storage.
- **Effort Estimate:** 6 Days.
- **Testing:** Simulated head/eye movement video fixtures verifying saccade latency detection.
- **Gate 7 Approval:** Verification that all UI, logs, and metadata refer to Visual Behavior, NOT retinal imaging.

---

### Phase 8: Sleep & Questionnaire Module (RBDSQ & Micro-Surveys)
- **Objective:** Standardized digital administration of the 13-item RBDSQ and daily morning sleep check-in.
- **Key Tasks:**
  - Build accessible, high-contrast digital RBDSQ questionnaire with clear radio inputs.
  - Calculate `rbdsq_total`, `above_cutoff_flag` ($\ge 5$), and `high_weight_item_flags`.
  - Daily micro-survey for sleep duration and nocturnal awakenings.
- **Effort Estimate:** 3 Days.
- **Testing:** Automated scoring logic verification against known RBDSQ score profiles.
- **Gate 8 Approval:** Clinical questionnaire logic validation.

---

### Phase 9: Daily Aggregation & Feature Vector Packaging
- **Objective:** Assemble multi-stream digital biomarkers into standardized Daily Feature Vector JSON.
- **Key Tasks:**
  - Aggregate modalities collected throughout the calendar day into single daily record.
  - Compute composite daily quality index.
  - Validate output against JSON schema specification (`MOBILE_DATA_SCHEMA.md`).
- **Effort Estimate:** 4 Days.
- **Testing:** JSON schema validation tests, edge-case tests with partial modality availability.
- **Gate 9 Approval:** Schema-compliance validation across 100 synthetic daily records.

---

### Phase 10: Personal Baseline Engine (14-Day Baseline & Rolling Statistics)
- **Objective:** Establish 14-day calibration profile and adaptive rolling baseline per participant.
- **Key Tasks:**
  - Track participant calibration progress (Days 1–14).
  - Calculate personal parametric ($\mu, \sigma$) and non-parametric (median, IQR) baseline stats.
  - Calculate feature covariance matrix $\mathbf{\Sigma}_{\text{base}}$ for multivariate distance.
  - Store baseline profiles in `personal_baselines` table.
- **Effort Estimate:** 5 Days.
- **Testing:** Unit tests verifying convergence on 14-day simulated data and resilience to outlier days.
- **Gate 10 Approval:** Verification of baseline-centric logic (no immediate population comparison).

---

### Phase 11: Longitudinal Trend & Deviation Engine
- **Objective:** Compute univariate Z-scores and multivariate Mahalanobis distance from personal baseline.
- **Key Tasks:**
  - Daily evaluation: $z_{i, t} = (x_{i, t} - \mu_{i, \text{base}}) / \sigma_{i, \text{base}}$.
  - Mahalanobis distance calculation with regularization for near-singular covariance matrices.
  - Longitudinal deviation persistence detector ($|z| \ge 2.5$ for $\ge 3$ consecutive days).
  - Standardized non-diagnostic text generator (Rule 1 compliance).
- **Effort Estimate:** 4 Days.
- **Testing:** Statistical validation of deviation sensitivity using synthetic baseline drift fixtures.
- **Gate 11 Approval:** Audit of generated summary text confirming zero diagnostic claims.

---

### Phase 12: Supabase Sync & Offline Resiliency Layer
- **Objective:** Robust, bi-directional synchronization with offline queue and retry mechanisms.
- **Key Tasks:**
  - Background synchronization service utilizing WorkManager (Android) and BackgroundTasks (iOS).
  - SQLite transaction queue with exponential backoff on network failure.
  - Realtime subscription for server-generated baseline and prediction updates.
- **Effort Estimate:** 4 Days.
- **Testing:** Network throttling, offline disconnection, and duplicate packet deduplication tests.
- **Gate 12 Approval:** Zero data loss during 48-hour simulated offline mobile operation.

---

### Phase 13: MPF Adapter Service (Feature Mapping & Normalization)
- **Objective:** Build `src/mobile/mpf_adapter.py` mapping mobile features to existing MPF model schema.
- **Key Tasks:**
  - Load `models/fusion/preprocessor.joblib` and apply scalers/imputers without refitting.
  - Map mobile features to MPF inputs (Voice 16-D, Motor 8-D, RBD 16-D).
  - Route olfactory and retinal modalities as `available=False` to trigger learnable missing tokens.
  - Validate output payload conforms strictly to `run_mpf_pipeline()` contract.
- **Effort Estimate:** 5 Days.
- **Testing:** Unit tests ensuring numerical outputs match expected scaled tensors.
- **Gate 13 Approval:** Exact match between adapter normalized features and training preprocessor.

---

### Phase 14: End-to-End MPF Pipeline Integration & Inference Verification
- **Objective:** Execute live inference through existing MPF core models from mobile adapter.
- **Key Tasks:**
  - Connect adapter to `src.pipeline.run_mpf_pipeline()`.
  - Verify neural gated attention weights ($\alpha_{\text{voice}}, \alpha_{\text{motor}}, \alpha_{\text{rbd}}$ sum to 1.0; $\alpha_{\text{olf}} = 0, \alpha_{\text{ret}} = 0$).
  - Verify XGBoost prediction generation and TreeSHAP feature attributions.
  - Store predictions in `mpf_predictions` table.
- **Effort Estimate:** 4 Days.
- **Testing:** Integration tests comparing adapter inference results against standard MPF CLI outputs.
- **Gate 14 Approval:** Complete pipeline execution with zero modification to core MPF files.

---

### Phase 15: Mobile Research Dashboard & Visualization UI
- **Objective:** Build patient-facing mobile dashboard displaying personal baseline trajectories and trends.
- **Key Tasks:**
  - Longitudinal trend charts showing daily measurements vs personal baseline envelope ($\mu \pm 2\sigma$).
  - Modality completion status cards and task reminders.
  - Non-diagnostic research feedback (Rule 1 compliance):
    - *"Elevated Parkinson's risk pattern detected"*
    - *"Your recent measurements differ from your personal baseline"*
  - Educational disclaimers and export functionality.
- **Effort Estimate:** 5 Days.
- **Testing:** UI responsiveness, accessibility (WCAG AA), screen reader testing.
- **Gate 15 Approval:** Clinical UI/UX review of trend visualizations and disclaimer prominence.

---

### Phase 16: Verification, End-to-End System Testing & Longitudinal Validation
- **Objective:** Comprehensive end-to-end system testing, performance benchmarking, and production readiness.
- **Key Tasks:**
  - 30-day simulated cohort test (50 synthetic participants) running end-to-end through full stack.
  - Latency profiling: ensure daily processing takes $< 500\text{ ms}$ per participant on server.
  - Security audit: penetration testing, RLS boundary verification, secret rotation drill.
  - Prepare final documentation and deployment packaging.
- **Effort Estimate:** 5 Days.
- **Testing:** End-to-end integration test suite, stress testing, chaos engineering disconnections.
- **Gate 16 Approval:** Formal sign-off and deployment authorization.

---

## 3. Risk Assessment & Mitigation Matrix

| Identified Risk | Severity | Probability | Mitigation Strategy |
| :--- | :---: | :---: | :--- |
| **Microphone hardware heterogeneity distorting voice features** | High | High | Enforce strict acoustic QC (SNR $> 15\text{ dB}$) and normalize acoustic metrics against personal 14-day baseline rather than absolute population thresholds. |
| **Participant drops off during 14-day calibration** | Medium | High | Implement adaptive baseline fallback: require minimum 7 valid days out of 14; trigger gentle in-app task reminders. |
| **Accidental character capture in typing dynamics** | Critical | Low | Hardcode keycode filtering at native OS bridge; emit solely timestamp deltas ($\Delta t$); verify via automated continuous privacy regression tests. |
| **Missing modality bias in fusion model** | Medium | Medium | MPF Gated Multimodal Fusion model was explicitly trained with learnable missing tokens and dynamic attention masking; verified zero crash on missing modalities. |
| **Misinterpretation of research screening as clinical diagnosis** | Critical | Medium | Prominent, persistent non-diagnostic banners; mandatory acknowledgment modal; clinical consultation advisory. |
| **High mobile battery drain during sensor tasks** | Medium | Low | Sensor collection active strictly during guided tasks (max 3 minutes total daily active time); zero continuous background GPS or sensor polling. |

---

## 4. Integration Checkpoints & Approval Protocol

| Gate | Milestone | Required Artifacts | Sign-off Role |
| :---: | :--- | :--- | :--- |
| **Gate 1** | Architecture Approval | 6 Design Documents (`ARCHITECTURE.md`, etc.) | Lead AI Engineer & System Architect |
| **Gate 2** | DB & Security Verification | Supabase DDL, RLS Test Suite Report | Security Lead & Backend Engineer |
| **Gate 3** | Consent & Privacy Sign-off | Consent Flow Walkthrough, Privacy Audit | Clinical Ethics Lead |
| **Gate 4** | Sensor Module Readiness | DSP Accuracy Benchmarks, QC Test Reports | Mobile AI Engineer |
| **Gate 5** | Baseline & Deviation Audit | Longitudinal Statistical Validation Suite | Research Biostatistician |
| **Gate 6** | MPF Integration Verification | Zero-Regression MPF Pipeline Test Suite | MPF Core Maintainer |
| **Gate 7** | Final Release Authorization | 30-Day Simulated Trial Report, Security Audit | Project Principal Investigator (PI) |
