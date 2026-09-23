# MPF-PD Deployment & Execution Guide

**Multimodal Prodromal Fusion for Parkinson’s Disease Risk Screening**  
*Investigational Research Prototype — Local Setup, API Deployment, & Self-Testing*

---

> [!IMPORTANT]
> ### RESEARCH DEMONSTRATION NOTICE
> **Deployment is strictly for local research demonstration, academic peer review, and software validation.**  
> This system is **NOT** authorized or architected for clinical deployment, healthcare provider triage, or patient-facing diagnostic services.

---

## 1. System Requirements & Environment Setup

### 1.1 Prerequisites
- **Operating System:** Windows 10/11, macOS 12+, or Ubuntu 20.04+ LTS
- **Python Runtime:** Python 3.10 or Python 3.11 (Python 3.12+ may have compatibility issues with select C-extensions)
- **Node.js Runtime:** Node.js v18.0+ and npm v9.0+ (required for React frontend)
- **Hardware Minimum:** 8 GB RAM, 4-core CPU, 2 GB available disk space
- **Optional Hardware:** NVIDIA GPU with CUDA 11.8+ (CPU inference is fully supported and deterministic)

### 1.2 Python Environment Installation
```bash
# Clone the repository
git clone https://github.com/dhanushaarnit143-blip/mini-project.git
cd "mini-project"

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Upgrade pip and install core dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 2. Model Artifacts & Dataset Setup

### 2.1 Model Artifact Verification
The repository ships with pretrained checkpoints and encoders located in the `models/` directory. Verify that all required checkpoints exist:
```bash
python scripts/healthcheck.py
```
Expected output:
- `models/fusion/classifier.joblib` (Present)
- `models/fusion/fusion_encoder.pt` (Present)
- `models/fusion/preprocessor.joblib` (Present)
- `models/fusion/metadata.json` (Present)
- `models/olfactory/model.joblib` (Present)
- `models/rbd/model.joblib` (Present)
- `models/voice/model.joblib` (Present)
- `models/motor/model.joblib` (Present)

### 2.2 Dataset Setup & Simulation Mode
- By default, the system operates in **`prototype_simulation`** mode using the synthetic multimodal fixture (`Category E`). No external downloads are required for local testing.
- If authentic clinical datasets (e.g. PPMI, PhysioNet Gait, UCI Voice) are approved under formal institutional DUAs, raw files should be placed under `data/raw/<dataset_id>/` following the directory structure in `docs/DATASETS.md`.

---

## 3. Pipeline Automated Self-Test & Quality Assurance

Run the automated test suite to ensure all 238+ assertions pass:

```bash
# Execute Pytest suite
pytest -v

# Run comprehensive Phase 10 research validation suite
python scripts/run_phase10_validation.py
```

Expected output:
- Zero test failures across data loaders, encoders, attention gating, and SHAP explainability.
- Verification of zero participant-level leakage logged to `evaluation/leakage_report.json`.

---

## 4. Launching the Interactive Web Dashboard

The MPF-PD dashboard consists of a **FastAPI backend REST service** and a **React + Tailwind CSS frontend application**.

### 4.1 Step 1: Start FastAPI Backend Service
Open a terminal, activate your virtual environment, and execute:
```bash
# From the repository root
python -m uvicorn dashboard.api.main:app --host 0.0.0.0 --port 8000 --reload
```
- API Documentation (Swagger UI): `http://localhost:8000/docs`
- Healthcheck Endpoint: `http://localhost:8000/health`

### 4.2 Step 2: Start React Frontend Application
Open a second terminal:
```bash
# Navigate to frontend directory
cd dashboard/frontend

# Install Node.js dependencies (first time only)
npm install

# Start Vite development server
npm run dev
```
- Open your browser at: `http://localhost:5173`
- The dashboard will load with pre-configured synthetic participant fixtures, risk gauge visualizations, dynamic modality toggles, and interactive SHAP waterfall plots.

---

## 5. API Endpoint Reference

The FastAPI service exposes four primary REST endpoints:

### 5.1 `GET /health`
Returns system status, active model versions, and artifact availability.
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "experiment_mode": "prototype_simulation",
  "models_loaded": {
    "fusion": true,
    "olfactory": true,
    "rbd": true,
    "voice": true,
    "motor": true
  }
}
```

### 5.2 `GET /samples`
Provides pre-formatted synthetic participant fixtures (`SYNTH-PD-001`, `SYNTH-CTRL-001`, etc.) for rapid testing.

### 5.3 `POST /predict`
Executes end-to-end multimodal inference.
- **Request Body:** JSON containing participant demographics and available modality feature dictionaries.
- **Response:**
```json
{
  "participant_id": "SYNTH-PD-001",
  "research_risk_estimate": 0.9903,
  "risk_category": "elevated_risk_pattern",
  "uncertainty_score": 0.20,
  "active_modalities": ["olfactory", "rbd", "voice", "motor"],
  "missing_modalities": ["retina"],
  "gate_weights": {
    "olfactory": 0.251,
    "rbd": 0.248,
    "voice": 0.252,
    "motor": 0.256,
    "retina": 0.000
  },
  "warnings": [
    "Retinal imaging was omitted; estimate reflects partial observation."
  ],
  "disclaimer": "This is a research prototype risk estimate. It does not diagnose Parkinson's disease."
}
```

### 5.4 `POST /api/mobile/analyze`
Executes end-to-end multimodal inference on mobile longitudinal digital biomarkers via the MPF Adapter layer.
- **Request Body (`MobileAnalysisRequest`):**
```json
{
  "participant_id": "P001",
  "features": {
    "typing": {"typing_speed": 4.2, "interval_variability": 0.12, "correction_rate": 0.05},
    "voice": {"jitter": 0.008, "shimmer": 0.04, "hnr": 18.5, "pitch_mean": 145.0},
    "motor": {"cadence": 105.0, "stride_variability": 2.5, "tapping_rate": 5.1},
    "sleep": {"rbdsq_total": 3.0, "unusual_movement_self_report": 0.0}
  },
  "baseline_deviation_context": {
    "baseline_version": "1.0.0",
    "mahalanobis_distance": 1.25,
    "status": "within_baseline"
  },
  "demographics": {"age": 65.0, "sex": "male"},
  "log_to_db": true,
  "raw_feature_version": "1.0.0",
  "app_version": "1.0.0"
}
```
- **Response (`MobileAnalysisResponse`):**
```json
{
  "risk_score": 0.3421,
  "status": "success",
  "risk_pattern": "Standard risk pattern observed",
  "available_modalities": ["voice", "motor", "rbd"],
  "missing_modalities": ["olfactory", "retina"],
  "model_version": "gated_multimodal_fusion_v1",
  "prediction_metadata": {
    "source": "mobile_extension",
    "feature_mapping_version": "1.0.0",
    "feature_version": "1.0.0",
    "raw_feature_version": "1.0.0",
    "processing_version": "1.0.0",
    "baseline_version": "1.0.0",
    "model_version": "gated_multimodal_fusion_v1",
    "app_version": "1.0.0",
    "disclaimer": "Research screening result — not a clinical diagnosis."
  },
  "gate_weights": {"voice": 0.34, "motor": 0.33, "rbd": 0.33},
  "explanation": {...}
}
```

---

## 6. Mobile Extension Deployment & Integration Guide

The MPF Mobile Extension coordinates three decoupled operational layers:
```
Mobile App (Flutter / React)  <-->  Supabase Cloud (PostgreSQL 15+ & Auth)  <-->  Backend API (FastAPI) + Frozen MPF Core
```

### 6.1 Environment Configuration
Create or configure the `.env` file in the repository root:
```ini
# Supabase Configuration
SUPABASE_URL=https://trtvdmgswouirfaqyrdk.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Backend API Service
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# MPF Adapter
PREPROCESSOR_PATH=models/fusion/preprocessor.joblib
PREDICTION_AUDIT_LOG=logs/mobile_predictions.jsonl
```

### 6.2 Step 1: Database Migration & Verification
Ensure all 16 tables and RLS policies are applied to Supabase:
```bash
# Verify live Supabase database and schema integrity
pytest supabase/tests/test_schema_integrity.py -v
pytest tests/test_supabase_integration.py -v
```

### 6.3 Step 2: Start MPF Backend Service
Launch the central FastAPI service with the mobile ingestion endpoint:
```bash
python -m uvicorn dashboard.api.main:app --host 0.0.0.0 --port 8000 --reload
```
Test health status:
```bash
curl -X GET http://localhost:8000/api/health
```

### 6.4 Step 3: Run Full Pipeline Integration Validation
Execute the complete Phase 16 end-to-end integration and backward compatibility test suite:
```bash
# 14-day baseline simulation, progressive deviation, adapter inference, and backward compatibility
pytest tests/integration/test_phase16_e2e_integration.py -v
```

### 6.5 Operational Deployment Checklist
- [x] Pre-trained models verified present in `models/` (classifier, encoder, preprocessor)
- [x] Supabase cloud connection established with RLS policies enabled
- [x] Zero raw sensor retention on-device (audio, video, keystroke text destroyed immediately after DSP)
- [x] Adapter maps mobile digital biomarkers without modifying existing MPF weights
- [x] 14-day calibration window enforced before computing longitudinal deviation alerts
- [x] 5-tuple version coordinates recorded for every prediction (`raw_feature`, `processing`, `baseline`, `model`, `app`)
- [x] Non-diagnostic disclaimers present across all API responses and UI screens

---

## 7. Productionization Limitations & Regulatory Notice

> [!CAUTION]
> ### MANDATORY WARNING BEFORE ANY PRODUCTION CONSIDERATION
> This deployment setup is strictly an **engineering prototype**. Translating this codebase toward any real-world healthcare environment requires the following unfulfilled milestones:
> 1. **Regulatory Clearance:** Formal SaMD (Software as a Medical Device) approval (FDA 510(k) / De Novo or CE mark under MDR 2017/745).
> 2. **Clinical Prospective Trials:** Blinded multi-center clinical validation demonstrating positive predictive value in real prodromal cohorts.
> 3. **EHR & Interoperability:** HL7 FHIR API integration for hospital electronic medical records.
> 4. **Cybersecurity & Compliance:** End-to-end TLS 1.3 encryption, HIPAA-compliant Business Associate Agreements, SOC 2 Type II certification, and immutable clinical audit logs.
> 5. **Human-in-the-Loop Safeguards:** Mandatory workflow locking requiring clinician sign-off before risk summaries are visible to medical staff.
