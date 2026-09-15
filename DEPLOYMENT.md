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

### 5.4 `POST /explain`
Computes exact TreeSHAP values and modality-level percentage attributions for the input record.

---

## 6. Productionization Limitations & Regulatory Notice

> [!CAUTION]
> ### MANDATORY WARNING BEFORE ANY PRODUCTION CONSIDERATION
> This deployment setup is strictly an **engineering prototype**. Translating this codebase toward any real-world healthcare environment requires the following unfulfilled milestones:
> 1. **Regulatory Clearance:** Formal SaMD (Software as a Medical Device) approval (FDA 510(k) / De Novo or CE mark under MDR 2017/745).
> 2. **Clinical Prospective Trials:** Blinded multi-center clinical validation demonstrating positive predictive value in real prodromal cohorts.
> 3. **EHR & Interoperability:** HL7 FHIR API integration for hospital electronic medical records.
> 4. **Cybersecurity & Compliance:** End-to-end TLS 1.3 encryption, HIPAA-compliant Business Associate Agreements, SOC 2 Type II certification, and immutable clinical audit logs.
> 5. **Human-in-the-Loop Safeguards:** Mandatory workflow locking requiring clinician sign-off before risk summaries are visible to medical staff.
