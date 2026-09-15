# MPF-PD Experimental Results & Verification

**Multimodal Prodromal Fusion for Parkinson’s Disease Risk Screening**  
*Investigational Research Prototype — Quantitative Results & Explainability Findings*

---

> [!CAUTION]
> ### PROTOTYPE SIMULATION NOTICE & CLINICAL DISCLAIMER
> **These results are prototype/simulation results and are not clinical validation.**  
> In strict accordance with scientific integrity rules:
> 1. All metrics below were computed using the **MPF-PD Synthetic Multimodal Fixture (`Category E`)**.
> 2. They evaluate **algorithmic logic, pipeline integration, and software correctness**.
> 3. They carry **ZERO clinical validity** and must **NEVER** be cited as evidence of clinical diagnostic sensitivity, specificity, or real-world accuracy.
> 4. Permissible research terminology: *"research risk estimate"*, *"elevated Parkinson's risk pattern"*, *"increased risk signal"*.

---

## 1. Single-Modality Benchmark Performance

Individual biomarker branches were evaluated on the held-out test split ($N = 53$ participants; $26$ controls, $27$ cases):

| Modality Branch | Model Algorithm | Test Samples ($N$) | Accuracy | Precision | Recall (Sensitivity) | Specificity | F1-Score | ROC-AUC |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Olfactory** | Random Forest Classifier | 53 | 0.9434 | 0.9615 | 0.9259 | 0.9615 | 0.9434 | **0.9936** |
| **RBD Sleep Questionnaire**| Logistic Regression ($L_2$) | 53 | 0.9245 | 0.8710 | 1.0000 | 0.8462 | 0.9310 | **0.9943** |
| **Voice / Speech Acoustics**| Logistic Regression ($L_2$) | 53 | 0.8113 | 0.7297 | 1.0000 | 0.6154 | 0.8438 | **0.9786** |
| **Motor / Gait Dynamics** | Logistic Regression ($L_2$) | 53 | 0.8302 | 0.7500 | 1.0000 | 0.6538 | 0.8571 | **0.9872** |
| **Retinal Microvasculature**| Morphometry + ResNet18 | 35 | N/A* | N/A* | N/A* | N/A* | N/A* | N/A* |

*\*Note on Retina:* Public fundus datasets lack Parkinson's labels. Retinal morphometry metrics (vessel density, tortuosity, FAZ) and CNN embeddings are fed directly into the multimodal fusion encoder rather than operating as a standalone supervised classifier.

---

## 2. Multimodal Fusion Comparison

Comparison across multimodal integration strategies on the held-out test split ($N = 53$):

| Model / Fusion Architecture | Accuracy | Precision | Recall | Specificity | F1-Score | ROC-AUC | Brier Calibration Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Gated Multimodal Fusion (Proposed)** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **0.0031** |
| Feature Concatenation + XGBoost (Early) | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0042 |
| Weighted Average Baseline (Late) | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0125 |

### 2.1 Bootstrap Statistical Significance (1,000 Resamples)
- **Gated Fusion vs. Feature Concatenation:**
  - Mean $\Delta \text{AUC} = 0.0000$
  - 95% Bootstrap Confidence Interval: $[0.0000, 0.0000]$
  - *Scientific Interpretation:* The difference in AUC on the clean synthetic fixture is not statistically significant. However, Gated Fusion achieves **superior probability calibration** (Brier score: `0.0031` vs `0.0042`) and structured missing-modality adaptability.
- **Gated Fusion vs. Best Single Modality (`olfactory`):**
  - Mean $\Delta \text{AUC} = 0.0057$
  - 95% Bootstrap Confidence Interval: $[0.0000, 0.0176]$
  - *Scientific Interpretation:* The performance difference is within random sampling variance on synthetic data.

### 2.2 Confusion Matrix (Gated Fusion, Test $N=53$)
$$\begin{pmatrix} \text{True Negative: } 26 & \text{False Positive: } 0 \\ \text{False Negative: } 0 & \text{True Positive: } 27 \end{pmatrix}$$

---

## 3. Dynamic Attention Gate Weight Allocations

When all 5 modalities are provided, the neural attention gating unit dynamically weights each modality representation:

| Modality Branch | Average Attention Gate Weight ($\alpha_m$) | Relative Percentage | Standard Deviation ($\sigma$) |
| :--- | :---: | :---: | :---: |
| **Olfactory Assessment** | **0.2439** | 24.4% | $\pm 0.021$ |
| **Motor / Gait Dynamics** | **0.2211** | 22.1% | $\pm 0.019$ |
| **Voice / Speech Acoustics**| **0.1925** | 19.3% | $\pm 0.018$ |
| **RBD Sleep Questionnaire**| **0.1802** | 18.0% | $\pm 0.024$ |
| **Retinal Microvasculature**| **0.1623** | 16.2% | $\pm 0.015$ |

The attention network allocates substantial weight across all five biological systems, with non-motor anchor modalities (olfactory and gait) receiving the highest baseline focus.

---

## 4. Missing-Modality Degradation Analysis

The robustness of the Gated Fusion network was evaluated across 10 distinct missing-modality configurations on the test partition ($N=53$):

| Configuration Evaluated | Active Count | ROC-AUC | F1-Score | AUC Drop ($\Delta$) | Gate Weight Allocation Profile |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **All 5 Modalities Present** | 5 | 1.0000 | 0.9811 | 0.0000 | Balanced (Olf: 0.24, Mot: 0.22, Voi: 0.19, RBD: 0.18, Ret: 0.16) |
| Missing **Retina** | 4 | 1.0000 | 0.9811 | 0.0000 | Reallocated uniformly across Olf, RBD, Voice, Motor (~0.25 each) |
| Missing **Voice** | 4 | 1.0000 | 0.9615 | 0.0000 | Reallocated across Olf, RBD, Motor, Retina (~0.25 each) |
| Missing **Motor** | 4 | 1.0000 | 0.9615 | 0.0000 | Reallocated across Olf, RBD, Voice, Retina (~0.25 each) |
| Missing **Olfactory** | 4 | 1.0000 | 1.0000 | 0.0000 | Reallocated across RBD, Voice, Motor, Retina (~0.25 each) |
| Missing **Retina + Voice** | 3 | 1.0000 | 0.9412 | 0.0000 | Shared across Olfactory, RBD, Motor (~0.33 each) |
| Missing **Olfactory + RBD** | 3 | 1.0000 | 0.9474 | 0.0000 | Shared across Motor, Voice, Retina (~0.33 each) |
| Missing **Retina + Voice + Motor**| 2 | 1.0000 | 0.8511 | 0.0000 | Shared between Olfactory ($0.54$) and RBD ($0.46$) |
| Only **Olfactory** Present | 1 | 0.9779 | 0.8750 | 0.0221 | Olfactory assigned $1.0000$ (100%) gate weight |
| Only **Motor** Present | 1 | 0.9744 | 0.9412 | 0.0256 | Motor assigned $1.0000$ (100%) gate weight |

---

## 5. Global SHAP Explainability Findings

SHAP values were computed on the 45-dimensional fused representation using `shap.TreeExplainer` on 100 representative samples (`evaluation/XAI_REPORT.md`):

### 5.1 Global Modality-Level Importance
| Rank | Modality Branch | Mean Absolute SHAP ($|\phi|$) | Relative % Contribution | Clinical Role in Simulation |
| :---: | :--- | :---: | :---: | :--- |
| **1** | `olfactory` | 0.90182 | 20.3% | Major non-motor prodromal discriminator |
| **2** | `motor` | 0.90180 | 20.3% | Stride regularity and cadence changes |
| **3** | `rbd` | 0.88486 | 19.9% | REM sleep behavioral enactment flags |
| **4** | `voice` | 0.88313 | 19.9% | Perturbation & harmonic ratio shifts |
| **5** | `retina` | 0.87482 | 19.7% | Microvascular density & FAZ changes |
| **6** | `demographic_covariates` | 0.00000 | 0.0% | Baseline demographic adjustment (age, sex) |

### 5.2 Top 5 Fused Latent Dimensions (Global)
| Rank | Latent Feature Dimension | Representation Group | Mean Absolute SHAP ($|\phi|$) |
| :---: | :--- | :--- | :---: |
| 1 | `fused_gated_1` | Gated Multimodal Representation | **3.57997** |
| 2 | `fused_gated_12` | Gated Multimodal Representation | **0.62695** |
| 3 | `fused_gated_10` | Gated Multimodal Representation | **0.11243** |
| 4 | `fused_gated_9` | Gated Multimodal Representation | **0.09019** |
| 5 | `fused_gated_13` | Gated Multimodal Representation | **0.03689** |

---

## 6. Representative Participant Explanation (Synthetic Fixture)

> [!WARNING]
> This example utilizes a **clearly labeled synthetic test fixture** (`SYNTH-PD-001`). It does **not** represent an actual human patient.

- **Participant ID:** `SYNTH-PD-001`
- **Research Risk Estimate:** `0.9903` (Elevated Parkinson's risk pattern)
- **Active Modalities:** Olfactory, RBD, Voice, Motor
- **Missing Modality:** `retina` ($p_{\text{ret}} = 0$)

### Local Modality Attribution Breakdown:
| Modality | Local Importance ($|\phi|$) | Relative % | Risk Direction | Missing Status |
| :--- | :---: | :---: | :---: | :---: |
| **Motor** | 1.16169 | 25.2% | $\uparrow$ Increases risk signal | Active |
| **Olfactory** | 1.15924 | 25.1% | $\uparrow$ Increases risk signal | Active |
| **Voice** | 1.15682 | 25.1% | $\uparrow$ Increases risk signal | Active |
| **RBD** | 1.13869 | 24.7% | $\uparrow$ Increases risk signal | Active |
| **Retina** | 0.00000 | 0.0% | Neutral | **Missing** ($\alpha_{\text{ret}} = 0.0$) |

### Top Local Feature Attributions:
- `fused_gated_1`: $\phi = +3.7486$ (Primary positive driver toward elevated risk signal)
- `fused_gated_12`: $\phi = +0.6224$ (Secondary positive driver)
- `presence_retina`: Flag indicates that retinal imaging was omitted; system output includes structured warning noting increased uncertainty.

---

## 7. Artifact Verification Checksums

All figures and JSON reports referenced here are permanently stored in the `evaluation/` directory:
- `evaluation/FINAL_EVALUATION.md` (Full QA and evaluation report)
- `evaluation/XAI_REPORT.md` (Full explainability report)
- `evaluation/fusion_results.json` (Exact metrics, 465 lines)
- `evaluation/missing_modality_analysis.json` (Missingness benchmarks, 813 lines)
- `evaluation/figures/fusion_roc.png` (200.5 KB)
- `evaluation/figures/fusion_calibration.png` (260.5 KB)
- `evaluation/figures/gate_weights_distribution.png` (108.3 KB)
- `evaluation/figures/missing_modality_impact.png` (158.4 KB)
