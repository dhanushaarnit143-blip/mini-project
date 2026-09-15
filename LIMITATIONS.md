# MPF-PD System Limitations

**Multimodal Prodromal Fusion for Parkinson’s Disease Risk Screening**  
*Investigational Research Prototype — Critical Limitations & Scientific Boundaries*

---

> [!IMPORTANT]
> ### STATEMENT OF SCIENTIFIC INTEGRITY
> Honest disclosure of limitations is essential for responsible biomedical research. The MPF-PD system is an **investigational research prototype**, not a medical device. It **does not diagnose Parkinson’s disease**. Researchers and software engineers evaluating this codebase must understand the following ten fundamental scientific and clinical limitations.

---

## 1. Lack of Same-Participant Multimodal Data

The primary scientific limitation of this prototype is the **absence of authentic, same-participant five-modality data** in open-access local storage.
- Longitudinal clinical cohorts containing synchronized retinal scans, acoustic recordings, force-plate gait dynamics, smell test scores, and sleep questionnaires from the identical human subjects (e.g. PPMI, Oxford Discovery) are restricted by institutional Data Use Agreements (DUAs) and cannot be distributed in open repositories.
- To validate the mathematical correctness and software architecture of the gated fusion pipeline, experiments in Phases 1–10 were executed on the **MPF-PD Synthetic Multimodal Fixture (`Category E`)**.
- While feature distributions were parameterized based on published clinical literature, synthetic cross-modality correlations do not capture the biological heterogeneity and stochasticity of true human disease.

---

## 2. Limited Sample Size & Synthetic Sample Statistics

- The active test fixture comprises **350 simulated participants** ($245$ training, $52$ validation, $53$ testing).
- This sample size is sufficient for validating software logic, gradient propagation, and algorithmic convergence, but it is **drastically smaller** than required to characterize the full epidemiological distribution of prodromal Parkinson's disease in the general population.
- True clinical screening algorithms require validation across cohorts of $10,000+$ individuals followed longitudinally over decades (as in PREDICT-PD).

---

## 3. Dataset Mismatch & Surrogate Labels

Publicly accessible unimodal datasets used to inform the feature extraction branches carry significant clinical domain mismatches:
1. **UCI Voice Dataset (`uci_voice`):** Contains recordings from **42 individuals, all of whom have manifest Parkinson's disease**. It contains **zero healthy controls**. Binary classification on this dataset represents splitting disease severity (motor UPDRS), not screening for early disease risk against healthy individuals.
2. **PhysioNet Gait Dataset (`physionet_gait`):** Ground reaction force data was recorded from patients with **moderate manifest Parkinson's disease** (Hoehn & Yahr stages 2–3). Gait signatures of manifest PD do not directly extrapolate to subtle prodromal motor changes that precede diagnosis by years.
3. **Retinal Pretraining Corpora (DRIVE, EyePACS, Messidor-2):** These datasets contain diabetic retinopathy and normal eye images, but **zero Parkinson's disease labels**. The retinal feature encoder can segment vessels, but has not learned a Parkinson's-specific retinal pathology representation.

---

## 4. Missing Modality Uncertainty

Although the neural attention gating mechanism handles arbitrary subsets of missing modalities without crashing:
- Omitting non-motor anchor modalities (such as olfactory testing or RBDSQ) noticeably widens statistical confidence bounds.
- If only one modality is provided, the system loses the cross-validating benefit of multimodal fusion, and the risk estimate reflects only unimodal discrimination.
- When all five modalities are omitted, the system can only output a non-informative prior ($0.50$) with a maximum uncertainty warning.

---

## 5. Demographic & Population Bias

- **Retinal Imaging:** Fundus pigmentation varies significantly across ethnic backgrounds. Lightly pigmented fundi exhibit different vascular contrast compared to heavily pigmented fundi, which can cause systematic errors in morphological vessel density calculations if algorithms are trained on homogenous cohorts.
- **Voice & Speech:** Acoustic dysphonia metrics (jitter, shimmer, fundamental frequency perturbation) vary widely by age, sex, primary language, regional dialect, and respiratory health.
- **Olfaction:** Normative smell identification performance declines physiologically with normal aging and is heavily influenced by prior viral infections (e.g. COVID-19, influenza) and chronic sinusitis.
- The current synthetic fixture does not adequately represent the full spectrum of demographic diversity across global populations.

---

## 6. Domain Shift: Lab Sensors vs. Real-World Devices

- **Gait Force Sensors:** PhysioNet gait data was captured using dedicated multi-sensor shoe insole force plates during a standardized 2-minute overground walking trial in a hospital corridor. These clean signals do not translate directly to noisy, uncontrolled accelerometry from consumer smartwatches or smartphones carried in pockets.
- **Acoustic Environment:** Voice metrics assume studio-quality or high-SNR microphone recordings of sustained vowel `/a/`. Background acoustic noise, mobile microphone compression, and room reverberation substantially degrade jitter and shimmer calculations in uncontrolled environments.

---

## 7. Lack of Prospective Validation & Longitudinal Phenoconversion

- Idiopathic REM Sleep Behavior Disorder (iRBD) and severe hyposmia confer high risk for alpha-synucleinopathies, but phenoconversion from prodromal status to overt motor Parkinson's disease takes **5 to 15 years**.
- The MPF-PD prototype has only been evaluated in a cross-sectional simulation paradigm. It has **never been validated prospectively** to determine whether individuals with an "elevated risk pattern" actually develop Parkinson's disease on multi-year follow-up.

---

## 8. Complete Absence of Clinical Diagnostic Validity

> [!CAUTION]
> The MPF-PD system:
> - Has **NOT** been approved, cleared, or certified by the FDA, EMA, MHRA, or any other medical regulatory body.
> - Must **NOT** be used to provide clinical diagnoses, recommend medications, or alter medical treatments.
> - High ROC-AUC values reported in `RESULTS.md` reflect clean synthetic fixture discrimination and must **NEVER** be advertised as clinical sensitivity or specificity.

---

## 9. Explanation Layer Limitations (TreeSHAP)

- TreeSHAP computes exact Shapley values on the **45-dimensional fused representation** $\mathbf{z}_{\text{final}}$, which consists of compressed neural embeddings ($\mathbf{z}_{\text{gated}}$) and presence flags.
- While Shapley values on presence flags accurately measure missingness impact, Shapley values on latent embedding dimensions (`fused_gated_1`, etc.) reflect compressed neural representations rather than individual raw biomarker variables (e.g. `jitter_pct`).
- Layer-wise backpropagation of Shapley values through non-linear multi-layer perceptron encoders is computationally expensive and was not implemented in this prototype.

---

## 10. Software Deployment & Productionization Boundaries

- The local FastAPI and React web dashboard are designed strictly for **research demonstrations and local workstation evaluation**.
- The system lacks hospital-grade cybersecurity, HIPAA/GDPR clinical data encryption at rest, formal Electronic Health Record (EHR) integrations (HL7 / FHIR), and automated audit trails required for medical software deployments.
