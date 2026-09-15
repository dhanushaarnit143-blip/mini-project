# MPF-PD Datasets & Data Provenance

**Multimodal Prodromal Fusion for Parkinson’s Disease Risk Screening**  
*Investigational Research Prototype — Dataset Specification and Integrity Catalog*

---

> [!IMPORTANT]
> ### CRITICAL PROVENANCE & CLINICAL DISCLAIMER
> - **Zero Fabrication Policy:** All dataset listings and metrics correspond strictly to verifiable files and authorized protocols.
> - **Same-Participant Multimodal Data Notice:** Because fully open, longitudinal cohorts containing all 5 synchronized modalities (retinal imaging, sustained voice recordings, sensor-based gait force time-series, smell test scores, and REM sleep behavior disorder questionnaires) are **not distributed in open public repositories without restricted Data Use Agreements (DUAs)**, active modeling in this prototype utilized an aligned **synthetic test fixture (`Category E`)**.
> - **Zero Clinical Validity:** Metrics derived from the synthetic simulation mode have **zero clinical validity** and must **never** be cited as clinical evidence or diagnostic sensitivity.

---

## 1. Dataset Taxonomy & Scientific Integrity Categories

To prevent misleading cross-study claims and maintain strict academic integrity, datasets in MPF-PD are classified into five explicit categories:

| Category Code | Category Name | Description | Regulatory & Scientific Constraint |
| :---: | :--- | :--- | :--- |
| **Category A** | **Same-Participant Multimodal** | Cohorts where multiple biomarker modalities were recorded from the identical participant under unified study protocols. | Mandatory for authentic multimodal cross-correlation learning. Governed by formal institutional DUAs. |
| **Category B** | **Modality-Specific Datasets** | Public cohorts with high-quality recordings for a single modality (e.g., voice only, gait only). | Used for unimodal pretraining, representation validation, or architecture benchmarking. Cannot evaluate cross-modality fusion. |
| **Category C** | **Pretraining / Auxiliary Datasets** | Large public corpora containing high-resolution data (e.g., fundus images, OCT volumes) with non-PD labels (e.g., diabetic retinopathy, glaucoma). | Strictly limited to pretraining feature encoders (e.g. vessel segmenters, CNN backbones). No Parkinson's diagnostic labels. |
| **Category D** | **External Validation Cohorts** | Independent longitudinal or population cohorts used strictly for out-of-distribution generalizability testing. | Evaluated without parameter fine-tuning. Governed by collaborative DTAs. |
| **Category E** | **Synthetic Fixtures / Mock Data** | Open, reproducible synthetic distributions generated from published literature parameters for CI/CD and software testing. | Permitted only for pipeline verification and simulation mode. Strictly zero clinical diagnostic validity. |

---

## 2. Comprehensive Dataset Catalog

The MPF-PD project catalogs 8 primary datasets across the five categories. The table below details their characteristics, access status, and usage in this prototype:

| Dataset ID | Full Study Name | Category | Modalities Covered | Participant Count | Clinical Labels / Targets | License & Access Governance | Intended Use | Prototype Usage Status |
| :--- | :--- | :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| **`ppmi`** | Parkinson's Progression Markers Initiative | **A** | Olfactory (UPSIT), Sleep (RBDSQ), Motor (MDS-UPDRS), Voice, DaTscan, Biofluid | ~4,000+ enrolled | De Novo PD (~1,500), Prodromal (~600), Healthy Controls (~800) | PPMI Data Use Agreement (DUA) via Michael J. Fox Foundation | Primary multimodal training & longitudinal trajectory tracking | Remote / DUA Pending *(Not distributed locally)* |
| **`predict_pd`** | PREDICT-PD UK Population Cohort | **D** (and A) | Olfactory (UPSIT), Sleep (RBDSQ), Finger Tapping, Non-motor survey | ~10,000+ enrolled | Longitudinal incident PD; High-risk vs Low-risk prodromal tiers | Institutional Data Transfer Agreement (Queen Mary University London) | External prospective validation of prodromal risk algorithm | Remote / DTA Pending *(Not distributed locally)* |
| **`mpower`** | Sage Bionetworks mPower Mobile Study | **A / B** | Voice (audio phonation), Motor (gait, balance, tapping), Memory | ~10,000+ smartphone users | Self-reported PD diagnosis vs self-reported control | Synapse Qualified Researcher Governance Terms | Self-supervised pretraining for mobile digital biomarkers | Remote / Synapse Governed *(Not distributed locally)* |
| **`uci_voice`** | UCI Parkinson's Telemonitoring Dataset | **B** | Voice / Speech Acoustics (sustained vowel phonation) | 42 participants (5,875 recordings) | Continuous motor-UPDRS and total-UPDRS (**NO Healthy Controls**) | Creative Commons Attribution 4.0 International (CC BY 4.0) | Modality-specific representation learning and severity tracking | Synthetic Fallback *(Precomputed tabular features supported)* |
| **`physionet_gait`**| Gait in Parkinson's Disease (PhysioNet) | **B** | Motor / Gait (Vertical ground reaction force, 8 sensors/foot) | 166 participants (93 PD, 73 Controls) | Manifest PD vs Healthy Control (Binary) | Open Data Commons Attribution License (ODC-By) v1.0 | Unimodal motor gait stride segmentation & feature extraction | Synthetic Fallback *(Raw 100 Hz VGRF parser implemented)* |
| **`retinal_fundus_pretraining`** | Retinal Fundus Corpus (DRIVE, EyePACS, Messidor-2, APTOS) | **C** | Retinal Fundus Color Photography | ~80,000+ images across cohorts | Diabetic Retinopathy grades, vessel masks (**NO Parkinson's labels**) | Academic Research / Kaggle Competition Terms | Pretraining CNN backbones & validating classical vessel morphometry | Fixture Tested *(Synthetic fundus image fixture active)* |
| **`oct500`** | OCT500 3D Retinal Optical Coherence Tomography | **C** | 3D Retinal OCT and OCT-Angiography volumes | 500 volumes | Retinal pathology (AMD, DR, CNV; **NO Parkinson's labels**) | Academic Non-Commercial End-User Agreement | Pretraining 3D OCT retinal nerve fiber layer (RNFL) encoders | Remote / Restricted *(Not distributed locally)* |
| **`synthetic_fixture`** | MPF-PD Aligned Multimodal Test Fixture | **E** | All 5 Modalities: Olfactory, RBD, Voice, Motor, Retina | 350 simulated participants | Latent Disease Status: 175 Control, 175 Case (simulated) | Open Access / MIT Project License | Software correctness, CI/CD testing, and pipeline simulation | **Active Local Fixture** *(Used in Phases 1–10)* |

---

## 3. Deep-Dive: Dataset Profiles & Modality Breakdown

### 3.1 PPMI (Parkinson's Progression Markers Initiative)
- **Modality Details:**
  - *Olfactory:* University of Pennsylvania Smell Identification Test (UPSIT) 40-item score.
  - *Sleep:* 13-item REM Sleep Behavior Disorder Screening Questionnaire (RBDSQ).
  - *Motor:* MDS-UPDRS Part III motor examination and postural instability scores.
  - *Voice:* Phonation recordings available through specialized acoustic sub-studies.
  - *Imaging:* DaTscan SPECT, structural MRI, and experimental retinal OCT sub-cohorts.
- **Labels:** High-confidence clinical diagnoses categorized as De Novo idiopathic PD, Prodromal (hyposmic or idiopathic RBD subjects with DaTscan deficits), Genetic carriers (LRRK2, GBA), and age-matched Healthy Controls.
- **Missingness Profile:** Longitudinal attrition, visit window non-attendance, optional sub-study participation rates (~20–40% missingness on acoustic and retinal sub-studies).
- **Primary Limitation:** Managed DUA registration and strict scientific committee approval required. Cannot be bundled into public open-source Git repositories.

### 3.2 PREDICT-PD Cohort
- **Modality Details:** Population-level prodromal risk screening via web-based surveys, postal scratch-and-sniff smell tests (UPSIT), and online finger-tapping tasks.
- **Labels:** Incident motor Parkinson's disease tracked longitudinally over 3 to 10 years; stratified baseline risk tiers (top 15% vs general population).
- **Missingness Profile:** Substantial survey drop-off; variable return rate for mailed olfactory testing.
- **Primary Limitation:** Geographically bounded to the UK; raw data requires formal bilateral institutional agreements.

### 3.3 UCI Parkinson's Telemonitoring Dataset (`uci_voice`)
- **Modality Details:** 5,875 recordings of sustained vowel `/a/` phonation across 42 patients over a 6-month home telemonitoring trial. 16 dysphonia parameters: Jitter (5 variants), Shimmer (6 variants), NHR, HNR, RPDE, DFA, and PPE.
- **Labels:** Clinician-scored motor UPDRS (range: 5.0 to 39.5) and total UPDRS (range: 7.0 to 54.5).
- **Critical Limitation:** **Zero healthy controls.** All 42 participants have manifest Parkinson's disease. Using this dataset for binary classification requires binarizing UPDRS scores around the median, which evaluates *disease severity prediction*, not *early risk screening vs healthy individuals*.

### 3.4 PhysioNet Gait in Parkinson's Disease (`physionet_gait`)
- **Modality Details:** Bilateral vertical ground reaction force (VGRF) time-series recorded at 100 Hz using 8 Ultraflex force sensors placed beneath each foot during 2 minutes of level overground walking.
- **Participants:** 93 patients with manifest PD (mean age: 66.3 years; 63% male; Hoehn & Yahr stages 2–3) and 73 age-matched healthy controls (mean age: 66.3 years; 55% male).
- **Labels:** Binary manifest PD vs Healthy Control.
- **Critical Limitation:** Data reflects manifest motor impairment under controlled laboratory conditions. It does not provide prodromal labels or free-living everyday mobility signals.

### 3.5 Retinal Pretraining Corpus (`retinal_fundus_pretraining`)
- **Modality Details:** High-resolution digital fundus photographs (macula- and optic disc-centered) from public ophthalmology benchmarks (DRIVE: N=40; Messidor-2: N=1,748; EyePACS: N=88,702).
- **Labels:** Retinal vascular segmentation ground truth, diabetic retinopathy severity grading (0–4), macular edema presence.
- **Critical Limitation:** **Zero Parkinson's disease labels.** Retinal images from these datasets can only be used to pretrain vessel segmentation networks (U-Net) or self-supervised vascular encoders. They cannot validate Parkinson's screening.

### 3.6 MPF-PD Synthetic Multimodal Fixture (`synthetic_fixture`)
- **Modality Details:** Complete 5-modality synchronized records generated using statistical parameterizations derived from published clinical literature:
  - *Olfactory:* Control mean UPSIT = 34.2 (SD 3.1); Case mean UPSIT = 21.8 (SD 4.5).
  - *RBD:* Control mean RBDSQ = 2.1 (SD 1.4); Case mean RBDSQ = 7.4 (SD 2.2).
  - *Voice:* Elevated jitter, shimmer, and PPE with reduced HNR in simulated cases.
  - *Motor:* Reduced gait speed, cadence, and step regularity in simulated cases.
  - *Retina:* Reduced vessel density and increased FAZ area in simulated cases.
- **Participants:** 350 simulated participants partitioned into 245 train, 52 validation, and 53 test subjects.
- **Missingness Injection:** Controlled realistic missingness rates (Olfactory: 14.6%, RBD: 16.0%, Voice: 28.9%, Motor: 18.6%, Retina: 32.0%).

---

## 4. Dataset Usage Across Project Phases

The table below indicates how each dataset was utilized during the development and evaluation phases:

| Dataset ID | Training | Validation | Pretraining | External Validation | Synthetic Software Test |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `ppmi` | Remote Specification | Remote Specification | No | Planned Phase 12+ | No |
| `predict_pd` | No | No | No | Planned Phase 12+ | No |
| `mpower` | No | No | Remote Design | No | No |
| `uci_voice` | Design Baseline | Design Baseline | Feature Verification | No | Software Fallback |
| `physionet_gait` | Design Baseline | Design Baseline | Signal Pipeline Test | No | Software Fallback |
| `retinal_fundus_pretraining` | No | No | Morphometry Check | No | Software Fallback |
| `oct500` | No | No | Remote Spec | No | No |
| `synthetic_fixture` | **Yes (Phase 6)** | **Yes (Phase 6)** | No | No | **Yes (Phases 1–10)** |

---

## 5. Availability of Same-Participant Multimodal Data

> [!CAUTION]
> ### EXPLICIT STATEMENT ON REAL DATA AVAILABILITY
> In strict adherence to scientific honesty:
> 1. **No authentic same-participant 5-modality clinical dataset was available locally** during Phase 1–10 execution.
> 2. Open-access repositories distribute modality-isolated datasets (e.g. voice alone in UCI, gait alone in PhysioNet, retinal images alone in EyePACS). True multimodal cohorts (such as PPMI) require institutional DUA clearance, identity verification, and multi-week data governance review.
> 3. Consequently, all cross-modality fusion metrics, gate weight distributions, and SHAP interactions reported in this prototype were derived from the **Synthetic Multimodal Fixture (`Category E`)**.
> 4. These results demonstrate **software architecture viability, pipeline resilience, and mathematical correctness**, but have **ZERO clinical diagnostic validity**.
