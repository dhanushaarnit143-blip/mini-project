# MPF-PD Experimental Protocols & Benchmarks

**Multimodal Prodromal Fusion for Parkinson’s Disease Risk Screening**  
*Investigational Research Prototype — Experimental Log & Benchmarking Protocols*

---

> [!IMPORTANT]
> ### EXPERIMENTAL PROVENANCE & SIMULATION NOTICE
> - **Active Mode:** `prototype_simulation`
> - **Dataset:** Synthetic Aligned Multimodal Test Fixture (`Category E`)
> - **Disclaimer:** All experiments were executed on synthetic datasets reflecting published literature distributions. These benchmarks evaluate **software correctness, pipeline architecture, and mathematical resilience**. They have **zero clinical validity** and must **not** be cited as real-world patient outcomes.

---

## 1. Overview of Experimental Series

The MPF-PD research investigation was divided into seven distinct experimental series spanning Phases 1 through 10:

```
[Experiment 1: Single-Modality Unimodal Benchmarks]
  ├── Olfactory (Random Forest vs Logistic Regression vs XGBoost)
  ├── RBD Sleep (Logistic Regression vs Random Forest vs XGBoost)
  ├── Voice Acoustics (Logistic Regression vs Random Forest vs XGBoost)
  ├── Motor / Gait Dynamics (Logistic Regression vs Random Forest vs XGBoost)
  └── Retinal Morphometry & CNN Representation
         │
         ▼
[Experiment 2: Early Fusion Baseline (Concatenation + XGBoost)]
         │
         ▼
[Experiment 3: Late Fusion Baseline (Weighted Probability Average)]
         │
         ▼
[Experiment 4: Gated Multimodal Fusion Architecture]
         │
         ▼
[Experiment 5: Missing-Modality Systematic Degradation Suite]
         │
         ▼
[Experiment 6: Robustness & Adversarial Boundary Tests]
         │
         ▼
[Experiment 7: Reproducibility & Determinism Verification]
```

---

## 2. Experiment 1: Single-Modality Benchmarks

### 2.1 Protocol & Objective
Evaluate the baseline discriminative capacity of each individual biomarker modality when modeled in isolation. Identify the optimal machine learning classifier for each branch before integrating into the multimodal network.

### 2.2 Specifications
- **Dataset Used:** Synthetic Multimodal Fixture (`Category E`, $N=350$ participants; Train $N=245$, Val $N=52$, Test $N=53$).
- **Experiment Type:** `prototype_simulation`
- **Models Compared per Branch:** Logistic Regression ($L_2$ penalty), Random Forest ($100$ estimators), and XGBoost ($100$ estimators, `max_depth=3`).
- **Evaluation Metrics:** ROC-AUC, Accuracy, Precision, Recall, Macro F1-Score on the held-out test split.
- **Artifact & Result Locations:**
  - Olfactory: `evaluation/olfactory_results.json`, `models/olfactory/model.joblib`
  - RBD: `evaluation/rbd_results.json`, `models/rbd/model.joblib`
  - Voice: `evaluation/voice_results.json`, `models/voice/model.joblib`
  - Motor: `evaluation/motor_results.json`, `models/motor/model.joblib`
  - Retina: `evaluation/retina_results.json`, `models/retina/metadata.json`

### 2.3 Single-Modality Test Split Results ($N=53$)
| Modality Branch | Selected Model | Test Samples | Accuracy | Precision | Recall | F1-Score | ROC-AUC |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Olfactory** | Random Forest | 53 | 0.9434 | 0.9615 | 0.9259 | 0.9434 | 0.9936 |
| **RBD Questionnaire** | Logistic Regression | 53 | 0.9245 | 0.8710 | 1.0000 | 0.9310 | 0.9943 |
| **Voice / Speech** | Logistic Regression | 53 | 0.8113 | 0.7297 | 1.0000 | 0.8438 | 0.9786 |
| **Motor / Gait** | Logistic Regression | 53 | 0.8302 | 0.7500 | 1.0000 | 0.8571 | 0.9872 |
| **Retina** | Morphometry + CNN | 35 | N/A* | N/A* | N/A* | N/A* | N/A* |

*\*Retina operates as an unsupervised/feature extraction branch in this setup because public retinal datasets lack Parkinson's labels. Its 28 features feed directly into the multimodal fusion network.*

### 2.4 Limitations
Isolated single-modality evaluations do not account for cross-biomarker correlations and cannot compensate when that single modality is missing.

---

## 3. Experiment 2: Early Fusion Baseline (Concatenation)

### 3.1 Protocol & Objective
Implement an early feature concatenation baseline where all 81 raw/preprocessed features across all five modalities ($5 \text{ olf} + 16 \text{ rbd} + 16 \text{ voi} + 8 \text{ mot} + 28 \text{ ret} + 2 \text{ demo} + 6 \text{ aux}$) are concatenated into a single flat vector and classified using an optimized XGBoost model.

### 3.2 Specifications
- **Dataset Used:** Synthetic Multimodal Fixture (`Category E`, $N=350$).
- **Experiment Type:** `prototype_simulation`
- **Feature Dimension:** $D = 81$ features.
- **Model:** `XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.05)`.
- **Metrics:** Accuracy: 1.0000, F1-Score: 1.0000, ROC-AUC: 1.0000, Brier Score: 0.0042.
- **Result Location:** `evaluation/fusion_results.json` (section: `concatenation`).
- **Limitations:** Early concatenation suffers from high dimensional sparsity when multiple modalities are missing, relying entirely on XGBoost default split directions without dynamic attention redistribution.

---

## 4. Experiment 3: Late Fusion Baseline (Weighted Average)

### 4.1 Protocol & Objective
Implement a decision-level late fusion baseline where individual single-modality models output risk probabilities $\hat{p}_m \in [0, 1]$, which are combined via uniform weighted averaging across active modalities:
$$\hat{p}_{\text{late}} = \frac{1}{\sum p_k} \sum_{m \in \mathcal{M}_{\text{present}}} \hat{p}_m$$

### 4.2 Specifications
- **Dataset Used:** Synthetic Multimodal Fixture (`Category E`, $N=350$).
- **Experiment Type:** `prototype_simulation`
- **Weighting Policy:** Uniform over present modalities ($w_m = 1 / |\mathcal{M}_{\text{present}}|$).
- **Metrics:** Accuracy: 1.0000, F1-Score: 1.0000, ROC-AUC: 1.0000, Brier Score: 0.0125.
- **Result Location:** `evaluation/fusion_results.json` (section: `weighted_average`).
- **Limitations:** Decision-level late fusion assumes conditional independence between modalities and cannot model complex non-linear feature interactions occurring across biological systems.

---

## 5. Experiment 4: Gated Multimodal Fusion Architecture

### 5.1 Protocol & Objective
Evaluate the novel **Gated Multimodal Fusion** architecture combining 2-layer MLP modality encoders, dynamic masked attention gating, learnable missing tokens, and a final calibrated XGBoost classifier.

### 5.2 Specifications
- **Dataset Used:** Synthetic Multimodal Fixture (`Category E`, $N=350$).
- **Experiment Type:** `prototype_simulation`
- **Embedding Dimension:** $d = 32$ per modality; Fused vector $D = 45$ (32 gated + 8 demo + 5 presence flags).
- **Metrics on Held-Out Test Split ($N=53$):**
  - **Accuracy:** 1.0000
  - **Precision:** 1.0000
  - **Recall:** 1.0000
  - **F1-Score:** 1.0000
  - **ROC-AUC:** 1.0000
  - **Brier Score:** **0.0031** (superior calibration compared to concatenation: 0.0042, and weighted average: 0.0125)
- **Mean Gate Weights (All 5 Present):**
  - Olfactory: $0.2439$ (24.4%)
  - Motor / Gait: $0.2211$ (22.1%)
  - Voice: $0.1925$ (19.3%)
  - RBD: $0.1802$ (18.0%)
  - Retina: $0.1623$ (16.2%)
- **Bootstrap Statistical Significance (1,000 resamples):**
  - Gated Fusion vs Concatenation: Mean $\Delta \text{AUC} = 0.0000$, 95% CI $[0.0000, 0.0000]$.
  - Gated Fusion vs Best Single (`olfactory`): Mean $\Delta \text{AUC} = 0.0057$, 95% CI $[0.0000, 0.0176]$.
- **Result Location:** `evaluation/fusion_results.json` (section: `gated_fusion`).
- **Limitations:** High discriminatory metrics reflect clean separability in synthetic fixtures; clinical cohorts exhibit far higher noise, comorbidity overlap, and phenotypic heterogeneity.

---

## 6. Experiment 5: Missing-Modality Systematic Degradation Suite

### 5.1 Protocol & Objective
Systematically remove modalities during inference on the test split ($N=53$) to measure architectural degradation, gate weight reallocations, and minimum required modality subsets.

### 5.2 Specifications
- **Dataset Used:** Synthetic Multimodal Fixture (`Category E`).
- **Scenarios Evaluated:** 10 distinct configurations ranging from 5 active modalities down to 1 active modality.
- **Result Location:** `evaluation/missing_modality_analysis.json` and `evaluation/figures/missing_modality_impact.png`.

### 5.3 Degradation Results Table
| Evaluated Configuration | Active Count | ROC-AUC | F1-Score | AUC Drop ($\Delta$) | Gate Redistribution Profile |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **All 5 Modalities Present** | 5 | 1.0000 | 0.9811 | 0.0000 | Balanced across all 5 branches (~0.20 each) |
| Missing **Retina** | 4 | 1.0000 | 0.9811 | 0.0000 | Reallocated uniformly to Olf, RBD, Voice, Motor |
| Missing **Voice** | 4 | 1.0000 | 0.9615 | 0.0000 | Reallocated to Olfactory, RBD, Motor, Retina |
| Missing **Motor** | 4 | 1.0000 | 0.9615 | 0.0000 | Reallocated to Olfactory, RBD, Voice, Retina |
| Missing **Olfactory** | 4 | 1.0000 | 1.0000 | 0.0000 | Reallocated to RBD, Voice, Motor, Retina |
| Missing **Retina + Voice** | 3 | 1.0000 | 0.9412 | 0.0000 | Tri-modal balance: Olfactory, RBD, Motor (~0.33 each) |
| Missing **Olfactory + RBD** | 3 | 1.0000 | 0.9474 | 0.0000 | Reallocated to Motor, Voice, Retina (~0.33 each) |
| Missing **Retina + Voice + Motor**| 2 | 1.0000 | 0.8511 | 0.0000 | Shared between Olfactory ($0.54$) and RBD ($0.46$) |
| Only **Olfactory** Present | 1 | 0.9779 | 0.8750 | 0.0221 | Olfactory assigned $1.0000$ gate weight |
| Only **Motor** Present | 1 | 0.9744 | 0.9412 | 0.0256 | Motor assigned $1.0000$ gate weight |

### 5.4 Policy Findings
- The system demonstrates **graceful degradation**; removing any single modality causes zero drop in ROC-AUC.
- When reduced to only 1 modality, AUC drops by $\sim 0.022$ to $0.025$, but remains discriminative.
- **Recommended Policy:** A minimum of **2 active modalities** is required for reliable screening.

---

## 7. Experiment 6: Robustness & Adversarial Stress Tests

### 7.1 Protocol & Objective
Expose the full inference pipeline and REST API to corrupted payloads, out-of-range sensor inputs, invalid demographics, and empty requests.

### 7.2 Stress Test Cases & Observed System Behavior
1. **Physiologic Out-of-Bounds Inputs:**
   - Input: `upsit_total_score = 999`, `rbdsq_total = -25`.
   - Behavior: Input values were clamped to $[0, 40]$ and $[0, 13]$; structured warning logged; risk calculation completed without software crash.
2. **Invalid Demographics:**
   - Input: `age = -15.0`.
   - Behavior: Clamped to neutral reference age ($65.0$); audit warning appended to output payload.
3. **Corrupted / Unreadable Image File:**
   - Input: Truncated binary string passed as retinal fundus JPEG.
   - Behavior: Vessel segmentation raised a trapped `ImageQualityException`; retina modality marked as `missing` ($p_{\text{ret}} = 0$); remaining 4 modalities processed smoothly.
4. **Empty Payload (All Modalities Missing):**
   - Input: `{}` (zero features provided).
   - Behavior: System gracefully outputted default uninformative risk estimate ($0.50$), uncertainty set to maximum ($1.00$), and explicit warning: *"Zero active modalities: cannot compute meaningful risk estimate"*.
- **Result Location:** Verified in Phase 10 test suite (`tests/` and `evaluation/FINAL_EVALUATION.md`).

---

## 8. Experiment 7: Reproducibility & Determinism Tests

### 8.1 Protocol & Objective
Verify that identical inputs produce identical risk estimates, identical gate weights, and identical top SHAP features across multiple runs, verifying deterministic seeding.

### 8.2 Protocol Execution
- Global random seed `seed = 42` enforced across NumPy, PyTorch, Scikit-Learn, and Python `random`.
- Repeated inference executed three times on the test split:
  - Max absolute difference in risk score: $\Delta \hat{y} < 10^{-6}$.
  - Max absolute difference in gate weights: $\Delta \alpha < 10^{-6}$.
  - Rank agreement of top-5 SHAP features: $100\%$ concordance.
- **Result Location:** `evaluation/leakage_report.json` and `evaluation/FINAL_EVALUATION.md`.
