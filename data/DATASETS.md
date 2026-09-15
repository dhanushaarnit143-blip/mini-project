# MPF-PD Dataset Research & Data Engineering Specification

## 1. Executive Summary & Core Scientific Principles

The **Multimodal Prodromal Framework for Parkinson’s Disease (MPF-PD)** investigates early-stage multimodal risk estimation across five physiological windows:
1. **Olfactory Dysfunction** (UPSIT / CC-SIT)
2. **REM Sleep Behavior Disorder (RBD)** (RBDSQ)
3. **Voice Dysphonia** (sustained phonation acoustic features)
4. **Motor / Gait Dynamics** (bilateral ground reaction force sensors / finger tapping)
5. **Retinal Microvasculature & Morphology** (fundus photography / OCT RNFL thickness)

### Non-Negotiable Scientific Integrity Rules

> [!IMPORTANT]
> ### 1. Zero Data Fabrication Rule
> **Under no circumstances is real clinical data fabricated, hallucinated, or synthesized to mimic real patient records.**  
> When credentialed access or physical files for restricted clinical cohorts (e.g. PPMI, PREDICT-PD, mPower) are not locally present on disk, the system marks their status as `restricted` and falls back explicitly to **Category E (Synthetic Test Fixtures)**. Synthetic fixtures carry **zero clinical validity** and are strictly reserved for CI/CD, pipeline verification, and unit tests.

> [!CAUTION]
> ### 2. Zero Cross-Cohort Merging Rule (Anti-Stitching Mandate)
> **Merging unrelated datasets into a fake same-participant multimodal cohort is strictly prohibited.**  
> For example: stitching speech recordings from UCI Voice (42 UK/US subjects) with gait force records from PhysioNet (166 Israeli subjects) using arbitrary index joins creates fabricated cross-modal correlation structures. Such artificial stitching violates physiological causality, renders biomarker fusion meaningless, and invalidates scientific peer review. Cross-modal fusion models are trained and evaluated **strictly on true same-participant cohorts** (Category A: PPMI).

---

## 2. Dataset Classification Taxonomy

Every dataset in the MPF-PD project belongs to exactly one of five distinct categories:

| Category | Category Name | Description | Datasets | Role in MPF-PD |
| :---: | :--- | :--- | :--- | :--- |
| **A** | **Same-Participant Multimodal Data** | True longitudinal or cross-sectional cohorts where all recorded modalities originate from the exact same human participants. | `ppmi`, `mpower` | Primary multimodal fusion training, cross-modal attention calibration, and longitudinal evaluation. |
| **B** | **Modality-Specific Datasets** | Datasets capturing a single physiological modality with clinical disease or motor severity labels. | `uci_voice`, `physionet_gait` | Standalone modality encoder pretraining, feature extraction tuning, and single-branch baselines. |
| **C** | **Pretraining Datasets** | Large-scale biomedical or imaging repositories containing relevant anatomical structures but **NO Parkinson’s disease clinical labels**. | `retinal_fundus_pretraining`, `oct500` | Self-supervised / supervised vision backbone pretraining (vessel segmentation, RNFL layer extraction). **Must never be reported as PD datasets.** |
| **D** | **External Validation Datasets** | Independent cohorts with prodromal or screening assessments used strictly to evaluate out-of-distribution generalization. | `predict_pd` | Held-out external validation of risk scoring models; never merged into training splits. |
| **E** | **Synthetic Test Fixtures** | Artificially generated numerical matrices designed to verify software pipeline mechanics, missingness handling, and API functionality. | `synthetic_fixture` | Continuous integration, unit testing, and software verification in `prototype_simulation` mode. |

---

## 3. Comprehensive Dataset Summary Table

| Dataset ID | Category | Name | Source | Access Requirements | License | Participants | Labels | Modalities | File Format | Missing Data | Main Limitations |
| :--- | :---: | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ppmi` | **A** | Parkinson's Progression Markers Initiative | MJFF / LONI Image Data Archive | Registration + DUA | PPMI DUA | 4,000+ | PD: ~1,500<br>Prodromal: ~600<br>Control: ~800 | Olfactory, RBD, Motor, Voice, Imaging, Biospecimens | CSV, Parquet, DICOM, NIfTI | Longitudinal attrition, optional sub-study gaps | Complex schema evolution; restricted bio-assays (SAA) |
| `mpower` | **A** | Parkinson Disease Mobile Data Study | Sage Bionetworks / Synapse | Synapse account + ethics cert | Synapse Qualified Researcher | 10,000+ | PD: ~3,000<br>Control: ~7,000 | Voice, Gait, Tapping, Memory | CSV, JSON, m4a | Severe longitudinal dropout (>80% by week 2) | Self-reported diagnosis; uncontrolled smartphone hardware |
| `uci_voice` | **B** | UCI Parkinson's Telemonitoring Dataset | UCI ML Repository / Oxford | Open Access | CC BY 4.0 | 42 | PD: 42 (motor & total UPDRS continuous) | Voice / Speech Dysphonia | CSV | Low feature missingness; uneven visit spacing | No healthy controls; small participant cohort (N=42) |
| `physionet_gait` | **B** | Gait in Parkinson's Disease | PhysioNet / Tel-Aviv SMC | Open Access | ODC-By v1.0 | 166 | PD: 93<br>Control: 73 | Motor / Gait VGRF Force Sensors | TXT, CSV | Minimal sensor frame dropouts | Short 2-minute lab trials; no non-motor/prodromal labels |
| `retinal_fundus_pretraining` | **C** | Retinal Fundus Pretraining Corpus | EyePACS / DRIVE / Messidor-2 / APTOS | Kaggle / Competition Agreement | CC-BY-NC / Academic | 40,000+ | Diabetic Retinopathy (0-4); **NO PD LABELS** | Retinal Fundus Photography | JPEG, PNG, TIFF | Illumination artifacts, varying camera fields | **Zero PD labels**; strictly for morphological vision pretraining |
| `oct500` | **C** | OCT500 Retinal Tomography Dataset | Nanjing Univ / IEEE DataPort | Academic registration | Academic Non-Commercial | 500 | AMD, DR, CNV, Normal; **NO PD LABELS** | Retinal 3D OCT & 2D OCTA | MAT, NIfTI, PNG | Low SNR in deep choroidal scans | **Zero PD labels**; small sample size (N=500 volumes) |
| `predict_pd` | **D** | PREDICT-PD Study Cohort | QMUL / UCL | Formal PI proposal + ethics | Institutional DTA | 10,000+ | Risk Tiers (High/Med/Low) + Incident PD | Olfactory, RBD, Tapping, Non-motor | CSV, Tabular | Online self-report survey attrition | Restricted institutional access; noisy web keyboard tapping |
| `synthetic_fixture` | **E** | MPF-PD Synthetic Test Fixture | MPF-PD Pipeline Generator | None (Internal) | MIT License | 100 | Mock Control (35), Prodromal (30), PD (35) | Olfactory, RBD, Motor, Voice, Retina | CSV, Parquet | Programmatically inserted (10% per column) | **Completely artificial**; carry zero clinical or biological validity |

---

## 4. Detailed Dataset Cards

### Card 1: PPMI (Parkinson’s Progression Markers Initiative)
- **Name:** Parkinson's Progression Markers Initiative (PPMI)
- **Source:** Michael J. Fox Foundation for Parkinson’s Research / LONI Image Data Archive ([https://www.ppmi-info.org](https://www.ppmi-info.org))
- **Access Requirements:** User account registration, submission of formal research plan, compliance review, and institutional execution of the PPMI Data Use Agreement (DUA).
- **License:** PPMI Specific Data Use Agreement (restricted non-commercial / approved commercial research use).
- **Participants:** ~4,000+ total enrolled human participants across worldwide clinical sites (de novo PD, healthy controls, prodromal individuals with hyposmia or RBD, and genetic cohorts carrying LRRK2, GBA, or SNCA variants).
- **Labels:** 
  - De Novo & Genetic Parkinson's Disease: ~1,500
  - Prodromal Cohort (isolated RBD, hyposmia, or high genetic penetrance): ~600
  - Healthy Controls: ~800
  - Scans Without Evidence of Dopaminergic Deficit (SWEDD): ~300
  - Longitudinal conversion tracking: incident clinical motor conversion from prodromal to manifest PD.
- **Modalities:** 
  1. Olfactory (UPSIT 40-item smell identification test)
  2. Sleep / RBD (RBDSQ, SCOPA-SLEEP, Epworth Sleepiness Scale)
  3. Motor / Gait (MDS-UPDRS Part III motor examination, timed 10m walk)
  4. Voice / Speech (sustained phonation /a/ recordings from mobile sub-studies)
  5. Imaging & Biospecimens (DaTscan SPECT SBR, 3T MRI, CSF $\alpha$-synuclein SAA, plasma neurofilament light chain)
- **Variables:** `PATNO` (Subject identifier), `EVENT_ID` (visit code, BL to V18), `UPSIT_TOTAL`, `RBDSQ_TOTAL`, `NP3TOT`, `DATSCAN_CAUDATE_R`, `DATSCAN_PUTAMEN_R`, `DIAGNOSIS`.
- **File Format:** CSV, Parquet, DICOM (raw SPECT/MRI), NIfTI.
- **Missing Data:** Longitudinal participant attrition, elective digital sub-study participation resulting in non-uniform audio availability, missing visit intervals.
- **Limitations:** Complex schema changes across annual curate data freezes; high computational storage for neuroimaging; sequestered biomarker assays (e.g., SAA seed amplification assays) require secondary approvals.
- **Category:** **Category A (Same-Participant Multimodal Data)**.

---

### Card 2: Sage Bionetworks mPower Mobile Dataset
- **Name:** Parkinson Disease Mobile Data Study (mPower)
- **Source:** Sage Bionetworks / Synapse Platform ([https://www.synapse.org/#!Synapse:syn4993293](https://www.synapse.org/#!Synapse:syn4993293))
- **Access Requirements:** Synapse account registration, certified training in human subjects research ethics, submission and institutional approval of a Data Access Request.
- **License:** Synapse Qualified Researcher Governance Terms.
- **Participants:** ~10,000+ smartphone application contributors worldwide.
- **Labels:** 
  - Self-reported clinical diagnosis of Parkinson's Disease: ~3,000 participants
  - Self-reported Healthy Controls: ~7,000 participants
  - Dynamic medication state: self-reported timing relative to dopaminergic medication (`Immediately before`, `After medication`, `No medication`).
- **Modalities:** 
  1. Voice / Phonation (sustained vowel /a/ recorded via mobile microphone)
  2. Motor / Gait (30-second walking and 30-second standing rest using 3-axis accelerometer and gyroscope)
  3. Motor / Tapping (alternating two-finger screen tapping speed and spatial interval)
  4. Cognitive / Memory (spatial memory game scores)
- **Variables:** `recordId`, `healthCode`, `createdOn`, `medTimepoint`, `accel_walking_outbound.json.items`, `tapping_results.json`, `audio_countdown.m4a`.
- **File Format:** CSV (metadata tables), JSON (sensor time-series arrays), m4a (audio).
- **Missing Data:** High participant dropout (>80% attrition after day 14); irregular micro-task engagement; bursty sampling intervals.
- **Limitations:** Unverified self-reported diagnosis introduces significant label noise; uncontrolled smartphone hardware variability across Android and iOS sensors; acoustic noise in unshielded ambient home recording environments.
- **Category:** **Category A (Same-Participant Multimodal Data)**.

---

### Card 3: UCI Parkinson’s Telemonitoring Dataset
- **Name:** UCI Parkinson's Telemonitoring Dataset (Little et al. / Tsanas et al.)
- **Source:** UCI Machine Learning Repository / University of Oxford ([https://archive.ics.uci.edu/dataset/189/parkinsons+telemonitoring](https://archive.ics.uci.edu/dataset/189/parkinsons+telemonitoring))
- **Access Requirements:** None (Open Access public download).
- **License:** Creative Commons Attribution 4.0 International (CC BY 4.0).
- **Participants:** 42 early-stage, non-demented Parkinson's disease patients monitored at home over a 6-month period.
- **Labels:** Continuous clinician-assessed motor impairment severity:
  - `motor_UPDRS`: range 5.0 to 40.0
  - `total_UPDRS`: range 7.0 to 55.0
  - **No healthy control group** is present in this telemonitoring collection.
- **Modalities:** Acoustic speech and voice micro-perturbation metrics.
- **Variables:** `subject#`, `age`, `sex`, `test_time`, `motor_UPDRS`, `total_UPDRS`, `Jitter(%)`, `Jitter(Abs)`, `Jitter:RAP`, `Jitter:PPQ5`, `Jitter:DDP`, `Shimmer`, `Shimmer(dB)`, `Shimmer:APQ3`, `Shimmer:APQ5`, `Shimmer:APQ11`, `Shimmer:DDA`, `NHR`, `HNR`, `RPDE`, `DFA`, `PPE`.
- **File Format:** CSV.
- **Missing Data:** Negligible missingness in tabular extracted features; variable numbers of voice recordings per participant across the 6-month window (range: 100 to 200 per subject).
- **Limitations:** Cohort is restricted to 42 individuals; zero healthy controls (cannot be used for binary diagnosis classification without pairing, which violates cross-cohort merging rules); voice modality only.
- **Category:** **Category B (Modality-Specific Datasets)**.

---

### Card 4: PhysioNet Gait in Parkinson’s Disease
- **Name:** Gait in Parkinson's Disease (Goldberger et al. / Hausdorff et al.)
- **Source:** PhysioNet / Tel-Aviv Sourasky Medical Center ([https://doi.org/10.13026/C24H3N](https://doi.org/10.13026/C24H3N))
- **Access Requirements:** None (Open Access with standard scholarly citation).
- **License:** Open Data Commons Attribution License (ODC-By) v1.0.
- **Participants:** 166 total human subjects (93 diagnosed PD patients, 73 age-matched healthy controls) compiled across three sub-investigations (Ga, Ju, Si).
- **Labels:** 
  - Parkinson's Disease: 93 patients
  - Healthy Controls: 73 participants
  - Severity indices: Hoehn & Yahr staging (1 to 3), UPDRS Part III motor scores, baseline gait speed (m/s).
- **Modalities:** Bilateral foot force dynamics captured by 16 vertical ground reaction force (VGRF) pressure sensors (8 under each foot) sampled at 100 Hz during level walking.
- **Variables:** `Time` (s), `L1` through `L8` (force in Newtons on left foot sensors), `R1` through `R8` (force in Newtons on right foot sensors), `Total_Force_Left`, `Total_Force_Right`.
- **File Format:** ASCII text files (`.txt`), CSV.
- **Missing Data:** Highly uniform 2-minute steady walking recordings; sensor dropouts are extremely rare (<0.1% of frames).
- **Limitations:** Data collection was conducted under controlled straight-line laboratory walking conditions; lacks ambulatory turn or free-living gait variations; no non-motor (olfactory, sleep, retinal) data.
- **Category:** **Category B (Modality-Specific Datasets)**.

---

### Card 5: Retinal Fundus Pretraining Corpus (EyePACS / Messidor-2 / DRIVE / APTOS)
- **Name:** Retinal Fundus Pretraining Corpus (EyePACS / Messidor-2 / DRIVE / APTOS 2019)
- **Source:** Kaggle / Grand-Challenge.org / DRiDB ([https://www.kaggle.com/c/diabetic-retinopathy-detection](https://www.kaggle.com/c/diabetic-retinopathy-detection))
- **Access Requirements:** Kaggle user account and competition terms acceptance.
- **License:** Custom Academic / CC-BY-NC 4.0 Non-Commercial.
- **Participants:** ~40,000+ clinical ophthalmology patients (~88,000 fundus images).
- **Labels:** Diabetic Retinopathy Grade (0: No DR, 1: Mild, 2: Moderate, 3: Severe, 4: Proliferative), optic disc and vessel segmentation binary masks.
  - **CONTAINS ZERO PARKINSON'S DISEASE LABELS.**
- **Modalities:** High-resolution digital color fundus photography (CFP).
- **Variables:** `image_id`, `patient_id`, `eye` (left/right), `dr_grade`, `vessel_mask`.
- **File Format:** JPEG, PNG, TIFF.
- **Missing Data:** Variable image quality, non-uniform resolution (from $400 \times 400$ up to $3000 \times 3000$), uneven illumination, media opacities (cataracts).
- **Limitations:** **Contains NO neurodegenerative or Parkinson's disease labels.** This dataset must NEVER be described as a Parkinson's disease dataset. It is utilized strictly to train vision models (e.g., U-Net for vessel segmentation, ResNet/ViT for feature extraction) before transferring embeddings to neurological cohorts.
- **Category:** **Category C (Pretraining Datasets)**.

---

### Card 6: OCT500 Retinal Optical Coherence Tomography Dataset
- **Name:** OCT500 Retinal Optical Coherence Tomography Dataset
- **Source:** Nanjing University of Science and Technology / IEEE DataPort ([https://mmlab.eecs.umich.edu/oct500/](https://mmlab.eecs.umich.edu/oct500/))
- **Access Requirements:** Academic institution email verification and non-commercial end-user agreement.
- **License:** Academic Non-Commercial License.
- **Participants:** 500 human eyes / subjects.
- **Labels:** Retinal and macular pathology annotations (Age-related Macular Degeneration [AMD], Diabetic Retinopathy [DR], Choroidal Neovascularization [CNV], Normal control eyes).
  - **CONTAINS ZERO PARKINSON'S DISEASE LABELS.**
- **Modalities:** 3D spectral-domain OCT volumes ($6 \times 6\text{ mm}$ and $3 \times 3\text{ mm}$ FOV), 2D OCT-Angiography (OCTA) superficial/deep projection maps, 6-layer retinal tissue segmentations.
- **Variables:** `subject_id`, `oct_volume`, `foveal_thickness`, `retinal_nerve_fiber_layer_mask` (RNFL), `ganglion_cell_layer_mask` (GCL).
- **File Format:** MAT (`.mat`), NIfTI (`.nii.gz`), PNG.
- **Missing Data:** Lower signal-to-noise ratio in peripheral B-scans; speckle noise artifacts.
- **Limitations:** Small cohort size (N=500); zero Parkinson's clinical status; restricted strictly to anatomical retinal layer segmenter pretraining.
- **Category:** **Category C (Pretraining Datasets)**.

---

### Card 7: PREDICT-PD Study Cohort
- **Name:** PREDICT-PD Study Cohort
- **Source:** Queen Mary University of London (QMUL) & University College London (UCL) ([https://www.predictpd.com](https://www.predictpd.com))
- **Access Requirements:** Formal collaboration request to Principal Investigators (`predictpd@qmul.ac.uk`) and institutional health research ethics committee approval.
- **License:** Institutional Data Transfer Agreement (DTA).
- **Participants:** ~10,000 enrolled general-population individuals aged 60–80 across the United Kingdom.
- **Labels:** 
  - Risk Stratification Tiers: High Risk (top 5% predicted prodromal risk), Intermediate Risk (next 15%), Low Risk / Controls (remaining 80%).
  - Longitudinal motor conversion: clinical diagnosis of manifest Parkinson's disease tracked through UK NHS electronic health records.
- **Modalities:** 
  1. Olfactory (UPSIT / online smell identification test)
  2. REM Sleep Behavior Disorder (RBDSQ questionnaire)
  3. Motor (browser-based alternating keyboard finger-tapping test)
  4. Non-motor risk factors (family history, mood, constipation, caffeine/smoking habits)
- **Variables:** `participant_id`, `upsit_score`, `kbd_tapping_speed`, `rbd_score`, `pd_risk_tier`, `incident_pd_conversion`.
- **File Format:** CSV, Tabular.
- **Missing Data:** Annual online questionnaire non-response; differential loss to follow-up over 5+ years.
- **Limitations:** Restricted access requiring institutional ethics agreements; remote self-administered finger-tapping is less sensitive than in-clinic force sensors.
- **Category:** **Category D (External Validation Datasets)**.

---

### Card 8: MPF-PD Synthetic Test Fixture
- **Name:** MPF-PD Synthetic Test Fixture
- **Source:** MPF-PD Internal Data Pipeline Generator (`src/data/synthetic_fixture.py`)
- **Access Requirements:** None (bundled open-source test fixture).
- **License:** MIT License.
- **Participants:** 100 artificially generated mock participants (`P0001` through `P0100`).
- **Labels:** 
  - Mock Healthy Control: 35
  - Mock Prodromal: 30
  - Mock Parkinson's Disease: 35
  - **Zero clinical validity; strictly artificial integer classes (0, 1, 2).**
- **Modalities:** Fully aligned 5-modality synthetic feature vectors:
  1. Olfactory (`upsit_score`, range: 10–40)
  2. RBD Sleep (`rbd_score`, range: 0–13)
  3. Motor / Gait (`updrs_motor`, range: 0–60)
  4. Voice / Speech (`voice_pitch_sd`, `voice_jitter_pct`)
  5. Retinal (`retinal_rnfl_thickness`, range: 60–120 $\mu\text{m}$)
- **Variables:** `participant_id`, `upsit_score`, `rbd_score`, `updrs_motor`, `voice_pitch_sd`, `retinal_rnfl_thickness`, `diagnosis`.
- **File Format:** CSV, Parquet (`tests/fixtures/synthetic_fixture.csv`).
- **Missing Data:** Controlled 10% random missingness inserted across non-critical columns to evaluate missing-modality masking and dynamic gating algorithms.
- **Limitations:** Purely mathematical fixture generated by parameterized random distributions. Must NEVER be cited or reported as empirical biomedical evidence.
- **Category:** **Category E (Synthetic Test Fixtures)**.

---

## 5. Dataset Engineering & Preparation Protocol

### Step 1: Registry Verification
All datasets must have a conforming metadata YAML in `data/metadata/` containing all 18 required schema attributes verified by `src/data/registry.py:validate_dataset_metadata()`.

### Step 2: Zero-Fabrication Local Verification
When dataset loaders in `src/data/loaders.py` are queried:
- If target raw files exist at `local_path`, data is loaded directly into pandas DataFrames.
- If target raw files are absent, the loader raises `DataNotAvailableError` detailing the credentialing URL.
- The pipeline never silently generates synthetic rows under real dataset identifiers.

### Step 3: Integrity Validation Pipeline
Every loaded dataset is passed through `src/data/validators.py`:
- `validate_required_columns()`: verifies presence of all clinical variables.
- `validate_no_duplicate_participants()`: ensures 1:1 participant mapping in cross-sectional tables.
- `validate_label_column()`: enforces discrete allowed classes or valid continuous ranges.
- `validate_missingness()`: flags features exceeding allowable missingness thresholds (default: 50%) without silent imputation.
- `validate_participant_split()`: proves 100% disjoint participant sets across train/validation/test splits (zero data leakage).
- `validate_multimodal_cohort_integrity()`: verifies that multi-modality matrices originate from verified single-subject IDs rather than synthetic cross-dataset stitching.

---

## 6. Access Application & Reproduction Checklist

- [x] Document exhaustive dataset cards across all 5 clinical categories.
- [x] Establish strict anti-fabrication and anti-stitching provenance rules.
- [x] Implement standardized metadata YAMLs in `data/metadata/`.
- [x] Implement schema-enforcing registry in `src/data/registry.py`.
- [x] Implement fail-safe dataset loaders in `src/data/loaders.py`.
- [x] Implement multi-tier validation functions in `src/data/validators.py`.
- [x] Generate comprehensive validation reports in `data/reports/` and `evaluation/`.
- [ ] Submit PPMI Data Use Agreement (DUA) request via LONI portal for research expansion.
- [ ] Download raw PPMI CSV tables into `data/raw/ppmi/`.
