# MPF-PD Phase 7 — XAI Explainability Report

> **Generated:** 2026-09-15 04:26 UTC  
> **Experiment type:** `prototype_simulation`  
> **Model:** Gated Multimodal Fusion → XGBoost Classifier  

> [!CAUTION]
> **RESEARCH PROTOTYPE ONLY.** Explanations are decision-support artefacts for
> research review. This system **does not diagnose Parkinson's disease**.
> No clinical validity is claimed. All risk scores are research prototype estimates.
> Requires clinician review if used in future clinical studies.

---

## 1. Explanation Method

| Property | Value |
|---|---|
| Explanation method | `shap_tree` |
| SHAP library | `shap` (TreeExplainer — exact, no surrogate) |
| Model type | `XGBClassifier` |
| Fused representation dim | 45 (32 gated + 8 demo + 5 presence flags) |
| Samples used for global SHAP | 100 |

**TreeExplainer** computes exact SHAP values for XGBoost/tree models without
surrogate approximation. SHAP values are computed on the **45-dimensional fused
representation** produced by the GatedMultimodalFusion encoder, not on raw
biomarker features directly.

---

## 2. Model Explained

The final classifier is an **XGBoost** model trained on a 45-dim fused vector:

| Vector slice | Indices | Semantics |
|---|---|---|
| Gated modality vector | 0–31 | Post-attention fusion of 5 modality embeddings |
| Demographic encoder | 32–39 | Age + sex projected through 2-layer MLP |
| Presence flags | 40–44 | Binary: 1=modality present, 0=modality absent |

Modality encoders project olfactory (5-d), RBD (16-d), voice (16-d),
motor (8-d), and retina (28-d) raw features to a shared 32-d embedding space.
A gated attention unit fuses these into a single 32-d vector.

---

## 3. Dataset Used

> [!IMPORTANT]
> Global SHAP importance computed on **synthetic fixture data**
> (Category E — `prototype_simulation` mode).
> These values have **ZERO clinical validity** and must not be reported as
> validated biomarker importance rankings.

- Dataset: `synthetic_fixture_prototype_simulation`
- N samples used: 100
- Modalities: olfactory, rbd, voice, motor, retina

---

## 4. Global Modality Importance

Modality-level importance is derived by:
1. **Direct SHAP on presence flags** (indices 40–44) — measures the direct
   contribution of each modality's presence/absence to the risk estimate.
2. **Gate-weight attribution** of the 32-dim gated representation — the
   post-attention vector is apportioned to modalities proportionally to their
   average fusion gate weights.

| Rank | Modality | Mean |SHAP| | % Contribution |
|---|---|---|---|
| 1 | `olfactory` | 0.90182 | 20.3% |
| 2 | `motor` | 0.90180 | 20.3% |
| 3 | `rbd` | 0.88486 | 19.9% |
| 4 | `voice` | 0.88313 | 19.9% |
| 5 | `retina` | 0.87482 | 19.7% |
| 6 | `demographic_covariates` | 0.00000 | 0.0% |

---

## 5. Top Features (Global)

| Rank | Feature | Group | Mean |SHAP| |
|---|---|---|---|
| 1 | `fused_gated_1` | `fused_gated_representation` | 3.57997 |
| 2 | `fused_gated_12` | `fused_gated_representation` | 0.62695 |
| 3 | `fused_gated_10` | `fused_gated_representation` | 0.11243 |
| 4 | `fused_gated_9` | `fused_gated_representation` | 0.09019 |
| 5 | `fused_gated_13` | `fused_gated_representation` | 0.03689 |
| 6 | `fused_gated_0` | `fused_gated_representation` | 0.00000 |
| 7 | `fused_gated_2` | `fused_gated_representation` | 0.00000 |
| 8 | `fused_gated_3` | `fused_gated_representation` | 0.00000 |
| 9 | `fused_gated_4` | `fused_gated_representation` | 0.00000 |
| 10 | `fused_gated_5` | `fused_gated_representation` | 0.00000 |

> [!NOTE]
> Feature names in the fused vector (`fused_gated_0..31`, `demo_enc_0..7`,
> `presence_*`) refer to compressed neural representations, not raw biomarker
> values. High importance on a `fused_gated_*` dimension indicates that the
> gated modality fusion vector strongly influences the risk estimate, but cannot
> be directly mapped to a single original feature (e.g., `jitter_pct`) without
> layer-wise attribution.

---

## 6. Example Explanation (Synthetic Fixture)

> [!WARNING]
> The following explanation uses a **clearly labeled synthetic test fixture**
> (`participant_id: SYNTH-PD-001`, `synthetic_example: true`).
> It does NOT represent a real participant. It is used for software validation only.

**Participant ID:** `SYNTH-PD-001`  
**Research Risk Estimate:** `0.9903` (elevated risk signal)  
**Missing modalities:** `['retina']`  

### Top-5 features by |SHAP|:

| Feature | Group | SHAP Value | Direction |
|---|---|---|---|
| `fused_gated_1` | `fused_gated_representation` | `+3.7486` | ↑ positive |
| `fused_gated_12` | `fused_gated_representation` | `+0.6224` | ↑ positive |
| `fused_gated_10` | `fused_gated_representation` | `+0.1160` | ↑ positive |
| `fused_gated_9` | `fused_gated_representation` | `+0.0911` | ↑ positive |
| `fused_gated_13` | `fused_gated_representation` | `+0.0383` | ↑ positive |

### Modality contributions:

| Modality | Importance | % | Direction | Missing? |
|---|---|---|---|---|
| `motor` | 1.16169 | 25.2% | ↑ positive | No |
| `olfactory` | 1.15924 | 25.1% | ↑ positive | No |
| `voice` | 1.15682 | 25.1% | ↑ positive | No |
| `rbd` | 1.13869 | 24.7% | ↑ positive | No |
| `retina` | 0.00000 | 0.0% | ~ mixed | ⚠ YES |

---

## 7. Missing-Modality Behaviour

When one or more modalities are absent:

1. **Learnable missing token** — the GatedMultimodalFusion encoder substitutes
   a learned placeholder embedding for the absent modality's encoder output.
2. **Presence flag** — the corresponding flag (index 40–44) is set to `0`.
   SHAP quantifies the direct effect of this flag on the risk estimate.
3. **Gate weight redistribution** — the attention gate down-weights absent
   modalities; remaining present modalities receive proportionally higher weight.
4. **Uncertainty increase** — all outputs include an explicit warning that
   missing modalities increase uncertainty in the research risk estimate.

In the example above, **retinal data was absent**. The presence flag
`presence_retina` was set to 0, and the explanation notes that the model
relied more heavily on olfactory, RBD, voice, and motor signals.

---

## 8. Limitations

- PROTOTYPE SIMULATION MODE: Global importance computed on synthetic fixture data. Metrics have ZERO clinical validity.
- SHAP values reflect the 45-dim fused representation, not raw biomarker features. Individual feature-level importance (e.g., jitter_pct, vessel_density) is not directly recoverable from fused SHAP without additional attribution.
- Modality-level importance for the gated vector is estimated via gate weights, which are soft attention scores rather than exact SHAP decompositions.
- No clinical claims. All outputs are research prototype estimates only.
- Do not interpret these values as validated biomarker importance rankings.

Additional limitations:
- Layer-wise attribution from raw features to SHAP values in the fused space
  is not implemented. Raw biomarker importance (e.g., `jitter_pct` or `vessel_density`)
  cannot be directly read from these SHAP values.
- Gate weights are soft attention scores and only approximate the modality
  contribution to the gated vector; exact attribution would require gradient-based
  or integrated-gradient methods applied to the encoder.
- SHAP base value reflects the classifier's expected output on the training
  distribution (synthetic fixture), not a clinically meaningful baseline.

---

## 9. Disclaimer

> [!CAUTION]
> **Explanations are decision-support artefacts for research review only.**
> - Do not use these explanations to diagnose or screen for Parkinson's disease.
> - Risk scores are research prototype estimates, not clinical findings.
> - This system has not been validated on real patient cohorts.
> - All outputs require clinician review if used in future clinical studies.

---

## 10. Commands to Reproduce

```bash
# Run full Phase 7 XAI pipeline (generates all evaluation outputs)
python -m src.explainability.generate_report

# Global importance only
python -m src.explainability.global_importance

# Sample explanation only
python -m src.explainability.local_explanation

# Run Phase 7 tests
pytest tests/test_xai.py -v
```

---

*MPF-PD Phase 7 XAI Report — Research Prototype — No clinical claims.*
