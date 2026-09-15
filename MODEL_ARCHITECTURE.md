# MPF-PD Model Architecture Specification

**Multimodal Prodromal Fusion for Parkinson’s Disease Risk Screening**  
*Investigational Research Prototype — Deep Learning & Machine Learning Architecture*

---

> [!IMPORTANT]
> ### RESEARCH PROTOTYPE DISCLAIMER
> The models described herein represent an **investigational machine learning architecture**. The system is designed to explore cross-biomarker representations for research risk stratification. It **does not diagnose Parkinson’s disease** and carries **zero regulatory clearance (FDA/CE)**. All model outputs are research prototype risk estimates.

---

## 1. Architectural Overview & Component Dimensions

The MPF-PD architecture is a hybrid deep-learning and gradient-boosted tree framework. It comprises five unimodal encoders, a demographic projection module, a presence indicator layer, a dynamic neural attention gating unit, and a final tree-based risk classifier with exact Shapley value explainability.

| Subsystem / Layer | Input Dimensions | Intermediate / Embedding Dimension | Output Dimensions | Algorithm / Model Type | Artifact Storage Path |
| :--- | :---: | :---: | :---: | :--- | :--- |
| **Olfactory Encoder** | 5 | 16 (hidden) | 32 | 2-Layer MLP (ReLU) + Random Forest baseline | `models/olfactory/model.joblib` |
| **RBD Encoder** | 16 | 32 (hidden) | 32 | 2-Layer MLP (ReLU) + Logistic Regression baseline | `models/rbd/model.joblib` |
| **Voice Encoder** | 16 | 32 (hidden) | 32 | 2-Layer MLP (ReLU) + Logistic Regression baseline | `models/voice/model.joblib` |
| **Motor / Gait Encoder** | 8 | 16 (hidden) | 32 | 2-Layer MLP (ReLU) + Logistic Regression baseline | `models/motor/model.joblib` |
| **Retina Encoder** | 28 (12 morph + 16 CNN) | 64 (hidden) | 32 | ResNet18 backbone + 2-Layer MLP projection | `models/retina/metadata.json` |
| **Demographic Encoder** | 2 (Age, Sex) | 16 (hidden) | 8 | 2-Layer MLP (ReLU) | Integrated in `fusion_encoder.pt` |
| **Presence Indicators** | 5 (Binary 0/1) | N/A | 5 | Binary presence flags | Vector slice [40:45] |
| **Gated Multimodal Fusion** | $5 \times 32$ | 32 (Gated context) | 32 | Neural Attention Gate with Softmax Masking | `models/fusion/fusion_encoder.pt` |
| **Combined Fused Vector** | $32 + 8 + 5$ | N/A | **45** | Concatenation layer | Feature space for Classifier |
| **Final Risk Classifier** | 45 | 100 Trees (max_depth=3) | 1 (Risk Probability $[0, 1]$) | XGBoost Classifier (`XGBClassifier`) | `models/fusion/classifier.joblib` |
| **Explanation Engine** | 45 | Exact TreeSHAP | 45 Local + 5 Modality % | SHAP `TreeExplainer` | `evaluation/xai_*.json` |

---

## 2. Modality Preprocessing & Feature Extraction

### 2.1 Olfactory Pipeline
- **Raw Feature Set ($D=5$):**
  1. `total_score`: Integer count of correct odor identifications (UPSIT range: 0–40).
  2. `pct_correct`: Normalized score ($\text{total\_score} / 40.0$).
  3. `response_time_mean`: Average response latency in seconds across test trials.
  4. `n_errors`: Total identification errors ($40 - \text{total\_score}$).
  5. `error_pattern_flags`: Binary indicator of errors in selective high-discriminability odorants (e.g. gasoline, banana, smoke, peppermint).
- **Preprocessing:** Median imputation for missing items; standard scaling ($\mu=0, \sigma=1$) fitted strictly on the training partition.

### 2.2 REM Sleep Behavior Disorder (RBD) Pipeline
- **Raw Feature Set ($D=16$):**
  1. `rbdsq_total`: Total sum of the 13 screening items (range: 0–13).
  2. `above_cutoff_flag`: Binary indicator ($\text{rbdsq\_total} \ge 5$).
  3. `high_weight_item_flags`: Binary composite flag for aggressive dream enactment (items 6.1–6.4).
  4. `item_1` through `item_13`: Individual binary questionnaire responses.
- **Preprocessing:** Zero-imputation for unselected items; standard scaling fitted on the training partition.

### 2.3 Voice / Speech Acoustics Pipeline
- **Raw Feature Set ($D=16$):**
  1. `jitter_pct`: Local fundamental frequency perturbation percentage.
  2. `jitter_abs`: Absolute fundamental frequency perturbation in microseconds.
  3. `jitter_rap`: Relative average perturbation.
  4. `jitter_ppq5`: Five-point period perturbation quotient.
  5. `jitter_ddp`: Average absolute difference of differences between consecutive periods.
  6. `shimmer`: Local amplitude perturbation.
  7. `shimmer_db`: Local amplitude perturbation in decibels.
  8. `shimmer_apq3`: Three-point amplitude perturbation quotient.
  9. `shimmer_apq5`: Five-point amplitude perturbation quotient.
  10. `shimmer_apq11`: Eleven-point amplitude perturbation quotient.
  11. `shimmer_dda`: Average absolute difference between consecutive amplitudes.
  12. `nhr`: Noise-to-harmonics ratio.
  13. `hnr`: Harmonics-to-noise ratio in dB.
  14. `rpde`: Recurrence period density entropy.
  15. `dfa`: Detrended fluctuation analysis fractal scaling exponent.
  16. `ppe`: Pitch period entropy.
- **Preprocessing:** Log-transform on skewed perturbation metrics; standard scaling fitted on the training partition.

### 2.4 Motor & Gait Dynamics Pipeline
- **Raw Feature Set ($D=8$):**
  1. `gait_speed_m_per_s`: Estimated overground walking speed (m/s).
  2. `cadence_steps_per_min`: Walking cadence in steps per minute.
  3. `stride_interval_mean_s`: Mean stride duration in seconds.
  4. `stride_interval_cv_pct`: Coefficient of variation of stride interval ($\text{SD} / \text{Mean} \times 100$).
  5. `step_regularity`: Autocorrelation of acceleration/force at the dominant step period.
  6. `symmetry_index_pct`: Normalized difference between left and right foot stride phases.
  7. `accel_variance`: Variance of total vertical force amplitude.
  8. `stance_swing_ratio`: Ratio of ground contact duration to swing phase duration.
- **Preprocessing:** Sensor artifact clipping at physiological boundaries; standard scaling fitted on the training partition.

### 2.5 Retinal Microvasculature Pipeline
- **Raw Feature Set ($D=28$):**
  - *Vascular Morphometry ($12$ features):* `vessel_density`, `mean_vessel_diameter_px`, `vessel_tortuosity_index`, `branch_count`, `branch_point_density`, `endpoint_count`, `peripapillary_vessel_density`, `peripapillary_branch_count`, `macular_vessel_density`, `foveal_avascular_zone_area_px`, `optic_disc_detected`, `macula_detected`.
  - *CNN Visual Embedding ($16$ features):* Output of a ResNet18 convolutional neural network encoder pretrained on retinal morphology and reduced via a linear bottleneck layer to 16 dimensions.
- **Preprocessing:** Contrast-limited adaptive histogram equalization (CLAHE) on the green color channel, morphological top-hat vessel segmentation, and z-score feature scaling.

---

## 3. Modality Encoders & Shared Latent Space

Each modality branch has a dedicated multi-layer perceptron (MLP) encoder that transforms heterogeneous, variable-dimensional feature vectors into a uniform **32-dimensional latent embedding space**:

$$\mathbf{e}_m = \text{Encoder}_m(\mathbf{x}_m) = \mathbf{W}_2^{(m)} \text{ReLU}\left(\mathbf{W}_1^{(m)} \mathbf{x}_m + \mathbf{b}_1^{(m)}\right) + \mathbf{b}_2^{(m)}$$

where:
- $\mathbf{x}_m \in \mathbb{R}^{D_m}$ is the raw feature vector for modality $m \in \{\text{olfactory}, \text{rbd}, \text{voice}, \text{motor}, \text{retina}\}$.
- $\mathbf{e}_m \in \mathbb{R}^{32}$ is the projected embedding vector.
- Batch normalization and dropout ($p=0.1$) are applied during training to prevent co-adaptation.

---

## 4. Missing-Modality Policy & Gated Attention Network

In real-world clinical screening, participants rarely present with all five assessments completed simultaneously. The system addresses arbitrary missing modality combinations without crashing or corrupting the feature manifold.

### 4.1 Learnable Missing Tokens
When modality $m$ is missing:
1. The raw feature extractor is bypassed.
2. The encoder output $\mathbf{e}_m$ is replaced by a **learnable parameter vector** $\mathbf{t}_m \in \mathbb{R}^{32}$:
   $$\mathbf{e}_m = \begin{cases} \text{Encoder}_m(\mathbf{x}_m) & \text{if } p_m = 1 \\ \mathbf{t}_m & \text{if } p_m = 0 \end{cases}$$
3. The parameter $\mathbf{t}_m$ is trained end-to-end with the fusion network to represent a neutral, uninformative prior for that modality.

### 4.2 Masked Gated Attention Mechanism
An attention sub-network evaluates the relevance and presence of each modality embedding:
1. **Attention Scoring:** For each modality $m$, an unnormalized score $s_m \in \mathbb{R}$ is computed:
   $$s_m = \mathbf{v}_a^\top \tanh\left(\mathbf{W}_a \mathbf{e}_m + \mathbf{b}_a\right)$$
   where $\mathbf{W}_a \in \mathbb{R}^{16 \times 32}$ and $\mathbf{v}_a \in \mathbb{R}^{16}$.
2. **Attention Masking:** To guarantee that absent modalities do not contribute spurious information to the fused embedding, a large negative mask is applied:
   $$s'_m = \begin{cases} s_m & \text{if } p_m = 1 \\ -10^9 & \text{if } p_m = 0 \end{cases}$$
3. **Softmax Gate Weights:** Dynamic gate weights $\alpha_m$ are calculated:
   $$\alpha_m = \frac{\exp(s'_m)}{\sum_{k=1}^5 \exp(s'_k)}$$
   - If modality $m$ is absent, $\alpha_m = 0.0000$.
   - The gate weights across present modalities strictly sum to $1.0$: $\sum_{m=1}^5 \alpha_m = 1.0$.
   - In the extreme boundary case where all 5 modalities are missing ($\sum p_k = 0$), uniform weights $\alpha_m = 0.20$ are assigned to avoid division by zero.
4. **Weighted Multimodal Aggregation:**
   $$\mathbf{z}_{\text{gated}} = \sum_{m=1}^5 \alpha_m \mathbf{e}_m \in \mathbb{R}^{32}$$

---

## 5. Demographic Integration & Final Feature Representation

To control for physiological covariates without diluting biomarker gate weights, demographic features (age and sex) are encoded through a parallel projection branch:
$$\mathbf{z}_{\text{demo}} = \text{Encoder}_{\text{demo}}(\mathbf{x}_{\text{demo}}) \in \mathbb{R}^{8}$$

The final representation vector $\mathbf{z}_{\text{final}} \in \mathbb{R}^{45}$ is constructed by direct concatenation:
$$\mathbf{z}_{\text{final}} = \Big[ \underbrace{\mathbf{z}_{\text{gated}}}_{\text{Indices } 0..31} \;\Big\|\; \underbrace{\mathbf{z}_{\text{demo}}}_{\text{Indices } 32..39} \;\Big\|\; \underbrace{\mathbf{p}}_{\text{Indices } 40..44} \Big] \in \mathbb{R}^{45}$$

where $\mathbf{p} = [p_{\text{olf}}, p_{\text{rbd}}, p_{\text{voi}}, p_{\text{mot}}, p_{\text{ret}}] \in \{0, 1\}^5$ indicates modality presence. Concatenating $\mathbf{p}$ enables the final classifier to learn distinct decision boundaries under partial vs complete observation regimes.

---

## 6. Final Risk Classifier

The final classification engine is an **XGBoost Classifier** (`XGBClassifier`) trained on $\mathbf{z}_{\text{final}}$:

### 6.1 Hyperparameters
- `n_estimators`: 100
- `max_depth`: 3 (shallow trees to prevent overfitting on the compact latent space)
- `learning_rate`: 0.05
- `subsample`: 0.8
- `colsample_bytree`: 0.8
- `reg_lambda` (L2 regularization): 1.0
- `objective`: `binary:logistic`
- `eval_metric`: `logloss`

### 6.2 Output Calibration
The classifier outputs a continuous research risk probability $\hat{y} \in [0.0, 1.0]$:
$$\hat{y} = P(\text{Elevated Risk Pattern} \mid \mathbf{z}_{\text{final}})$$
Isotonic and sigmoid calibration was evaluated on the validation set, achieving an optimal Brier score of `0.0031` without post-hoc scaling distortion.

---

## 7. SHAP Explainability Engine

The explainability layer utilizes **TreeSHAP** (`shap.TreeExplainer`), which calculates mathematically exact Shapley values in polynomial time $\mathcal{O}(T L D^2)$ for the tree ensemble:

1. **Exact Feature Attribution:** For any input vector $\mathbf{z}_{\text{final}}$, the predicted log-odds $f(\mathbf{z}_{\text{final}})$ decomposes as:
   $$f(\mathbf{z}_{\text{final}}) = \phi_0 + \sum_{i=0}^{44} \phi_i$$
   where $\phi_0$ is the base expected value across the training distribution, and $\phi_i$ is the exact Shapley attribution of feature dimension $i$.
2. **Presence Flag Attribution:** Shapley values $\phi_{40} \dots \phi_{44}$ quantify the explicit direction and magnitude of risk shift caused solely by the absence or presence of a given modality.
3. **Modality-Level Attribution Redistribution:**
   Because dimensions $0 \dots 31$ represent the gated mixture $\mathbf{z}_{\text{gated}} = \sum \alpha_m \mathbf{e}_m$, the attribution of modality $m$ is derived as:
   $$\Phi_m = \alpha_m \left( \sum_{i=0}^{31} |\phi_i| \right) + |\phi_{\text{presence\_}m}|$$
   Normalized modality contribution percentages are reported to researchers via the dashboard.

---

## 8. Model Artifact Inventory

All models are serialized in standard formats with explicit checksums and metadata cards:

| Component | Path | File Format | Checksum / Size |
| :--- | :--- | :--- | :--- |
| **Fusion Gated Classifier** | `models/fusion/classifier.joblib` | Joblib / Scikit-Learn | 85.7 KB |
| **PyTorch Fusion Encoder** | `models/fusion/fusion_encoder.pt` | Torch Script / State Dict | 61.0 KB |
| **Fusion Feature Preprocessor** | `models/fusion/preprocessor.joblib`| Joblib / Pipeline | 6.2 KB |
| **Fusion Model Metadata** | `models/fusion/metadata.json` | JSON | 1.8 KB |
| **Olfactory Model Checkpoint** | `models/olfactory/model.joblib` | Joblib / Random Forest | 155.5 KB |
| **RBD Model Checkpoint** | `models/rbd/model.joblib` | Joblib / Logistic Regression | 2.9 KB |
| **Voice Model Checkpoint** | `models/voice/model.joblib` | Joblib / Logistic Regression | 2.9 KB |
| **Motor Model Checkpoint** | `models/motor/model.joblib` | Joblib / Logistic Regression | 2.2 KB |
| **Retina Model Specification** | `models/retina/metadata.json` | JSON / ResNet18 Specs | 2.4 KB |
