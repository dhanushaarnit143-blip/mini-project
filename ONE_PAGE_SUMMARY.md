# MPF-PD: Executive Project Summary

**Project Title:** Multimodal Prodromal Fusion for Parkinson's Disease Risk Screening (MPF-PD)  
**Document Type:** One-Page Executive Brief  
**System Status:** Complete Investigational Research Prototype (Phases 0–11)  

---

> [!IMPORTANT]
> **MANDATORY SCIENTIFIC DISCLAIMER**  
> **Research Prototype Only. Not a Diagnostic Tool.**  
> MPF-PD is an investigational decision-support prototype for risk pattern estimation. It does not diagnose Parkinson's disease. Clinical diagnosis requires evaluation by a board-certified neurologist or movement disorder specialist.

---

### 1. Problem Statement
Parkinson's disease diagnosis currently occurs only after manifest motor symptoms appear, at which point 50% to 70% of dopaminergic neurons in the substantia nigra are already irreversibly degenerated. In the preceding prodromal stage, subtle warning signs occur across multiple biological systems (loss of smell, sleep disturbances, micro-speech changes, and retinal microvascular changes), but no single symptom is sufficiently reliable in isolation.

### 2. Proposed Solution
We propose **MPF-PD**, a multimodal machine learning framework that integrates five non-invasive prodromal modalities—olfactory testing, REM sleep behavior disorder screening, vocal acoustic analysis, motor/gait dynamics, and retinal fundus imaging—into a single risk-screening model. The system employs a dynamic neural attention gating architecture that estimates calibrated risk while gracefully handling missing modalities without penalty. The framework is deployed through a modern React dashboard and extended with longitudinal mobile digital biomarker collection.

### 3. Defensible Novelty Claim
Our defensible novelty is the fusion of retinal microvascular biomarkers with prodromal digital biomarkers (RBD screening, olfactory testing, voice acoustics, and gait) inside a single multimodal model, a combination not previously integrated in literature. Additionally, we propose and implement an accessible screening deployment pathway that leverages non-specialist community infrastructure, such as routine optometry fundus photography and smartphone-based digital tasks.

### 4. End-to-End Architecture
$$\text{Participant Inputs (5 Modalities)} \longrightarrow \text{Feature Extractors} \longrightarrow \text{Gated Neural Fusion} \longrightarrow \text{Calibrated XGBoost} \longrightarrow \text{SHAP XAI} \longrightarrow \text{React Dashboard}$$

### 5. Technology Stack
- **Core ML & Deep Learning:** Python 3.10, PyTorch (gated fusion encoder, U-Net), Scikit-Learn, XGBoost
- **Signal & Image Processing:** Librosa, SoundFile, Praat/Parselmouth, OpenCV
- **Explainability:** SHAP (TreeExplainer with local & global feature attribution)
- **Backend & Storage:** FastAPI (REST API), Pydantic v2, Supabase (PostgreSQL, Row-Level Security)
- **Frontend & Visualization:** React 18, TypeScript, Tailwind CSS, Vite, Recharts, Lucide Icons
- **Software Quality:** Pytest (238+ automated unit and integration tests)

### 6. Datasets & Provenance
- **PPMI (Parkinson's Progression Markers Initiative):** Reference for olfactory (UPSIT), sleep (RBDSQ), and clinical motor scores.
- **UCI Parkinson's Telemonitoring Dataset:** Reference for vocal phonation dysphonia features.
- **PhysioNet Gait in PD:** Reference for vertical ground reaction force cadence and stride variability.
- **DRIVE / STARE / EyePACS:** Reference for retinal vessel segmentation pretraining (no PD labels).
- **Synthetic Multimodal Aligned Fixture:** Active local simulation fixture (N=350) for end-to-end architectural validation.

### 7. Key Results (Prototype Simulation)
- **Individual Modalities (Test F1):** Olfactory = 0.943 | RBD Sleep = 0.931 | Voice = 0.844 | Motor/Gait = 0.857
- **Gated Multimodal Fusion:** ROC-AUC = 1.000 | F1 = 1.000 | Brier Calibration Score = 0.0031
- **Missing Modality Robustness:** Seamless degradation down to 2 modalities with zero software crashes.
- **Code Quality:** 100% test pass rate across 238 unit assertions; zero train/test data leakage.

### 8. Key Limitations
- **Synthetic Simulation Fixture:** Multimodal fusion results reflect software feasibility on literature-calibrated simulation data, not real human clinical trials.
- **Lack of Synchronized Public Cohorts:** No open-access repository currently provides co-occurring 5-modality measurements from the same participants.
- **Post-Hoc Explainability:** SHAP feature attributions reflect mathematical model correlations rather than proven biological causation.

### 9. Future Work
- **Prospective Clinical Trial:** Validate the pipeline on an IRB-approved prospective prodromal cohort with multi-year motor conversion tracking.
- **Optical Coherence Tomography (OCT):** Incorporate cross-sectional retinal layer thickness (macular ganglion cell complex thinning) to enhance sensitivity.

---
*MPF-PD Research Group — Investigational Research Prototype — Not for Clinical Diagnostic Use.*
