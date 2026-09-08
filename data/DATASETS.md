# MPF-PD Dataset Research & Data Engineering Specification

## 1. Executive Summary

The **Multimodal Prodromal Framework for Parkinson’s Disease (MPF-PD)** aims to leverage non-invasive and early-stage biomarkers across multiple physiological modalities—including Olfactory, REM Sleep Behavior Disorder (RBD), Speech/Voice, Motor/Gait, and Retinal imaging—to detect prodromal Parkinson’s Disease (PD) prior to manifest motor degeneration.

A critical principle of clinical data engineering for MPF-PD is **dataset provenance and multimodal alignment integrity**. Unrelated datasets collected across non-overlapping participant cohorts (e.g., combining a voice dataset from one study with a gait dataset from another) must **NEVER** be merged into a fake multimodal cohort. Such synthetic merging introduces artificial cross-modal correlations, invalidates causal inference, and violates clinical research standards.

This document serves as the authoritative dataset registry, provenance record, and data engineering strategy for Phase 1 of MPF-PD.

---

## 2. Dataset Summary Table

| Dataset ID | Category | Primary Modalities | Participants | PD / Prodromal / Control Labels | Access Level | License | Main Limitation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ppmi` | A (Same-Participant Multimodal) | Olfactory, Sleep/RBD, Motor, Voice, Biospecimens, Imaging | ~4,000+ | PD: ~1,500<br>Prodromal: ~600<br>Control: ~800 | Registration & DUA | PPMI Data Use Agreement | Complex DUA, sequestered bio-assays, missing imaging alignment |
| `predict_pd` | A / D (Prodromal Cohort) | Olfactory, Sleep/RBD, Finger Tapping, Risk Scores | ~10,000 enrolled (online screening) | High Risk / Low Risk / Prodromal | Restricted | Formal Research Collaboration Agreement | Not open access; requires institutional DUA & ethics approval |
| `uci_voice` | B (Modality-Specific) | Speech / Voice Dysphonia | 42 (5,875 recordings) | PD: 42 (Longitudinal UPDRS) | Open | CC BY 4.0 / Public Domain | Small participant cohort; no healthy controls in Telemonitoring set |
| `physionet_gait` | B (Modality-Specific) | Gait Dynamics / Force Sensors (VGRF) | 166 | PD: 93<br>Control: 73 | Open | Open Data Commons Attribution (ODC-By) v1.0 | Short 2-minute walking protocol; no non-motor/prodromal labels |
| `mpower` | A / B (Mobile Multimodal) | Tapping, Gait, Memory, Voice | ~10,000+ | Self-reported PD & Controls | Registration-Based | Synapse Governance / Qualified Researcher DUA | Self-reported diagnosis; high participant drop-off rate |
| `retinal_fundus_pretraining` | C (Pretraining Only) | Retinal Fundus Photographs | ~80,000+ images (DRIVE, EyePACS, Messidor-2, APTOS) | Diabetic Retinopathy / Vessel Labels (**NO PD Labels**) | Open / Kaggle Access | Custom Academic / CC-BY-NC | **No PD labels**; strictly for encoder feature representation pretraining |
| `oct500` | C (Pretraining Only) | OCT / OCTA Retinal Scans | 500 volumes | Retinal Pathology (**NO PD Labels**) | Registration / Request | Non-Commercial Academic License | **No PD labels**; small volume count; specialized pretraining only |
| `synthetic_fixture` | E (Synthetic Test Fixture) | Tabular / Mock Modalities | N/A (Generated) | Mock Labels (0, 1, 2) | Internal | MIT / Open | **Synthetic mock data**; strictly for unit tests & CI pipeline |

---

## 3. Detailed Dataset Cards

### Card 1: PPMI (Parkinson’s Progression Markers Initiative)
- **Dataset ID:** `ppmi`
- **Dataset Name:** Parkinson’s Progression Markers Initiative
- **Official Source:** Michael J. Fox Foundation for Parkinson’s Research / LONI Image Data Archive
- **Persistent URL / Access Portal:** [https://www.ppmi-info.org/access-data-specimens/download-data](https://www.ppmi-info.org/access-data-specimens/download-data)
- **Access Requirements:** Registration, submission of research statement, and signing of PPMI Data Use Agreement (DUA).
- **License:** PPMI Specific Data Use Agreement (restricted academic/commercial research use).
- **Access Level:** Registration-Based / Controlled.
- **Participant Count:** ~4,000+ total participants across multi-site longitudinal cohorts.
- **Record / Sample Count:** >100,000 longitudinal observation records across visits (BL, V01-V18).
- **Labels:** 
  - Parkinson's Disease (De Novo & Genetic): ~1,500
  - Prodromal (RBD / Hyposmia / Genetic Risk): ~600
  - Healthy Controls: ~800
  - SWEDD (Scans Without Evidence of Dopaminergic Deficit): ~300
- **Available Modalities:**
  1. Olfactory (UPSIT - University of Pennsylvania Smell Identification Test)
  2. Sleep / RBD (RBDSQ, SCOPA-SLEEP, ESS)
  3. Motor / Gait / Tapping (MDS-UPDRS Part III, sensor sub-studies)
  4. Voice / Speech (Digital sub-study recordings & acoustic features)
  5. Imaging / Biospecimens (DaTscan SPECT, MRI, CSF alpha-synuclein SAA, serum)
- **Relevant Variables:** `PATNO`, `EVENT_ID`, `UPSIT_TOTAL`, `RBDSQ_TOTAL`, `NP3TOT`, `DATSCAN_CAUDATE_R`, `DATSCAN_PUTAMEN_R`, `DIAGNOSIS`.
- **File Format:** CSV, Parquet, DICOM (imaging), NIfTI.
- **Missing Data Patterns:** Longitudinal attrition, optional sub-study drop-off, missing visits due to protocol updates.
- **Known Limitations:** Complex schema changes across data releases; high cost of imaging raw downloads; restricted alpha-synuclein SAA access.
- **Same-Participant Multimodal Support:** **YES**. True longitudinal same-participant multimodal data across non-motor and motor modalities.
- **Suitability:** Primary dataset for prototype training, multimodal fusion development, and longitudinal validation.

---

### Card 2: PREDICT-PD Cohort
- **Dataset ID:** `predict_pd`
- **Dataset Name:** PREDICT-PD Study Cohort
- **Official Source:** Queen Mary University of London (QMUL) & University College London (UCL)
- **Persistent URL / Access Portal:** [https://www.predictpd.com](https://www.predictpd.com)
- **Access Requirements:** Formal collaboration request submitted to study PIs (`predictpd@qmul.ac.uk`) and institutional ethics approval.
- **License:** Strict Institutional Data Transfer Agreement (DTA).
- **Access Level:** Restricted / Managed Access.
- **Participant Count:** ~10,000 enrolled general population participants in UK online screening cohort.
- **Record / Sample Count:** Annual longitudinal assessments over 5+ years.
- **Labels:**
  - High Risk (Prodromal PD risk score): ~5% of cohort
  - Intermediate Risk: ~15%
  - Low Risk / Healthy Controls: ~80%
  - Incident PD conversions tracked longitudinally.
- **Available Modalities:**
  1. Olfactory (UPSIT / online smell test)
  2. RBD / Sleep (RBDSQ)
  3. Motor (Keyboard finger-tapping latency test)
  4. Non-motor risk factors (family history, constipation, mood)
- **Relevant Variables:** `participant_id`, `upsit_score`, `kbd_tapping_speed`, `rbd_score`, `pd_risk_tier`.
- **File Format:** CSV / Tabular.
- **Missing Data Patterns:** Online self-administration missingness; loss to follow-up in web questionnaires.
- **Known Limitations:** Not available for direct open-source download; keyboard tapping is noisy compared to clinical sensors.
- **Same-Participant Multimodal Support:** **YES**. Same participants undergo battery of online screening tasks.
- **Suitability:** External validation dataset for prodromal risk stratification algorithms.

---

### Card 3: UCI Parkinson’s Telemonitoring / Speech Dataset
- **Dataset ID:** `uci_voice`
- **Dataset Name:** UCI Parkinson's Telemonitoring Dataset (Little et al. / Tsanas et al.)
- **Official Source:** UCI Machine Learning Repository / University of Oxford
- **Persistent URL / Access Portal:** [https://archive.ics.uci.edu/dataset/189/parkinsons+telemonitoring](https://archive.ics.uci.edu/dataset/189/parkinsons+telemonitoring)
- **Access Requirements:** None (Open Access).
- **License:** Creative Commons Attribution 4.0 International (CC BY 4.0).
- **Access Level:** Open Access.
- **Participant Count:** 42 early-stage PD patients.
- **Record / Sample Count:** 5,875 voice recording samples (approx. 140-200 per patient over 6 months).
- **Labels:** Continuous clinician-assessed `motor_UPDRS` (range 5-40) and `total_UPDRS` (range 7-55). **No healthy controls** in Telemonitoring set.
- **Available Modalities:** Speech / Voice acoustic dysphonia measures.
- **Relevant Variables:** `subject#`, `age`, `sex`, `test_time`, `motor_UPDRS`, `total_UPDRS`, `Jitter(%)`, `Shimmer`, `NHR`, `HNR`, `RPDE`, `DFA`, `PPE`.
- **File Format:** CSV.
- **Missing Data Patterns:** Low missingness within extracted feature table; unbalanced recording frequencies.
- **Known Limitations:** Lacks healthy control group; single modality (voice only); small participant headcount (N=42).
- **Same-Participant Multimodal Support:** **NO**. Voice and UPDRS only.
- **Suitability:** Modality-specific representation learning and regression model validation for the voice branch.

---

### Card 4: PhysioNet Gait in Parkinson’s Disease
- **Dataset ID:** `physionet_gait`
- **Dataset Name:** Gait in Parkinson's Disease (Goldberger et al. / Hausdorff et al.)
- **Official Source:** PhysioNet / Tel-Aviv Sourasky Medical Center
- **Persistent URL / Access Portal:** [https://doi.org/10.13026/C24H3N](https://doi.org/10.13026/C24H3N)
- **Access Requirements:** None (Open Access with proper citation).
- **License:** Open Data Commons Attribution License (ODC-By) v1.0.
- **Access Level:** Open Access.
- **Participant Count:** 166 total participants.
- **Record / Sample Count:** 93 PD patients and 73 healthy controls across 3 sub-studies.
- **Labels:** 
  - Parkinson's Disease: 93
  - Healthy Control: 73
- **Available Modalities:** Gait dynamics via 16 force sensors (8 under each foot measuring Vertical Ground Reaction Force - VGRF at 100 Hz).
- **Relevant Variables:** `Time`, `L1`-`L8` (left foot sensors), `R1`-`R8` (right foot sensors), `Total_Force_Left`, `Total_Force_Right`, `HoehnYahr`, `UPDRS`, `GaitSpeed`.
- **File Format:** ASCII text files (`.txt`) / CSV.
- **Missing Data Patterns:** Clean 2-minute steady-state walking trials; minimal missing sensor frames.
- **Known Limitations:** Gait recorded under clean lab conditions; no non-motor (olfactory/RBD) data available.
- **Same-Participant Multimodal Support:** **NO**. Single-modality gait force dataset.
- **Suitability:** Modality-specific pretraining and encoder evaluation for the gait/motor branch.

---

### Card 5: Sage Bionetworks mPower Mobile Dataset
- **Dataset ID:** `mpower`
- **Dataset Name:** Parkinson Disease Mobile Data Study (mPower)
- **Official Source:** Sage Bionetworks / Synapse Platform
- **Persistent URL / Access Portal:** [https://www.synapse.org/#!Synapse:syn4993293](https://www.synapse.org/#!Synapse:syn4993293)
- **Access Requirements:** Synapse account, ethics training certification, research request submission.
- **License:** Synapse Qualified Researcher Governance Terms.
- **Access Level:** Registration-Based.
- **Participant Count:** ~10,000+ smartphone app users.
- **Record / Sample Count:** Hundreds of thousands of longitudinal micro-tasks.
- **Labels:** Self-reported PD diagnosis, medication timing (pre/post dopaminergic medication), and self-reported age/sex controls.
- **Available Modalities:**
  1. Memory / Cognitive (Spatial Memory Game)
  2. Voice (Sustained phonation /a/)
  3. Tapping (Two-finger memory tapping task)
  4. Gait / Balance (30-second walk & standing rest)
- **Relevant Variables:** `recordId`, `healthCode`, `createdOn`, `medTimepoint`, `accel_gait.json`, `tapping_results.json`.
- **File Format:** JSON, CSV, m4a audio.
- **Missing Data Patterns:** Severe longitudinal drop-off (high sparsity after week 1); self-selection bias.
- **Known Limitations:** Self-reported labels introduce diagnostic noise; noisy sensor data from varying smartphone models.
- **Same-Participant Multimodal Support:** **YES** (within digital mobile tasks for active app users).
- **Suitability:** Large-scale digital biomarker feature extraction and pretraining.

---

### Card 6: Retinal Fundus Pretraining Dataset (DRIVE / EyePACS / Messidor-2)
- **Dataset ID:** `retinal_fundus_pretraining`
- **Dataset Name:** Combined Retinal Fundus Pretraining Corpus (DRIVE, EyePACS, Messidor-2, APTOS 2019)
- **Official Source:** Kaggle / Grand-Challenge.org / DRiDB
- **Persistent URL / Access Portal:** [https://www.kaggle.com/c/diabetic-retinopathy-detection](https://www.kaggle.com/c/diabetic-retinopathy-detection)
- **Access Requirements:** Kaggle user agreement for competition datasets.
- **License:** Custom Non-Commercial Academic / CC-BY-NC.
- **Access Level:** Open Access / Registration.
- **Participant Count:** ~40,000+ patients (~80,000 fundus images).
- **Record / Sample Count:** 88,702 color fundus photographs.
- **Labels:** Diabetic Retinopathy Grade (0-4), Vessel segmentations. **NO Parkinson's Labels**.
- **Available Modalities:** High-resolution color retinal fundus photography.
- **Relevant Variables:** `image_id`, `eye` (left/right), `dr_grade`, `vessel_mask`.
- **File Format:** JPEG, PNG, TIFF.
- **Missing Data Patterns:** Variable image resolution, illumination artifacts, cataract opacities.
- **Known Limitations:** **Contains NO Parkinson's disease clinical labels**.
- **Same-Participant Multimodal Support:** **NO**.
- **Suitability:** Strictly Category C (Pretraining Only). Used to train self-supervised CNN/Vision Transformer encoders or vessel segmentation backbones. Must NOT be presented as a PD clinical dataset.

---

### Card 7: OCT500 Dataset
- **Dataset ID:** `oct500`
- **Dataset Name:** OCT500 Retinal Optical Coherence Tomography Dataset
- **Official Source:** Nanjing University of Science and Technology / IEEE DataPort
- **Persistent URL / Access Portal:** [https://mmlab.eecs.umich.edu/oct500/](https://mmlab.eecs.umich.edu/oct500/)
- **Access Requirements:** Academic email registration and non-commercial agreement.
- **License:** Academic Non-Commercial License.
- **Access Level:** Registration-Based.
- **Participant Count:** 500 subjects.
- **Record / Sample Count:** 500 3D OCT / OCTA volumes with 2D retinal layer segmentations.
- **Labels:** Age, Gender, Retinal Disease Types (AMD, DR, CNV). **NO Parkinson's Labels**.
- **Available Modalities:** 3D OCT volumes, 2D OCTA projection maps, 6-layer retinal segmentations.
- **Relevant Variables:** `subject_id`, `oct_volume`, `foveal_thickness`, `retinal_nerve_fiber_layer_mask`.
- **File Format:** MAT, NIfTI, PNG.
- **Missing Data Patterns:** High signal-to-noise ratio variation; speckle noise artifacts.
- **Known Limitations:** **Contains NO Parkinson's disease labels**. Small sample size (N=500).
- **Same-Participant Multimodal Support:** **NO**.
- **Suitability:** Category C (Pretraining Only). Used for 3D OCT layer segmentation encoder pretraining.

---

### Card 8: Synthetic Fixture Dataset
- **Dataset ID:** `synthetic_fixture`
- **Dataset Name:** MPF-PD Synthetic Test Fixture
- **Official Source:** MPF-PD Data Engineering Pipeline (Generated)
- **Persistent URL / Access Portal:** Local pipeline generator (`tests/fixtures/`)
- **Access Requirements:** None.
- **License:** MIT License / Open.
- **Access Level:** Open Access.
- **Participant Count:** 100 synthetic mock participants.
- **Record / Sample Count:** 100 aligned synthetic records.
- **Labels:** Mock Clinical Status (0 = Control, 1 = Prodromal, 2 = PD).
- **Available Modalities:** Synthetic Olfactory, RBD, Motor, Voice, and Retinal feature vectors.
- **Relevant Variables:** `participant_id`, `upsit_score`, `rbd_score`, `updrs_motor`, `voice_pitch_sd`, `retinal_rnfl_thickness`, `diagnosis`.
- **File Format:** CSV, Parquet.
- **Missing Data Patterns:** Controlled missingness inserted synthetically for testing missing-data pipelines.
- **Known Limitations:** **Completely synthetic fixture data**. Has zero physiological or clinical reality.
- **Same-Participant Multimodal Support:** Simulated.
- **Suitability:** Category E (Synthetic Test Fixtures). Strictly for CI/CD, unit testing, and code structure validation.

---

## 4. Dataset Category Classification

All candidate datasets are explicitly categorized according to the project classification rules:

### Category A: Same-Participant Multimodal Data
- **`ppmi`**: Primary same-participant cohort containing Olfactory (UPSIT), RBD (RBDSQ), Motor (UPDRS III), Speech, and Longitudinal Diagnoses for the exact same participants over time.
- **`mpower`**: Secondary mobile same-participant cohort containing voice, tapping, gait, and memory tasks.

### Category B: Modality-Specific Datasets
- **`uci_voice`**: Speech/voice dysphonia features paired with UPDRS scores for 42 participants.
- **`physionet_gait`**: Ground reaction force sensor time-series for 166 participants walking on level ground.

### Category C: Pretraining Datasets
- **`retinal_fundus_pretraining`** (EyePACS / DRIVE / Messidor-2): Retinal fundus images for feature extractor pretraining (vessel segmentation / vision backbone pretraining). **NOT a PD dataset**.
- **`oct500`**: Retinal OCT 3D volumes and layer segmentation. **NOT a PD dataset**.

### Category D: External Validation Datasets
- **`predict_pd`**: Prodromal risk cohort used for external validation of non-motor prodromal risk scoring.

### Category E: Synthetic Test Fixtures
- **`synthetic_fixture`**: Artificial test fixture used exclusively for unit tests, pipeline checks, and CI validation.

---

## 5. Recommended Dataset Strategy for Student Research Prototype

For an effective, clinically grounded student research prototype within MPF-PD, we recommend the following dataset strategy:

1. **Primary Dataset for Prototype Training:**
   - **PPMI (Category A)** is the **ONLY** feasible dataset for genuine same-participant multimodal fusion. It contains longitudinal UPSIT olfactory scores, RBDSQ sleep assessments, MDS-UPDRS motor scores, and clinical diagnosis labels for the same participants.

2. **Modality-Specific Branch Development:**
   - Use **`uci_voice`** to train and validate the Voice/Speech feature extractor branch.
   - Use **`physionet_gait`** to train and validate the Motor/Gait sensor feature extractor branch.

3. **Retinal Pretraining Strategy:**
   - Use **`retinal_fundus_pretraining`** (DRIVE / EyePACS) to pretrain the ResNet/EfficientNet/Vision Transformer backbone for retinal vessel & structural feature extraction.
   - Fine-tune or extract features for PPMI participants if retinal OCT sub-study data is acquired.

4. **Feasibility of True Same-Participant Multimodal Fusion:**
   - **YES**, true same-participant fusion is feasible **IF AND ONLY IF** PPMI is used as the primary backbone dataset.
   - Combining `uci_voice` with `physionet_gait` across different subject IDs is strictly prohibited for multimodal fusion model evaluation.

5. **Phase 6 Evaluation Labeling:**
   - If PPMI data is used: Label Phase 6 as **`true_multimodal`**.
   - If prototype relies on cross-dataset synthetic matching due to access restrictions: Label Phase 6 explicitly as **`prototype_simulation`**.

6. **Suggested Train / Validation / Test Strategy:**
   - **Participant-level Stratified Splitting**: Split data by `participant_id` (70% Train, 15% Validation, 15% Test) stratified by clinical diagnosis label (`PD`, `Prodromal`, `Control`).
   - **Zero Data Leakage Rule**: All temporal longitudinal records for a single `participant_id` must reside exclusively within one split (Train, Val, or Test).

7. **Risks & Licensing Restrictions:**
   - PPMI requires DUA execution and approval.
   - PREDICT-PD is restricted and cannot be downloaded directly into public repositories.
   - Retinal datasets must never be mislabeled as PD datasets.

8. **Missing Modality Strategy:**
   - In real-world prodromal screening, participants often lack complete modality coverage. The fusion pipeline must implement explicit missingness masking and transformer-based or attention-gated modality embedding rather than naive missing row deletion or zero-imputation without mask flags.

9. **What Claims MUST NOT Be Made:**
   - Do **NOT** claim that diabetic retinopathy datasets contain Parkinson's disease signals.
   - Do **NOT** claim that combining UCI voice subjects with PhysioNet gait subjects constitutes a real multimodal patient cohort.
   - Do **NOT** claim prodromal diagnostic accuracy on synthetic test fixtures.

---

## 6. Risks and Limitations

1. **Access Risk:** PPMI DUA review can take several days/weeks. Pipeline must operate smoothly on synthetic fixtures (`synthetic_fixture`) while awaiting access.
2. **Modality Sparsity:** Not all PPMI subjects have every modality recorded at every visit.
3. **Diagnostic Noise in Prodromal Stage:** Phenotypic converters in PPMI take years to manifest motor PD; labels reflect risk probability rather than absolute ground truth.

---

## 7. Access Checklist

- [x] Identify candidate datasets across all 5 target modalities.
- [x] Categorize datasets into Categories A, B, C, D, and E.
- [x] Create standardized metadata YAML files in `data/metadata/`.
- [x] Implement Python registry module in `src/data/registry.py`.
- [x] Implement dataset loaders in `src/data/loaders.py`.
- [x] Implement dataset validators in `src/data/validators.py`.
- [x] Implement unit tests in `tests/test_data_registry.py` and `tests/test_data_validators.py`.
- [ ] Submit PPMI Data Use Agreement application via LONI portal.
- [ ] Download PPMI tabular datasets (`UPSIT.csv`, `RBDSQ.csv`, `MDS_UPDRS_III.csv`).
