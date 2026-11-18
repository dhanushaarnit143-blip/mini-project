# MPF-PD Slide Deck Outline for Project Defense / Viva

**Project Title:** Multimodal Prodromal Fusion for Parkinson's Disease Risk Screening (MPF-PD)  
**Target Duration:** 15 to 20 Minutes (16 Slides)  
**Intended Use:** Master presentation template for project guides, supervisors, academic committees, and evaluation panels.

---

### Slide 1: Title Slide
- **Title:** Multimodal Prodromal Fusion for Parkinson's Disease Risk Screening (MPF-PD)
- **Subtitle:** An Explainable Multi-Source Machine Learning Framework for Non-Specialist Early Risk Estimation
- **Presenter Names:** [Student / Candidate Names]
- **Department / Institution:** Department of Computer Science & Engineering / Biomedical Engineering
- **Project Supervisor:** [Guide / Faculty Name & Designation]
- **Academic Year:** 2026
- **Visuals:** Project logo; high-level icon array representing the 5 modalities (Nose, Bed, Waveform, Walking Figure, Eye).
- **Footer Alert:** *"Investigational Research Prototype. Not a Clinical Diagnostic Tool."*
- **Speaker Timing:** 1 minute.
- **Key Talking Point:** Introduce the project title, emphasizing that this is an engineering research prototype designed to explore early prodromal risk patterns.

---

### Slide 2: Clinical Context & The Core Problem
- **Headline:** Current Parkinson's Diagnosis Occurs Too Late
- **Key Bullet Points:**
  - Parkinson's is the 2nd most common progressive neurodegenerative disorder worldwide.
  - Current diagnosis relies on manifest motor symptoms (resting tremor, bradykinesia, rigidity).
  - **The Irreversible Deficit:** By the time a movement disorder specialist confirms diagnosis, **50% to 70% of dopaminergic substantia nigra neurons are already destroyed**.
  - Current pharmacological therapies offer only symptomatic relief; neuroprotective treatments must intervene *earlier*.
- **Visuals:** Timeline diagram showing the 10-year prodromal phase vs. the manifest clinical motor threshold; bar chart of dopaminergic neuronal loss over time.
- **Speaker Timing:** 1.5 minutes.
- **Key Talking Point:** Frame the urgency: clinical diagnosis today catches the disease at the finish line of neuronal death, rather than at its starting point.

---

### Slide 3: The Prodromal Opportunity & Five Modalities
- **Headline:** Early Warning Signals Exist Across Distinct Biological Systems
- **Key Bullet Points:**
  - Years before motor diagnosis, multi-organ neurodegeneration produces subtle prodromal markers:
    1. **Olfactory Loss (Hyposmia):** Present in ~90% of early cases (UPSIT assessment).
    2. **REM Sleep Behavior Disorder (RBD):** Loss of muscle atonia during dreams; >70% 10-year conversion rate.
    3. **Acoustic Dysphonia:** Vocal cord hypokinesia causes micro-jitter and reduced pitch variability.
    4. **Subtle Gait & Motor Dynamics:** Cadence shifts, stride time variability, and subtle tapping delays.
    5. **Retinal Microvascular Architecture:** Retinal ganglion cell degeneration and microvascular thinning visible in fundus photographs.
  - **The Core Dilemma:** No single symptom is specific on its own (hyposmia occurs in sinus infections; sleep apnea mimics RBD).
- **Visuals:** 5-segment circular biological diagram illustrating the cross-organ prodromal markers.
- **Speaker Timing:** 1.5 minutes.
- **Key Talking Point:** Explain why combining orthogonal biological markers provides a far more trustworthy early signal than relying on any isolated test.

---

### Slide 4: Project Motivation & Objectives
- **Headline:** Multimodal Fusion for Non-Specialist Screening
- **Key Bullet Points:**
  - **Why Multimodal?** Capitalize on physiological orthogonality; robust risk estimation despite noise.
  - **Why Prodromal Focus?** Target the exact window required for future disease-modifying neuroprotection.
  - **Why Non-Specialist Infrastructure?** Movement disorder specialists have 6-month waitlists; optometry clinics and smartphones offer broad community reach.
  - **Core Engineering Objectives:**
    1. Build dedicated feature pipelines for all 5 modalities.
    2. Engineer a Gated Multimodal Fusion network that handles missing modalities without penalty.
    3. Integrate transparent post-hoc explainability (SHAP).
    4. Deploy an end-to-end full-stack prototype (FastAPI + React Dashboard).
    5. Extend to longitudinal mobile digital biomarkers via an adapter.
- **Visuals:** Target deployment funnel: Community Optometrist / Primary Care / Smartphone $\rightarrow$ Risk Screening $\rightarrow$ Specialist Referral.
- **Speaker Timing:** 1.5 minutes.
- **Key Talking Point:** Emphasize the translational screening funnel—triaging at-risk individuals to scarce specialists earlier.

---

### Slide 5: Defensible Novelty Claim
- **Headline:** Scientific Novelty & Boundary Framing
- **Defensible Novelty Statement:**
  > *"Our defensible novelty is the fusion of retinal biomarkers with prodromal digital biomarkers — RBD screening, olfactory testing, voice, and motor/gait — inside a single multimodal model. This specific combination was not found integrated in the current literature. Additionally, we propose a deployment pathway through non-specialist screening infrastructure, such as optometry practices and smartphone-based tasks."*
- **Comparison Table:**
  | Dimension | Typical Existing Literature | MPF-PD System |
  | :--- | :--- | :--- |
  | **Disease Stage** | Manifest PD (Post-diagnosis) | **Prodromal (Pre-motor diagnosis)** |
  | **Modalities** | Voice + Gait only | **Retinal + Olfactory + RBD + Voice + Gait** |
  | **Missing Data** | Drops record / Mean imputation | **Dynamic Neural Attention Gating** |
  | **Deployment Target** | Academic Neurology Center | **Community Screening / Optometry / Mobile** |
- **What We Do NOT Claim:** We do not claim clinical validation, we do not claim to diagnose disease, and we do not claim smartphones take retinal scans.
- **Speaker Timing:** 1.5 minutes.
- **Key Talking Point:** Clearly establish our research contribution without overstepping into unsubstantiated clinical claims.

---

### Slide 6: End-to-End System Architecture
- **Headline:** Pipeline Architecture & Data Flow
- **Key Bullet Points:**
  - Strict unidirectional data flow from raw inputs to dashboard visualization.
  - Multi-stage hierarchy:
    1. Input Ingestion (File uploads & questionnaire forms).
    2. Preprocessing & Quality Verification (Audio SNR filtering, image contrast).
    3. Modality-Specific Feature Extractors.
    4. Gated Neural Fusion Encoder (PyTorch).
    5. Calibrated Risk Classifier (XGBoost).
    6. Explainability Decomposition (SHAP TreeExplainer).
    7. User Interface (React 18 + Tailwind CSS).
- **Visuals:** Comprehensive system architecture diagram matching `PROJECT_ARCHITECTURE.md`.
- **Speaker Timing:** 1.5 minutes.
- **Key Talking Point:** Walk the panel through the flow of data, pointing out how modularity allows each modality to be upgraded independently.

---

### Slide 7: Modality Engineering Deep Dive
- **Headline:** Feature Engineering Across Five Modalities
- **Modality Breakdown:**
  - **Olfactory:** 40-item UPSIT $\rightarrow$ Age/Sex demographic stratification $\rightarrow$ 4D feature vector (total score, normative percentile, hyposmia class, error entropy).
  - **RBD Sleep:** 13-item RBDSQ $\rightarrow$ Clinical thresholding ($\ge 5$) + dream/motor subscales (3D).
  - **Voice:** Sustained /a/ phonation $\rightarrow$ Praat/librosa $\rightarrow$ 16D acoustic vector (jitter local, shimmer local, HNR, PPE, RPDE, MFCCs).
  - **Motor / Gait:** Stride force sensors / IMU $\rightarrow$ 6D biomechanical vector (cadence, stride variability, stance/swing ratio, tremor spectral power).
  - **Retina:** 45° Fundus photo $\rightarrow$ PyTorch U-Net vessel segmentation $\rightarrow$ 4D vascular morphometry (density, fractal dimension $D_f$, tortuosity, FAZ) + 16D CNN latent embedding.
- **Visuals:** Grid of 5 screenshots/diagrams: segmented retinal vessels, voice waveform spectrogram, gait stride plot, UPSIT scratch card, RBDSQ questionnaire.
- **Speaker Timing:** 2 minutes.
- **Key Talking Point:** Demonstrate domain-specific scientific rigor behind each individual feature pipeline.

---

### Slide 8: Gated Multimodal Fusion & Missing Data Strategy
- **Headline:** Handling Incomplete Real-World Screening Data
- **The Challenge:** In real-world clinics, participants rarely have all 5 tests completed.
- **Our Mathematical Solution:**
  - Each modality $i$ produces embedding $h_i$ and binary presence flag $m_i \in \{0, 1\}$.
  - Dynamic Attention Gate: $g_i = \sigma(W_g h_i + b_g)$.
  - Masked Softmax Attention:
    $$\alpha_i = \frac{m_i \cdot \exp(g_i)}{\sum_{j=1}^5 m_j \cdot \exp(g_j) + \epsilon}$$
  - Fused representation: $H_{fused} = \bigoplus_{i=1}^5 [\alpha_i \cdot h_i, m_i]$.
- **Graceful Degradation Guarantee:** When a modality is missing, its gate is zeroed, and attention is smoothly redistributed across available modalities. Participants are **never penalized** for missing tests.
- **Visuals:** Block diagram showing the gated neural network with active and masked pathways.
- **Speaker Timing:** 2 minutes.
- **Key Talking Point:** Highlight that this gating mechanism is what makes the system practically deployable in heterogeneous community settings.

---

### Slide 9: Transparent Explainability Layer (SHAP)
- **Headline:** Opening the Black Box with Exact Shapley Values
- **Key Bullet Points:**
  - Machine learning in healthcare cannot be a black box; clinicians require justification.
  - Employed **SHAP TreeExplainer** on the 45-dimensional fused representation:
    - **Global Importance:** Quantifies which modalities contribute most across the population (RBD and Olfactory act as primary anchors, supplemented by Motor and Voice).
    - **Local Attribution:** Decomposes an individual's risk score into specific positive and negative drivers (e.g. UPSIT score of 18 added +0.31 to risk; normal gait cadence subtracted -0.08).
    - **Missingness Transparency:** Explicitly displays the mathematical impact of absent inputs.
- **Visuals:** Screenshot of the SHAP waterfall feature attribution chart directly from the React dashboard.
- **Speaker Timing:** 1.5 minutes.
- **Key Talking Point:** Show how SHAP bridges the gap between complex gradient-boosted trees and clinical interpretability.

---

### Slide 10: Full-Stack Implementation & Mobile Extension
- **Headline:** Production Architecture & Longitudinal Mobile Extension
- **System Stack:**
  - **Backend:** FastAPI (asynchronous ASGI), Pydantic v2 schemas, automated temporary file scrubbing.
  - **Frontend:** React 18, TypeScript, Tailwind CSS, Vite, Recharts dynamic visualization.
  - **Database:** Supabase PostgreSQL with Row-Level Security (RLS) and HIPAA/GDPR audit trails.
- **Mobile Digital Extension (`MPFAdapter`):**
  - Collects daily longitudinal smartphone metrics (keystroke dynamics, tap rate, vocal stability, sleep proxy).
  - Aggregates daily logs into rolling 14-day Z-scores against the user's personal baseline.
  - Maps to the **frozen** MPF model input—**no risky retraining on mobile devices**.
- **Visuals:** Architecture diagram connecting the mobile phone, Supabase cloud, FastAPI backend, and desktop React dashboard.
- **Speaker Timing:** 1.5 minutes.
- **Key Talking Point:** Emphasize the separation of concerns: continuous daily mobile monitoring feeds into a stable, frozen screening model via an audited adapter.

---

### Slide 11: Datasets, Provenance & Scientific Integrity
- **Headline:** Honest Data Governance & Scientific Provenance
- **Dataset Inventory:**
  - **PPMI (Category A):** Formal clinical reference for olfactory and RBD protocols (DUA protocol defined).
  - **UCI Voice (Category B):** 5,875 sustained vowel phonation samples.
  - **PhysioNet Gait (Category B):** 166 subjects (93 PD, 73 Controls) with vertical ground force data.
  - **DRIVE / STARE / EyePACS (Category C):** Retinal fundus datasets for vessel segmentation pretraining (**No PD labels**).
  - **Synthetic Multimodal Aligned Fixture (Category E):** N=350 aligned synthetic participants for end-to-end prototype verification.
- **Mandatory Statement:**
  > *"Because synchronized 5-modality human datasets are not publicly distributed in open repositories, all fusion metrics were derived on literature-calibrated synthetic fixtures. We evaluate software correctness, not clinical efficacy."*
- **Visuals:** Data provenance taxonomy table displaying Categories A through E.
- **Speaker Timing:** 1.5 minutes.
- **Key Talking Point:** Direct, upfront honesty about data origins will win the respect of any rigorous academic evaluation panel.

---

### Slide 12: Experimental Results & Comparative Benchmarks
- **Headline:** Architectural Verification & Benchmark Metrics
- **Individual Modality Test Split Performance (N=53):**
  - Olfactory Model: F1 = **0.943** | ROC-AUC = **0.994**
  - RBD Sleep Model: F1 = **0.931** | ROC-AUC = **0.994**
  - Voice Model: F1 = **0.844** | ROC-AUC = **0.979**
  - Motor / Gait Model: F1 = **0.857** | ROC-AUC = **0.987**
- **Fusion Comparison & Calibration:**
  - Gated Multimodal Fusion: F1 = **1.000**, ROC-AUC = **1.000**, **Brier Score = 0.0031**
  - Feature Concatenation: ROC-AUC = 1.000, Brier Score = 0.0042
  - Weighted Average Baseline: ROC-AUC = 1.000, Brier Score = 0.0125
  - *Key Takeaway:* Gated Fusion achieves **superior probability calibration (lowest Brier score)**.
- **Missing Modality Graceful Degradation:**
  - Full 5 Modalities: ROC-AUC = 1.000 | F1 = 0.981
  - Missing Retina + Voice (3 Modalities): ROC-AUC = 1.000 | F1 = 0.941
  - Single Modality Only (Olfactory): ROC-AUC = 0.978 (Zero crashes).
- **Visuals:** Calibration curves (Reliability diagram) and Missing Modality degradation line chart.
- **Speaker Timing:** 2 minutes.
- **Key Talking Point:** Highlight that calibration (Brier score) and robust handling of missing modalities are the true technical achievements of the fusion layer.

---

### Slide 13: Software Engineering Rigor & Leakage Audit
- **Headline:** Code Quality, Determinism & Zero Data Leakage
- **Key Engineering Achievements:**
  - **238+ Automated Test Assertions:** Pytest suite testing pipeline robustness, mathematical edge cases, and API routes.
  - **Automated Data Leakage Audit (`evaluation/leakage_report.json`):**
    - Subject Disjointness: **PASSED** (0 overlapping participant IDs between train/val/test).
    - Image & Audio Duplication: **PASSED** (0 duplicate biometric files across splits).
    - Preprocessor Fitting: **PASSED** (Scalers/imputers fitted exclusively on `df_train`).
  - **Deterministic Seeding:** Global seed (`seed=42`) across NumPy, PyTorch, Scikit-Learn.
  - **Robustness Against Corrupted Inputs:** Clamps out-of-bounds scores (e.g. UPSIT=999) safely with warnings; zero unhandled runtime crashes.
- **Visuals:** Screenshot of Pytest execution showing green test suite results.
- **Speaker Timing:** 1 minute.
- **Key Talking Point:** Show that this is not just an ML experiment, but an engineered, test-driven software system.

---

### Slide 14: Limitations & Ethical Governance
- **Headline:** Honest Scientific Limitations & Ethical Controls
- **Explicit Limitations:**
  1. Prototype simulation data; no real-world clinical trial validation.
  2. Public fundus datasets lack confirmed Parkinson's labels.
  3. Digital biomarkers are behavioral proxies, not clinical motor ratings.
  4. Demographic calibration across diverse racial backgrounds is required.
  5. Post-hoc SHAP reflects mathematical correlation, not direct biological causation.
- **Privacy & Ethical Safeguards:**
  - Zero raw biometric media retention on backend (immediate scrub).
  - Purely pseudonymous IDs; zero patient PII ingested.
  - Granular user consent tracking with automated GDPR-style data deletion.
- **Visuals:** Privacy architecture diagram highlighting temporary memory cleanup and user consent revocation.
- **Speaker Timing:** 1.5 minutes.
- **Key Talking Point:** Address potential criticisms proactively before the panel even asks them.

---

### Slide 15: Future Work & Clinical Translation
- **Headline:** Roadmap Toward Clinical Decision Support
- **Key Future Milestones:**
  1. **Prospective Clinical Cohort:** Ingest verified PPMI datasets under institutional DUA and partner with university clinics for multi-year prospective validation.
  2. **Optical Coherence Tomography (OCT):** Transition from 2D fundus photography to cross-sectional OCT to measure macular ganglion cell-inner plexiform layer (GCIPL) thinning.
  3. **Survival & Time-to-Phenoconversion Modeling:** Extend binary classification into longitudinal Cox hazard models predicting *years until motor onset*.
  4. **Genomic & Fluid Biomarkers:** Incorporate LRRK2/GBA genetic variants and plasma phosphorylated tau / alpha-synuclein seed amplification assays.
  5. **Regulatory SaMD Submission:** Formal software verification for FDA 510(k) or CE-mark clinical decision-support certification.
- **Visuals:** 5-year translational research timeline diagram.
- **Speaker Timing:** 1 minute.
- **Key Talking Point:** Outline a realistic, scientifically grounded path forward from prototype to healthcare impact.

---

### Slide 16: Conclusion & Open Floor for Questions
- **Headline:** Summary of Contributions & Q&A
- **Summary Takeaways:**
  - Built an end-to-end, 5-modality prodromal risk screening framework.
  - Implemented dynamic neural attention gating for penalty-free missing modality handling.
  - Provided transparent local SHAP explainability on every prediction.
  - Delivered a production-grade FastAPI backend, React dashboard, and mobile collection adapter.
  - Backed by rigorous test-driven validation, zero data leakage, and honest scientific framing.
- **Closing Safety Statement:**
  > *"MPF-PD is a research prototype designed to explore early prodromal risk patterns. It is not a clinical diagnostic device. Thank you for your time and guidance."*
- **Visuals:** Contact details, GitHub repository link, and invitation for questions.
- **Speaker Timing:** 30 seconds (transition to Viva / Q&A).

---
*End of Slide Deck Outline.*
