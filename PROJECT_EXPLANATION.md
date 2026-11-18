# MPF-PD Guide & Supervisor Explanation Document

**Project Title:** Multimodal Prodromal Fusion for Parkinson's Disease Risk Screening (MPF-PD)  
**Author / Presenter:** Project Engineering & Research Team  
**Target Audience:** Project Guide, Faculty Supervisor, Evaluation Panel, External Reviewers  
**Document Purpose:** Complete, structured viva/defense presentation script and technical explanation guide.  
**Total Presentation Duration:** ~20 minutes (or adaptable to 10–15 min summaries).

---

## Non-Negotiable Presentation Framing & Clinical Safeguards
When presenting to guides or review panels, always adhere to the following principles:
- **Never claim diagnosis:** The system is an **investigational research prototype** that performs *risk pattern estimation*.
- **Never inflate dataset claims:** Explicitly distinguish between public retrospective training data, synthetic multimodal simulation fixtures, and prospective clinical validation.
- **Accurate terminology:** Use *"elevated Parkinson's risk pattern"*, *"research risk estimate"*, or *"multimodal risk signal"*; never use *"patient has Parkinson's"* or *"disease detected"*.

---

## SECTION A: Problem Statement (2 Minutes)

Good morning/afternoon, respected guide and panel members. Today I am presenting our work on **MPF-PD: Multimodal Prodromal Fusion for Parkinson's Disease Risk Screening**.

### 1. What is Parkinson's Disease?
Parkinson's disease (PD) is the second most common progressive neurodegenerative disorder worldwide, characterized pathologically by the accumulation of alpha-synuclein protein aggregates (Lewy bodies) and the progressive loss of dopaminergic neurons within the substantia nigra pars compacta.

### 2. Why is Early Detection Important, and Why is Current Diagnosis Too Late?
Under current clinical criteria (such as MDS Clinical Diagnostic Criteria), diagnosis relies predominantly on manifest motor signs: resting tremor, bradykinesia, rigidity, and postural instability. 

By the time a patient notices these motor symptoms and receives a formal diagnosis from a movement disorder specialist:
- **Between 50% to 70% of dopaminergic neurons in the substantia nigra have already degenerated irreversibly.**
- At this advanced stage, therapeutic interventions can only offer symptomatic relief; there is no opportunity to preserve the damaged neuronal architecture.

### 3. The Prodromal Window: The Crucial Opportunity
Years or even a decade before motor symptoms manifest, patients enter the **prodromal stage**. During this extended preclinical phase, neurodegeneration produces subtle, non-motor and micro-motor abnormalities across distinct biological systems:
- **Olfactory dysfunction (Hyposmia):** Reduced sense of smell, occurring in up to 90% of early-stage patients.
- **REM Sleep Behavior Disorder (RBD):** Dream-enactment behavior due to brainstem nuclei degeneration; over 70% of idiopathic RBD patients phenoconvert to a synucleinopathy within 10–12 years.
- **Subtle Acoustic Changes:** Early vocal fold hypokinesia leading to micro-jitter, reduced pitch variability, and dysphonia.
- **Subtle Motor & Gait Irregularities:** Minor reductions in arm swing, cadence irregularities, and micro-tremor detectable via digital sensors.
- **Retinal Microvascular & Structural Changes:** The retina is an embryological extension of the central nervous system; neurodegeneration causes retinal ganglion cell loss and microvascular thinning detectable via fundus imaging.

### 4. The Core Gap Addressed
No single prodromal symptom is sufficiently sensitive or specific on its own. For example, hyposmia can result from chronic sinusitis or viral infections; sleep disturbances can stem from stress or obstructive sleep apnea. 

**The core research gap:** Existing computer-aided tools either focus on post-diagnosis motor severity tracking or rely on a single modality. What is missing is a unified, explainable framework that fuses **retinal microvascular biomarkers** with **prodromal digital biomarkers** (smell, sleep, voice, and gait) into a single risk screening model designed for non-specialist deployment.

---

## SECTION B: Motivation and Objectives (2 Minutes)

### Why Multimodal Fusion?
In the prodromal phase, physiological signals are weak and noisy. Individual modalities provide noisy, incomplete observations of underlying neurodegeneration. By integrating complementary signals across five distinct physiological domains:
1. **Sensory:** Olfactory identification
2. **Neurological/Sleep:** Brainstem-mediated sleep regulation (RBD)
3. **Phonatory:** Vocal fold neuromuscular stability
4. **Motor/Biomechanical:** Stride dynamics and motor timing
5. **Neurovascular:** Retinal microvascular architecture

Multimodal fusion leverages orthogonality: when one modality is equivocal or missing, other modalities reinforce or temper the composite risk signal.

### Why a Prodromal Focus Instead of Post-Diagnosis Classification?
Classifying manifest Parkinson's with full-blown resting tremor is clinically trivial and therapeutically late. The greatest clinical and societal value lies in identifying individuals during the prodromal window—the exact population that will be eligible for future disease-modifying neuroprotective drugs currently in clinical trials.

### Why Non-Specialist Deployment?
Movement disorder specialists are concentrated in academic medical centers with multi-month waiting lists. Our system is designed for accessible community-level screening:
- Olfactory scratch-and-sniff cards (e.g. UPSIT) can be administered at home or in primary care.
- Validated sleep questionnaires (RBDSQ) require only 3 minutes.
- Voice and motor tasks run on ubiquitous smartphones.
- Retinal imaging leverages standard fundus cameras already present in routine community optometry clinics.

### Specific Project Objectives
1. **Develop Five Modality Pipelines:** Build dedicated preprocessing, feature extraction, and validation pipelines for olfactory, RBD, voice, motor, and retinal inputs.
2. **Construct a Gated Multimodal Fusion Architecture:** Implement a neural network with dynamic attention gating and presence flags that handles missing modalities without performance collapse.
3. **Implement Post-Hoc Explainability (SHAP):** Provide clinician-interpretable attributions showing exact feature and modality contributions for each individual risk estimate.
4. **Build a Full-Stack Prototype Application:** Deploy a FastAPI backend and modern React + Tailwind CSS dashboard with comprehensive audit and export capabilities.
5. **Extend via Mobile Digital Biomarkers:** Build a longitudinal smartphone data collection adapter that maps continuous daily digital features into the frozen MPF screening model without retraining.

---

## SECTION C: Defensible Novelty Claim (2 Minutes)

To maintain absolute academic integrity, we state our novelty with precision and defensibility:

### Our Exact Defensible Novelty Statement
> *"Our defensible novelty is the fusion of retinal biomarkers with prodromal digital biomarkers — RBD screening, olfactory testing, voice, and motor/gait — inside a single multimodal model. This specific combination was not found integrated in the current literature. Additionally, we propose a deployment pathway through non-specialist screening infrastructure, such as optometry practices and smartphone-based tasks."*

### What We Do NOT Claim
- We do **NOT** claim to have invented multimodal machine learning for Parkinson's disease.
- We do **NOT** claim to be the first to combine voice and gait (this has been studied extensively in manifest cohorts).
- We do **NOT** claim that this system diagnoses Parkinson's disease.
- We do **NOT** claim to lower the official clinical age of diagnosis.
- We do **NOT** claim that a smartphone camera can capture retinal fundus images.

### What We Positively DO Claim
- We systematically investigate a novel 5-modality feature combination (retinal + olfactory + RBD + voice + motor) not previously integrated into a single unified architecture.
- We implement dynamic neural attention gating that provides penalty-free handling of arbitrary missing modalities.
- We demonstrate how community optometry and mobile interfaces can serve as a distributed screening funnel.
- We provide transparent, local SHAP explainability on every prediction, ensuring that the tool functions as an interpretable research decision-support aid.

---

## SECTION D: Architecture & Methodology (3 Minutes)

The entire MPF-PD pipeline follows a clear, unidirectional flow:

```
Participant Input (5 Modalities)
      │
      ▼
Modality-Specific Preprocessing & Feature Extraction
  ├── Olfactory:  UPSIT score → Age/Sex Norm tables → Error Pattern Vector (d=4)
  ├── RBD:        RBDSQ items → Total + Dream/Motor Subscales (d=3)
  ├── Voice:      Audio (.wav) → Praat/librosa → Jitter, Shimmer, HNR, MFCCs (d=16)
  ├── Motor:      VGRF/IMU (.csv) → Stride intervals, Cadence, Regularity (d=6)
  └── Retina:     Fundus Image → U-Net Vessel Segmentation + ResNet Embedding (d=20)
      │
      ▼
Modality Imputation & Scaler Standardization (Fitted strictly on train splits)
      │
      ▼
Gated Multimodal Fusion Encoder (PyTorch)
  ├── Learnable Modality Projections (each projected to latent space)
  ├── Dynamic Attention Gating Layer (computes soft attention weights per modality)
  └── Presence Masking (multiplies by binary availability flags [m_1, ..., m_5])
      │
      ▼
45-Dimensional Unified Fused Representation Vector
      │
      ▼
Calibrated Final Classifier (XGBoost)
      │
      ▼
Output: Calibrated Risk Score (0.00 – 1.00) & Categorical Risk Tier
      │
      ▼
Explainability Engine (SHAP TreeExplainer)
  ├── Modality Contribution Decomposition
  └── Top-N Positive / Negative Feature Attributions
      │
      ▼
Research Dashboard (React 18 + Tailwind CSS / FastAPI)
```

### Modality Engineering Details:
1. **Olfactory Modality:** Processes University of Pennsylvania Smell Identification Test (UPSIT) or Brief Smell Identification Test (B-SIT) scores. Incorporates age- and biological-sex-adjusted normative percentiles, distinguishing benign presbyosmia (normal aging) from neurodegenerative hyposmia.
2. **RBD Sleep Modality:** Scores the 13-item REM Sleep Behavior Disorder Screening Questionnaire (RBDSQ). Extracts the composite score (clinical cut-off $\ge 5$), item 10 motor sub-score, and dream enactment frequency.
3. **Voice Modality:** Ingests sustained vowel phonation (/a/). Computes dysphonia features including local jitter, local shimmer, harmonics-to-noise ratio (HNR), pitch period entropy (PPE), and recurrence period density entropy (RPDE).
4. **Motor / Gait Modality:** Processes bilateral vertical ground reaction force (VGRF) or smartphone IMU accelerometry. Computes stride time variability, gait cadence, stance/swing phase ratio, and spectral energy in the tremor band (4–7 Hz).
5. **Retinal Modality:** Preprocesses 45° fundus photography. Employs a U-Net architecture to segment the retinal microvasculature, from which morphological parameters are extracted: vessel area density, fractal branching dimension ($D_f$), average tortuosity, and foveal avascular zone (FAZ) contour, augmented with a 16-dimensional CNN latent embedding.

### Gated Multimodal Fusion & Missing Data Handling:
Real-world screening participants rarely present all five modalities. Instead of discarding incomplete records or applying naive mean imputation:
- Each modality's feature vector is projected into a normalized latent subspace.
- A **Neural Attention Gating Module** learns a gating vector $g = \sigma(W_g [h_1, \dots, h_5] + b_g)$.
- When a modality is absent, its presence flag is set to $0$. The network zero-masks the missing modality and re-normalizes attention weights across the active modalities via a masked softmax:
  $$\alpha_i = \frac{m_i \cdot \exp(g_i)}{\sum_{j=1}^5 m_j \cdot \exp(g_j) + \epsilon}$$
- This guarantees that an individual is **never penalized simply because a test was unavailable**.

### Explainability Engine:
An exact TreeExplainer (SHAP) operates on the final classifier. It computes exact Shapley feature attributions, answering two critical questions for researchers:
1. *Which modality drove this participant's risk score?* (e.g. 48% Olfactory, 32% RBD, 20% Motor).
2. *Which specific features were abnormal?* (e.g. UPSIT score of 18 increased risk by +0.28, while normal gait cadence lowered risk by -0.12).

---

## SECTION E: Technology Stack (1 Minute)

The project leverages a robust, production-grade open-source stack:
- **Core Scientific Computing:** Python 3.10+, NumPy, Pandas, SciPy.
- **Machine Learning & Deep Learning:** PyTorch (gated fusion encoder, retinal CNN), Scikit-Learn (preprocessing, linear models, Random Forests), XGBoost (calibrated gradient-boosted risk classifier).
- **Acoustic & Signal Processing:** Librosa, SoundFile, Praat/Parselmouth.
- **Computer Vision:** OpenCV, PyTorch Torchvision.
- **Model Explainability:** SHAP (Shapley Additive exPlanations).
- **Backend API:** FastAPI (asynchronous ASGI), Pydantic v2 (schema validation), Uvicorn.
- **Frontend Dashboard:** React 18, TypeScript, Tailwind CSS, Vite, Recharts (dynamic risk gauge, gate visualization), Lucide React.
- **Mobile Backend & Persistence:** Supabase (PostgreSQL with Row-Level Security, audit logging, encrypted consent storage).
- **Software Quality Assurance:** Pytest, Pytest-cov (238+ automated test assertions).

---

## SECTION F: Datasets and Scientific Provenance (2 Minutes)

To ensure scientific honesty, we categorize all data sources under explicit provenance classifications:

| Dataset | Modality Covered | Provenance Category | Status in Project |
| :--- | :--- | :---: | :--- |
| **PPMI** | Olfactory, Sleep, Motor, Demographics | Category A (Clinical Multimodal) | DUA protocol defined; remote/restricted |
| **UCI Voice** | Sustained Voice Dysphonia | Category B (Modality-Specific) | CC BY 4.0; manifest PD telemonitoring |
| **PhysioNet Gait** | Vertical Ground Reaction Force | Category B (Modality-Specific) | ODC-By v1.0; 93 PD vs 73 Healthy Controls |
| **DRIVE / STARE / EyePACS** | Retinal Fundus Photography | Category C (Pretraining Only) | Pretraining vascular segmentation (**NO PD LABELS**) |
| **Synthetic Multimodal Fixture** | All 5 Modalities Aligned (N=350) | Category E (Synthetic Fixture) | **Active local prototype fixture** |

### Crucial Statements on Data Reality:
1. *"We use public retrospective datasets and validated clinical literature distributions for prototype validation. We do NOT claim clinical validation."*
2. *"Our fusion experiment is explicitly labeled as a prototype/simulation because true same-participant multimodal data across all five modalities was not publicly available in a single unrestricted open dataset. The architecture is fully implemented, verified, and functional, but clinical validation requires a dedicated prospective multimodal cohort."*

---

## SECTION G: Results and Evaluation (2 Minutes)

Our validation protocol (Phase 10) executed an exhaustive technical audit across held-out test splits:

### 1. Individual Modality Performance (Held-out Test Split, N=53)
- **Olfactory Model:** Accuracy = 94.3%, Recall = 92.6%, F1 = 0.943, ROC-AUC = 0.994
- **RBD Sleep Model:** Accuracy = 92.5%, Recall = 100.0%, F1 = 0.931, ROC-AUC = 0.994
- **Voice Acoustic Model:** Accuracy = 81.1%, Recall = 100.0%, F1 = 0.844, ROC-AUC = 0.979
- **Motor / Gait Model:** Accuracy = 83.0%, Recall = 100.0%, F1 = 0.857, ROC-AUC = 0.987
- **Retinal Modality:** Extracted quantitative microvascular morphometry (vessel density, fractal dimension) and latent embeddings for fusion.

### 2. Fusion Performance vs. Baselines
On the aligned evaluation fixture:
- **Gated Multimodal Fusion:** Accuracy = 100.0%, F1 = 1.000, ROC-AUC = 1.000, **Brier Score = 0.0031**
- **Feature Concatenation + XGBoost:** ROC-AUC = 1.000, Brier Score = 0.0042
- **Weighted Average Baseline:** ROC-AUC = 1.000, Brier Score = 0.0125

*Key Finding:* While simple concatenation achieves high separation on synthetic data, **Gated Fusion achieves superior probability calibration (lowest Brier score: 0.0031 vs 0.0125)** and retains stability when modalities are masked.

### 3. Graceful Degradation Under Missing Modalities
- Full 5 Modalities: ROC-AUC = 1.000, F1 = 0.981
- Missing Retina: ROC-AUC = 1.000, F1 = 0.981 (Attention dynamically reallocated to Olfactory and Motor)
- Missing Voice: ROC-AUC = 1.000, F1 = 0.962
- Missing Retina + Voice: ROC-AUC = 1.000, F1 = 0.941
- Missing 3 Modalities (Olfactory + RBD only): ROC-AUC = 1.000, F1 = 0.851
- Single Modality Only (Olfactory): ROC-AUC = 0.978 (AUC drop = 0.022)
- *Recommendation:* The system functions with any subset, but requires **a minimum of 2 active modalities** for high confidence.

### 4. Zero Data Leakage Verification
An automated leakage audit (`evaluation/leakage_report.json`) confirmed:
- Zero participant ID overlap between train, validation, and test splits.
- All scalers, imputers, and normalizers fitted exclusively on training splits.
- Zero audio recording or fundus image duplication across partitions.

---

## SECTION H: Limitations (2 Minutes)

We maintain complete scientific transparency regarding the project's limitations:

1. **Simulation Data Constraint:** Current multimodal fusion metrics stem from synthetic fixtures aligned to literature distributions; they demonstrate architectural correctness, not human diagnostic efficacy.
2. **Lack of Synchronized Public Cohorts:** No public repository currently provides simultaneous same-participant retinal scans, speech audio, gait sensor logs, and UPSIT scores without restricted institutional DUAs.
3. **Absence of Prospective Clinical Trials:** The system has not been tested prospectively in living patients entering primary care or neurology clinics.
4. **Retinal Pretraining Limitations:** Public fundus datasets (DRIVE, EyePACS) contain diabetic retinopathy annotations, not confirmed Parkinson's retinal labels.
5. **Acoustic Environment Sensitivity:** Voice dysphonia analysis can be degraded by microphone frequency response, room reverberation, and background noise.
6. **Laboratory vs. Free-Living Motor Data:** Physical gait datasets derive from supervised treadmill/force-plate tasks, which differ from unconstrained daily smartphone movement.
7. **Demographic & Ethnic Bias:** Retinal fundus pigmentation varies significantly across ethnicities; speech features vary across dialects and languages. Current public models lack full demographic calibration.
8. **Longitudinal Latency:** In real life, prodromal phenoconversion occurs over 5 to 10 years; retrospective cross-sectional snapshots cannot capture rapid micro-trajectories.
9. **Mobile Digital Biomarkers are Proxies:** Daily smartphone typing and tapping measures are behavioral proxies, not clinical motor ratings.
10. **Explainability is Post-Hoc:** SHAP explains the tree model's mathematical associations, which reflect statistical correlation rather than direct neurobiological causation.

---

## SECTION I: Future Work (1 Minute)

To transition this research prototype toward clinical translation, future work will focus on:
1. **Prospective Clinical Cohort Validation:** Partner with a movement disorder registry to collect synchronized 5-modality data from 500+ prodromal participants over a 5-year follow-up.
2. **Optical Coherence Tomography (OCT / OCTA):** Integrate cross-sectional retinal layer thickness measurements (specifically macular ganglion cell-inner plexiform layer [GCIPL] thinning).
3. **Longitudinal Survival & Hazard Modeling:** Transition from binary risk classification to time-to-phenoconversion survival models (e.g. Cox proportional hazards or deep survival neural networks).
4. **Genomic & Blood Biomarker Integration:** Ingest GBA/LRRK2 mutation status and serum neurofilament light chain (NfL) levels.
5. **Multi-Center Federated Learning:** Train models across hospital nodes without pooling sensitive patient data.

---

## SECTION J: Live Demonstration Walkthrough (3 Minutes)

Here is the structured sequence for demonstrating the running prototype:

1. **Open Dashboard:** Navigate to `http://localhost:5173`.
2. **Highlight Research Disclaimer:** Point out the prominent banner: *"Research Prototype Only. Not for Clinical Diagnosis."*
3. **Enter Demographics:** Enter participant identifier `PART-PRODROMAL-01`, Age `68`, Sex `Male`.
4. **Enter Olfactory Assessment:** Input UPSIT score `19` (demonstrating moderate hyposmia; normal $>34$).
5. **Enter RBD Assessment:** Check affirmative on dream enactment and motor movements, yielding RBDSQ score `8` (above the clinical cut-off of 5).
6. **Upload Voice Sample:** Select a sustained vowel `/a/` recording, showing automatic acoustic extraction.
7. **Leave Retinal Upload Unchecked:** Deliberately leave the retinal modality unselected to demonstrate missing modality handling.
8. **Execute Inference:** Click **"Run Risk Pattern Analysis"**.
9. **Examine Multimodal Risk Gauge:** Display the calibrated risk score (e.g. `0.84 — Elevated Risk Pattern`).
10. **Examine Attention Gate Allocations:** Show the Recharts bar chart demonstrating how the neural gating network automatically reallocated weight from the absent retinal modality to the available olfactory and sleep modalities.
11. **Examine Local SHAP Breakdown:** Highlight the waterfall chart showing that hyposmia (+0.31) and positive RBD (+0.26) were the dominant positive risk drivers.
12. **Review Missing Modality Badge:** Show the informational callout: *"Retinal Modality Missing: Evaluated with remaining 4 modalities without penalty."*
13. **Export Audit Report:** Click **"Download JSON Summary"** to inspect the structured, timestamped audit payload.
14. **Conclude with Disclaimer:** Reiterate to the panel: *"This demonstrates end-to-end system viability, robust missingness handling, and full interpretability for research screening."*

---
*End of Project Explanation Document.*
