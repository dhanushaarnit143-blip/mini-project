# MPF-PD: Multimodal Prodromal Fusion for Parkinson’s Disease Risk Screening

## Project Summary
A research prototype investigating multimodal fusion of olfactory, RBD, voice, motor/gait, and retinal biomarkers for early Parkinson’s risk screening.

## Medical Disclaimer
> [!WARNING]
> **This project is a research prototype and does not provide medical diagnosis.**
> It is designed exclusively for investigational risk stratification research and decision-support algorithms.

## Defensible Novelty Statement
The main investigational contribution of this work is the fusion of non-invasive retinal microvascular/structural biomarkers with prodromal digital (voice, touchscreen motor, IMU gait/tremor) and clinical (RBDSQ, olfactory) biomarkers deployed via a non-specialist screening pathway.

## Phase Roadmap
- **Phase 0: Environment & Architecture Setup** (Current)
- **Phase 1: Dataset Research & Data Engineering**
- **Phase 2: Olfactory + RBD Biomarker Pipelines**
- **Phase 3: Voice Biomarker Pipeline**
- **Phase 4: Touchscreen & IMU Motor/Gait Biomarker Pipeline**
- **Phase 5: Retinal Biomarker Pipeline**
- **Phase 6: Multimodal Fusion & Explainability Dashboard**

## Installation Instructions
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows PowerShell: .venv\Scripts\Activate.ps1

# Upgrade pip and install core dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Test & Health-Check Instructions
```bash
# Run automated tests
pytest -v

# Run system health check
python scripts/healthcheck.py
```

## Directory Structure Overview
```
mpf-pd/
├── README.md
├── requirements.txt
├── config.yaml
├── .gitignore
├── data/
│   ├── raw/
│   ├── interim/
│   ├── processed/
│   ├── external/
│   └── metadata/
├── models/
│   ├── olfactory/
│   ├── rbd/
│   ├── voice/
│   ├── motor/
│   ├── retina/
│   └── fusion/
├── evaluation/
├── logs/
├── notebooks/
├── scripts/
│   └── healthcheck.py
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── logging_utils.py
│   ├── seeds.py
│   ├── healthcheck.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── loaders.py
│   │   ├── validators.py
│   │   └── registry.py
│   ├── olfactory/
│   │   └── __init__.py
│   ├── rbd/
│   │   └── __init__.py
│   ├── voice/
│   │   └── __init__.py
│   ├── motor/
│   │   └── __init__.py
│   ├── retina/
│   │   └── __init__.py
│   └── fusion/
│       └── __init__.py
└── tests/
    ├── __init__.py
    ├── test_imports.py
    ├── test_config.py
    ├── test_logging.py
    ├── test_seed.py
    └── test_healthcheck.py
```
