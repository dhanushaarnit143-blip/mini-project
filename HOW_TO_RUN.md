# MPF-PD Execution Guide: How to Run the Project

**Project Title:** Multimodal Prodromal Fusion for Parkinson's Disease Risk Screening (MPF-PD)  
**Document Purpose:** End-to-end technical execution guide covering prerequisites, environment setup, model training, API deployment, React dashboard execution, mobile extension integration, testing, and troubleshooting.  
**System Status:** Research Prototype (Phases 0–11 Complete)  
**Clinical Notice:** Investigational research prototype only. Not for medical diagnosis or clinical decision-making.

---

## Table of Contents
1. [Prerequisites](#1-prerequisites)
2. [Repository Structure](#2-repository-structure)
3. [Environment Setup](#3-environment-setup)
4. [Dataset Preparation](#4-dataset-preparation)
5. [Training the Models](#5-training-the-models)
6. [Running the Backend API (FastAPI)](#6-running-the-backend-api-fastapi)
7. [Running the React Dashboard](#7-running-the-react-dashboard)
8. [Running the Mobile Extension & Supabase Backend](#8-running-the-mobile-extension--supabase-backend)
9. [Running Tests & Validation](#9-running-tests--validation)
10. [Common Issues and Solutions](#10-common-issues-and-solutions)

---

## 1. Prerequisites

### 1.1 Hardware and OS Requirements
- **Operating System:** Windows 10/11, Ubuntu 20.04/22.04 LTS, or macOS (Apple Silicon or Intel).
- **CPU:** Quad-core x86_64 or ARM64 processor (Intel i5/i7/i9, AMD Ryzen, or Apple M-series).
- **RAM:** Minimum 8 GB (16 GB recommended for retinal CNN feature extraction and multimodal training).
- **Disk Space:** 5 GB free disk space for virtual environments, model weights, and synthetic fixtures.
- **GPU (Optional):** NVIDIA GPU with CUDA 11.8+ / 12.1+ supported for PyTorch retinal training. A GPU is **not mandatory**; all pipelines, encoders, and inference routines include CPU fallback.

### 1.2 Software Dependencies
- **Python:** Version `3.10.x` or `3.11.x` (Python 3.10 recommended; avoid Python 3.12+ due to specific PyTorch and audio C-extension wheels).
- **Node.js:** Version `18.x LTS` or `20.x LTS` with `npm` version 9+.
- **Git:** Version 2.30+.

### 1.3 External Accounts & API Services
- **Supabase Account (Free Tier):** Required for the mobile extension, user consent storage, and longitudinal feature logging.
  - Project URL: `https://<your-project-id>.supabase.co`
  - Anon Key: Public client key (`SUPABASE_ANON_KEY`)
  - Service Role Key: Backend administrative key (`SUPABASE_SERVICE_ROLE_KEY`)
- **PPMI Data Access (Optional / Prospective):**
  - Data Use Agreement (DUA) through the [Parkinson's Progression Markers Initiative](https://www.ppmi-info.org/access-data-specimens/download-data).
  - *Note:* Real PPMI data is restricted. When not downloaded locally, MPF-PD automatically falls back to deterministic synthetic clinical fixtures (`Category E`) for prototype demonstration.

---

## 2. Repository Structure

```
mini project/
├── .env.example                     # Template environment variable configuration
├── config.yaml                      # Global pipeline parameters and hyperparameter config
├── pytest.ini                       # Test suite discovery configuration
├── requirements.txt                 # Core Python package dependencies
│
├── data/                            # Dataset root (gitignored for large binaries)
│   ├── raw/                         # Raw clinical & sensor data (PPMI, UCI, DRIVE)
│   ├── interim/                     # Segmented vessels, normalized audio, filtered gait
│   ├── processed/                   # Split train/val/test feature matrices
│   ├── external/                    # Pretrained weights and norm tables
│   ├── metadata/                    # Dataset provenance and catalog manifests
│   └── reports/                     # Data quality and audit reports
│
├── models/                          # Serialized model artifacts
│   ├── olfactory/                   # Olfactory scaler, imputer, model.joblib, metadata
│   ├── rbd/                         # RBDSQ model.joblib, threshold metadata
│   ├── voice/                       # Dysphonia scaler, model.joblib, feature schema
│   ├── motor/                       # Gait/tapping imputer, model.joblib
│   ├── retina/                      # U-Net weights, ResNet encoder, feature schemas
│   └── fusion/                      # Gated fusion encoder (PyTorch), XGBoost classifier
│
├── src/                             # Core Python algorithmic source code
│   ├── config.py                    # YAML configuration parser
│   ├── seeds.py                     # Deterministic random seed controller (seed=42)
│   ├── pipeline.py                  # End-to-end multimodal inference pipeline
│   ├── model_registry.py            # Artifact loader with checksum verification
│   ├── olfactory/                   # Modality 1: UPSIT preprocessing, features, train
│   ├── rbd/                         # Modality 2: RBDSQ scoring, screening, train
│   ├── voice/                       # Modality 3: Praat/librosa acoustic extraction, train
│   ├── motor/                       # Modality 4: VGRF/IMU cadence, regularity, train
│   ├── retina/                      # Modality 5: Vessel segmentation, CNN embedding, train
│   ├── fusion/                      # Gated neural fusion encoder, attention gates, train
│   ├── explainability/              # SHAP TreeExplainer, local/global feature attribution
│   └── mobile/                      # Mobile extension: adapter, daily mapper, privacy
│       ├── mpf_adapter.py           # Adapts daily mobile features to frozen MPF input
│       ├── feature_mapper.py        # Mapping specifications and Z-score transforms
│       ├── prediction_logger.py     # Secure database logger for mobile estimates
│       ├── onboarding/              # Consent forms, research ethics, permissions
│       ├── typing/                  # Keystroke dynamics and hold-time extractors
│       ├── visual/                  # Visual reaction time and saccade proxies
│       └── sleep/                   # Sleep regularity and nocturnal movement proxies
│
├── dashboard/                       # Research Dashboard interfaces
│   ├── app.py                       # Streamlit standalone research prototype
│   ├── api/                         # FastAPI backend REST service
│   │   ├── main.py                  # API routes (/api/health, /api/analyze, etc.)
│   │   ├── schemas.py               # Pydantic request/response data contracts
│   │   └── supabase_client.py       # Async Supabase database bridge
│   └── frontend/                    # Modern React 18 + Tailwind CSS + Vite application
│       ├── index.html               # Frontend root HTML
│       ├── package.json             # NPM dependencies (Recharts, Lucide, Tailwind)
│       ├── vite.config.ts           # Vite development server configuration
│       └── src/                     # React UI components, risk gauges, SHAP charts
│
├── supabase/                        # Database schema & migrations
│   ├── migrations/                  # Versioned SQL migrations (001-006)
│   └── seed/                        # Model version seed scripts
│
├── evaluation/                      # Verification reports, benchmarks, and JSON outputs
│   ├── FINAL_EVALUATION.md          # Comprehensive phase 10 evaluation report
│   ├── XAI_REPORT.md                # Interpretability and SHAP analysis findings
│   └── *.json                       # Machine-readable evaluation metrics
│
├── scripts/                         # Automation & validation scripts
│   ├── run_phase10_validation.py    # Master end-to-end testing and validation suite
│   └── generate_dataset_reports.py  # Dataset audit and distribution reports
│
└── tests/                           # Complete Pytest test suite (238+ test assertions)
    ├── test_pipeline.py             # Multimodal integration and fallback tests
    ├── test_fusion.py               # Gated network and missingness tests
    ├── test_olfactory.py            # UPSIT pipeline unit tests
    ├── test_rbd.py                  # RBDSQ pipeline unit tests
    ├── test_voice.py                # Acoustic extraction tests
    ├── test_motor.py                # Gait and tapping tests
    ├── test_retina.py               # Retinal vessel and encoder tests
    └── test_xai.py                  # SHAP calculation verification tests
```

### Component Entry Points
| Component | Entry File | Execution Method |
| :--- | :--- | :--- |
| **FastAPI Backend** | `dashboard/api/main.py` | `uvicorn dashboard.api.main:app --port 8000 --reload` |
| **React Dashboard** | `dashboard/frontend/src/main.tsx` | `cd dashboard/frontend && npm run dev` |
| **Streamlit Interface** | `dashboard/app.py` | `streamlit run dashboard/app.py` |
| **Full Pipeline CLI** | `src/pipeline.py` | `python -m src.pipeline` |
| **System Validation** | `scripts/run_phase10_validation.py`| `python scripts/run_phase10_validation.py` |

---

## 3. Environment Setup

### Step 3.1: Clone the Repository
Open a terminal (PowerShell on Windows, or Bash on macOS/Linux) and navigate to your workspace directory:
```bash
git clone <repository-url> "mini-project"
cd "mini-project"
```

### Step 3.2: Create and Activate Python Virtual Environment
Always isolate dependencies inside a dedicated virtual environment:

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(If script execution is blocked on Windows, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first).*

**On macOS / Linux:**
```bash
python3.10 -m venv venv
source venv/bin/activate
```

Verify your active Python version:
```bash
python --version
# Output must be Python 3.10.x or 3.11.x
```

### Step 3.3: Install Python Dependencies
Upgrade `pip` and install all required scientific and ML dependencies:
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

*Optional packages:*
- To enable Praat-based acoustic feature extraction from uncompressed `.wav` files:
  ```bash
  pip install praat-parselmouth
  ```
- To run FastAPI backend server and Streamlit UI:
  ```bash
  pip install uvicorn fastapi python-multipart streamlit
  ```

### Step 3.4: Install Node.js Dependencies (React Dashboard)
Navigate into the frontend directory and install dependencies:
```bash
cd dashboard/frontend
npm install
cd ../..
```

### Step 3.5: Configure Environment Variables
Copy `.env.example` to `.env` in the project root:

**On Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**On Linux/macOS:**
```bash
cp .env.example .env
```

Open `.env` in your text editor and ensure the parameters are configured:
```env
# Supabase Configuration (Leave default or point to your active Supabase instance)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key

# Frontend Environment Variables (Vite)
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-supabase-anon-key

# Backend API
API_URL=http://localhost:8000/api
VITE_API_URL=http://localhost:8000/api
```

Also verify or copy `.env` to `dashboard/frontend/.env` if configuring custom ports:
```bash
cp .env.example dashboard/frontend/.env
```

---

## 4. Dataset Preparation

### 4.1 Overview of Dataset Roles
The MPF-PD system was developed with strict scientific data governance:
1. **PPMI (Parkinson's Progression Markers Initiative):** Primary clinical reference for olfactory scores (UPSIT), sleep disorders (RBDSQ), and motor ratings (MDS-UPDRS Part III).
2. **UCI Parkinson's Telemonitoring Dataset:** Reference for dysphonia measures (jitter, shimmer, HNR, PPE) across sustained phonation samples.
3. **Public Fundus Imaging (DRIVE / STARE / EyePACS):** Used for pretraining retinal vessel segmentation and topological morphometry extraction.
4. **PhysioNet Gait in Parkinson's Disease:** Used for gait stride interval and cadence extraction.

### 4.2 How to Access Clinical Datasets
- **PPMI:** Register at [PPMI Data Portal](https://www.ppmi-info.org/). Upon signing the Data Use Agreement (DUA), download the clinical tabular CSVs and place them in `data/raw/ppmi/`.
- **UCI Voice:** Download the dataset from the [UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/189/parkinsons+telemonitoring) and place `parkinsons_updrs.data` in `data/raw/uci_voice/`.
- **Public Fundus Images:** Place sample retinal fundus photographs (`.jpg` or `.png`) in `data/raw/retina/`.

### 4.3 Automated Synthetic Fixture (Prototype Simulation Mode)
**Crucial Architectural Safeguard:** Because synchronized same-participant longitudinal datasets spanning all five modalities are not distributed without individual institutional agreements, **MPF-PD contains built-in synthetic clinical fixtures.**

If external datasets are not detected in `data/raw/`, the system automatically switches to:
```
experiment_type: "simulation"
not_trained: true
```
All synthetic data generators adhere to clinical distributions established in Parkinson's literature (e.g., UPSIT normal > 34 vs PD < 22; RBDSQ cutoff >= 5; voice jitter elevation). The pipeline functions end-to-end with 100% feature compliance without requiring immediate external downloads.

---

## 5. Training the Models

You can execute model training for each single modality as well as the central multimodal fusion network using standard Python module commands. Pre-trained weights are already packaged in the `models/` folder, but you can retrain from scratch at any time:

### 5.1 Train Olfactory Model (Modality 1)
Trains age/sex-adjusted UPSIT classifiers (Logistic Regression, Random Forest, XGBoost):
```bash
python -m src.olfactory.train
```
- **Saved Artifacts:** `models/olfactory/model.joblib`, `models/olfactory/preprocessor.joblib`, `models/olfactory/metadata.json`
- **Evaluation Export:** `evaluation/olfactory_results.json`

### 5.2 Train RBD Sleep Model (Modality 2)
Trains RBDSQ questionnaire scoring and thresholded likelihood estimators:
```bash
python -m src.rbd.train
```
- **Saved Artifacts:** `models/rbd/model.joblib`, `models/rbd/metadata.json`
- **Evaluation Export:** `evaluation/rbd_results.json`

### 5.3 Train Voice Acoustic Model (Modality 3)
Trains classifiers on acoustic dysphonia features (jitter, shimmer, HNR, MFCCs):
```bash
python -m src.voice.train
```
- **Saved Artifacts:** `models/voice/model.joblib`, `models/voice/preprocessor.joblib`, `models/voice/metadata.json`
- **Evaluation Export:** `evaluation/voice_results.json`

### 5.4 Train Motor & Gait Model (Modality 4)
Trains cadence, stride regularity, and gait variability estimators:
```bash
python -m src.motor.train
```
- **Saved Artifacts:** `models/motor/model.joblib`, `models/motor/preprocessor.joblib`, `models/motor/metadata.json`
- **Evaluation Export:** `evaluation/motor_results.json`

### 5.5 Train Retinal Biomarker Model (Modality 5)
Trains vessel morphometry pipeline and latent CNN embedding network:
```bash
python -m src.retina.train
```
- **Saved Artifacts:** `models/retina/retina_encoder.pt`, `models/retina/vessel_segmentor.pt`, `models/retina/metadata.json`
- **Evaluation Export:** `evaluation/retina_results.json`

### 5.6 Train Gated Multimodal Fusion Model
Trains the PyTorch gated fusion encoder, attention gates, and final XGBoost risk classifier:
```bash
python -m src.fusion.train
```
- **Saved Artifacts:**
  - `models/fusion/fusion_encoder.pt` (PyTorch Gated Neural Network)
  - `models/fusion/classifier.joblib` (XGBoost Estimator)
  - `models/fusion/preprocessor.joblib` (Feature transformer)
  - `models/fusion/metadata.json` (Provenance and hyperparameters)
- **Evaluation Export:** `evaluation/fusion_results.json`

### 5.7 Generate SHAP Explainability Reports
Computes global Shapley values across the multimodal feature space:
```bash
python -m src.explainability.global_importance
```
- **Saved Artifacts:** `evaluation/xai_global_importance.json`, `evaluation/XAI_REPORT.md`

---

## 6. Running the Backend API (FastAPI)

The backend provides a RESTful API wrapping the entire inference pipeline, adapter layers, and Supabase integration.

### 6.1 Start the Server
Make sure your virtual environment is active, then run:
```bash
uvicorn dashboard.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 6.2 Verify API Health
Open your browser or run curl to test the healthcheck endpoint:
```bash
curl http://localhost:8000/api/health
```

**Expected JSON Response:**
```json
{
  "status": "ok",
  "version": "0.8.0",
  "models_loaded": {
    "fusion_classifier": true,
    "fusion_encoder": true,
    "fusion_preprocessor": true,
    "voice_model": true,
    "motor_model": true,
    "olfactory_model": true,
    "rbd_model": true
  },
  "message": "All model artifacts loaded and ready for multimodal inference."
}
```

### 6.3 Available API Endpoints
| HTTP Method | Route | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | System health and artifact load verification. |
| `GET` | `/api/cohort` | Fetches active research cohort participants. |
| `POST`| `/api/cohort` | Registers a new participant profile. |
| `POST`| `/api/analyze`| Runs multimodal fusion inference with optional audio/gait/retinal file uploads. |
| `POST`| `/api/mobile/analyze` | Ingests daily mobile sensor features via the MPF Adapter. |
| `GET` | `/docs` | Interactive Swagger UI API documentation. |

### 6.4 Test Inference via curl
Test the multimodal inference endpoint with tabular inputs (olfactory + RBD + demographics):
```bash
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "participant": {"age": 68, "sex": "male", "participant_id": "P099"},
    "olfactory": {"available": true, "upsit_total": 19},
    "rbd": {"available": true, "rbdsq_total": 8},
    "voice": {"available": false},
    "motor": {"available": false},
    "retina": {"available": false}
  }'
```

---

## 7. Running the React Dashboard

The frontend is a modern React 18 single-page application built with TypeScript, Tailwind CSS, Vite, Recharts, and Lucide Icons.

### 7.1 Start Vite Development Server
In a new terminal window:
```bash
cd dashboard/frontend
npm run dev
```

The terminal will confirm:
```
  VITE v5.1.6  ready in 240 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

### 7.2 Access the Dashboard
Open your browser and navigate to:
**`http://localhost:5173`**

*(Note: If port 5173 is busy, Vite will automatically select 5174 or 5175, which is handled seamlessly by CORS).*

### 7.3 Executing an Assessment in the UI
1. **Examine Research Disclaimer:** Confirm acceptance of the investigational disclaimer banner at the top of the interface.
2. **Participant Demographics:** Enter participant ID (e.g. `PART-042`), Age (e.g. `67`), and Biological Sex.
3. **Olfactory Input:** Provide UPSIT score (range 0–40, e.g. `21`).
4. **RBD Sleep Input:** Complete the RBDSQ items or enter total score (range 0–13, e.g. `7`).
5. **Digital Modalities (Optional):**
   - Upload a voice sample (`.wav`) or leave unchecked to trigger missing modality masking.
   - Upload a gait/motor sensor file (`.csv`) or leave unchecked.
   - Upload a retinal fundus photograph (`.png`/`.jpg`) or leave unchecked.
6. **Trigger Analysis:** Click the **"Run Risk Pattern Analysis"** button.
7. **Interpreting Results:**
   - **Multimodal Risk Gauge:** Shows the calibrated risk estimate (0.0 to 1.0) with risk category (`low`, `moderate`, `elevated`).
   - **Modality Gate Weights:** Recharts visualizer displaying how the neural attention network weighted each modality.
   - **Local SHAP Feature Importance:** Bar plot showing the top positive and negative risk contributors.
   - **Missing Modality Notice:** Badges highlighting missing modalities with explicit penalty-free masking confirmation.
   - **Export Report:** Click **"Download JSON Summary"** or **"Export PDF"** to save the structured audit report.

---

## 8. Running the Mobile Extension & Supabase Backend

The mobile extension enables longitudinal digital biomarker collection (keystroke dynamics, tap rate, vocal stability, sleep proxy) and connects to MPF via the frozen `MPFAdapter`.

### 8.1 Setting Up the Supabase Database
1. Log in to [Supabase Console](https://supabase.com/).
2. Open the **SQL Editor** in your Supabase dashboard.
3. Execute the migration scripts located in `supabase/migrations/` in sequential order:
   - `001_initial_schema.sql` (Creates users, consent records, sensor logs)
   - `002_model_registry.sql` (Model version audit trail)
   - `003_mobile_tables.sql` (Daily mobile feature tables)
   - `004_rls_policies.sql` (Row-level security enforcement)
   - `005_audit_logs.sql` (HIPAA/GDPR compliant audit trail)
   - `006_data_retention.sql` (Consent revocation and automated purge routines)
4. (Optional) Run `supabase/seed/seed_model_versions.sql` to populate baseline metadata.

### 8.2 Testing Mobile Ingestion via API
To simulate a daily sync from the mobile app:
```bash
curl -X POST "http://localhost:8000/api/mobile/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "participant_id": "MOB-TEST-001",
    "feature_date": "2026-09-23",
    "features": {
      "typing_mean_hold_time": 115.4,
      "typing_flight_time_variance": 42.1,
      "voice_jitter_local": 0.0185,
      "voice_shimmer_local": 0.042,
      "gait_cadence_steps_per_min": 98.2,
      "tap_inter_tap_interval_std": 38.5
    },
    "demographics": {"age": 65, "sex": "female"},
    "log_to_db": false
  }'
```

### 8.3 Verifying Privacy & Revocation Flow
The mobile extension guarantees that participants can revoke consent and permanently scrub their data. Run the automated privacy verification suite:
```bash
pytest tests/test_consent_revocation.py tests/test_data_deletion.py -v
```

---

## 9. Running Tests & Validation

The codebase includes an extensive Pytest suite ensuring 100% deterministic reproducibility, zero data leakage, and mathematical resilience under missing inputs.

### 9.1 Run Entire Test Suite
```bash
pytest
```
*Expected: 238+ passed assertions with zero test failures.*

### 9.2 Run Specific Phase / Component Tests
- **Multimodal Pipeline & Gating Tests:**
  ```bash
  pytest tests/test_pipeline.py tests/test_fusion.py -v
  ```
- **Missing Modality Graceful Degradation Tests:**
  ```bash
  pytest tests/test_missing_modalities.py -v
  ```
- **Single Modality Unit Tests:**
  ```bash
  pytest tests/test_olfactory.py tests/test_rbd.py tests/test_voice.py tests/test_motor.py tests/test_retina.py -v
  ```
- **SHAP Explainability Verification Tests:**
  ```bash
  pytest tests/test_xai.py -v
  ```
- **Mobile Adapter & Feature Mapping Tests:**
  ```bash
  pytest tests/test_feature_mapping.py tests/test_adapter_output.py tests/test_no_retraining.py -v
  ```

### 9.3 Run Master Phase 10 Validation Script
To regenerate the full validation audit report:
```bash
python scripts/run_phase10_validation.py
```
This script audits participant disjointness, verifies zero data leakage, runs cross-modality benchmarks, checks robustness against corrupted inputs, and generates `evaluation/FINAL_EVALUATION.md`.

---

## 10. Common Issues and Solutions

### Issue 1: "FileNotFoundError: Model artifacts missing"
- **Cause:** Pretrained weights were deleted or not generated.
- **Solution:** Run the individual training pipelines to generate fresh artifacts:
  ```bash
  python -m src.olfactory.train
  python -m src.rbd.train
  python -m src.voice.train
  python -m src.motor.train
  python -m src.retina.train
  python -m src.fusion.train
  ```

### Issue 2: "Port 8000 or 5173 Already in Use"
- **Cause:** A previous instance of Uvicorn or Vite is running in the background.
- **Solution:**
  - *Windows (PowerShell):*
    ```powershell
    Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process -Force
    ```
  - *macOS / Linux:*
    ```bash
    lsof -ti:8000 | xargs kill -9
    ```
  - Alternatively, launch on a custom port:
    ```bash
    uvicorn dashboard.api.main:app --port 8001
    ```

### Issue 3: "CUDA Out of Memory" or "PyTorch GPU Error"
- **Cause:** Insufficient VRAM when training retinal CNN on large image batches.
- **Solution:** Force CPU execution. In `config.yaml`, ensure `device: cpu`, or set environment variable:
  ```bash
  # Windows PowerShell
  $env:CUDA_VISIBLE_DEVICES=""
  # Linux/macOS
  export CUDA_VISIBLE_DEVICES=""
  ```

### Issue 4: "Supabase Connection Timed Out"
- **Cause:** Invalid Supabase URL or network proxy blocking outbound HTTPS traffic.
- **Solution:** The FastAPI backend is designed to run in standalone local mode. If Supabase is unreachable, local in-memory fallbacks automatically preserve full dashboard inference without crashing.

### Issue 5: "Praat / Parselmouth C-Extension Warning"
- **Cause:** Optional audio analysis library `praat-parselmouth` is not installed.
- **Solution:** MPF-PD contains an internal pure-Python fallback using `librosa` and `scipy.signal`. To install native Praat support:
  ```bash
  pip install praat-parselmouth
  ```

---
*End of Execution Guide. For scientific architecture and guide presentation details, consult `PROJECT_EXPLANATION.md`.*
