"""
MPF-PD Phase 7 — Explainability Report Generator.

Entry point: python -m src.explainability.generate_report

Executes the full Phase 7 XAI pipeline:
  1. Load trained fusion model artifacts.
  2. Compute global SHAP importance (across synthetic fixture).
  3. Generate a clearly-labeled sample explanation.
  4. Write evaluation/xai_global_importance.json
  5. Write evaluation/xai_sample_explanation.json
  6. Write evaluation/XAI_REPORT.md

RESEARCH PROTOTYPE ONLY. Not a diagnostic device. No clinical claims.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mpf.explainability.generate_report")

from src.explainability.shap_explainer import MPFSHAPExplainer
from src.explainability.global_importance import compute_global_importance
from src.explainability.local_explanation import explain_single, save_sample_explanation
from src.fusion.dataset import MODALITIES

GLOBAL_IMPORTANCE_PATH = "evaluation/xai_global_importance.json"
SAMPLE_EXPLANATION_PATH = "evaluation/xai_sample_explanation.json"
REPORT_PATH = "evaluation/XAI_REPORT.md"

# Clearly-labeled synthetic test fixture for the sample explanation
SYNTHETIC_SAMPLE = {
    "olfactory": {
        "total_score": 22.0,
        "pct_correct": 0.55,
        "response_time_mean": 5.1,
        "n_errors": 3,
        "error_pattern_flags": 1,
    },
    "rbd": {
        "rbdsq_total": 8.0,
        "above_cutoff_flag": 1.0,
        "high_weight_item_flags": 2.0,
        "item_1": 1, "item_2": 1, "item_3": 1, "item_4": 1,
        "item_5": 0, "item_6": 1, "item_7": 1, "item_8": 0,
        "item_9": 1, "item_10": 1, "item_11": 0, "item_12": 0, "item_13": 0,
    },
    "voice": {
        "jitter_pct": 0.0085, "jitter_abs": 0.00006,
        "jitter_rap": 0.004, "jitter_ppq5": 0.0039, "jitter_ddp": 0.012,
        "shimmer": 0.065, "shimmer_db": 0.61, "shimmer_apq3": 0.037,
        "shimmer_apq5": 0.040, "shimmer_apq11": 0.065, "shimmer_dda": 0.11,
        "nhr": 0.030, "hnr": 14.5, "rpde": 0.48, "dfa": 0.79, "ppe": 0.23,
    },
    "motor": {
        "gait_speed_m_per_s": 0.88, "cadence_steps_per_min": 93.0,
        "stride_interval_mean_s": 1.18, "stride_interval_cv_pct": 3.1,
        "step_regularity": 0.82, "symmetry_index_pct": 5.2,
        "accel_variance": 0.041, "stance_swing_ratio": 1.85,
    },
    # Retina intentionally absent — demonstrates missing modality handling
    "age": 71.0,
    "sex": "male",
}
SYNTHETIC_PARTICIPANT_ID = "SYNTH-PD-001"


def generate_markdown_report(
    global_data: dict,
    sample_explanation: dict,
    report_path: str = REPORT_PATH,
) -> None:
    """
    Write the Phase 7 XAI report to Markdown.

    Args:
        global_data:        Output from compute_global_importance().
        sample_explanation: Output from explain_single().
        report_path:        Destination file path.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    top_features = global_data["global_feature_importance"][:10]
    top_modalities = global_data["modality_importance"][:6]
    sample_pid = sample_explanation["participant_id"]
    sample_score = sample_explanation["risk_score"]
    sample_missing = sample_explanation["missing_modalities"]
    sample_top_feats = sample_explanation["important_features"][:5]
    sample_top_mods = sample_explanation["important_modalities"][:5]

    lines = [
        "# MPF-PD Phase 7 — XAI Explainability Report",
        "",
        f"> **Generated:** {now}  ",
        f"> **Experiment type:** `prototype_simulation`  ",
        f"> **Model:** Gated Multimodal Fusion → XGBoost Classifier  ",
        "",
        "> [!CAUTION]",
        "> **RESEARCH PROTOTYPE ONLY.** Explanations are decision-support artefacts for",
        "> research review. This system **does not diagnose Parkinson's disease**.",
        "> No clinical validity is claimed. All risk scores are research prototype estimates.",
        "> Requires clinician review if used in future clinical studies.",
        "",
        "---",
        "",
        "## 1. Explanation Method",
        "",
        f"| Property | Value |",
        "|---|---|",
        f"| Explanation method | `{global_data['explanation_method']}` |",
        f"| SHAP library | `shap` (TreeExplainer — exact, no surrogate) |",
        f"| Model type | `{global_data['model_type']}` |",
        f"| Fused representation dim | 45 (32 gated + 8 demo + 5 presence flags) |",
        f"| Samples used for global SHAP | {global_data['n_samples_used']} |",
        "",
        "**TreeExplainer** computes exact SHAP values for XGBoost/tree models without",
        "surrogate approximation. SHAP values are computed on the **45-dimensional fused",
        "representation** produced by the GatedMultimodalFusion encoder, not on raw",
        "biomarker features directly.",
        "",
        "---",
        "",
        "## 2. Model Explained",
        "",
        "The final classifier is an **XGBoost** model trained on a 45-dim fused vector:",
        "",
        "| Vector slice | Indices | Semantics |",
        "|---|---|---|",
        "| Gated modality vector | 0–31 | Post-attention fusion of 5 modality embeddings |",
        "| Demographic encoder | 32–39 | Age + sex projected through 2-layer MLP |",
        "| Presence flags | 40–44 | Binary: 1=modality present, 0=modality absent |",
        "",
        "Modality encoders project olfactory (5-d), RBD (16-d), voice (16-d),",
        "motor (8-d), and retina (28-d) raw features to a shared 32-d embedding space.",
        "A gated attention unit fuses these into a single 32-d vector.",
        "",
        "---",
        "",
        "## 3. Dataset Used",
        "",
        "> [!IMPORTANT]",
        "> Global SHAP importance computed on **synthetic fixture data**",
        "> (Category E — `prototype_simulation` mode).",
        "> These values have **ZERO clinical validity** and must not be reported as",
        "> validated biomarker importance rankings.",
        "",
        f"- Dataset: `synthetic_fixture_prototype_simulation`",
        f"- N samples used: {global_data['n_samples_used']}",
        f"- Modalities: {', '.join(MODALITIES)}",
        "",
        "---",
        "",
        "## 4. Global Modality Importance",
        "",
        "Modality-level importance is derived by:",
        "1. **Direct SHAP on presence flags** (indices 40–44) — measures the direct",
        "   contribution of each modality's presence/absence to the risk estimate.",
        "2. **Gate-weight attribution** of the 32-dim gated representation — the",
        "   post-attention vector is apportioned to modalities proportionally to their",
        "   average fusion gate weights.",
        "",
        "| Rank | Modality | Mean |SHAP| | % Contribution |",
        "|---|---|---|---|",
    ]

    for rank, m in enumerate(top_modalities, 1):
        miss_note = " ⚠ presence flag contributes" if "presence_" in m["modality"] else ""
        lines.append(
            f"| {rank} | `{m['modality']}` | {m['mean_abs_shap']:.5f} | "
            f"{m['percent_contribution']:.1f}%{miss_note} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 5. Top Features (Global)",
        "",
        "| Rank | Feature | Group | Mean |SHAP| |",
        "|---|---|---|---|",
    ]
    for rank, feat in enumerate(top_features, 1):
        lines.append(
            f"| {rank} | `{feat['feature_name']}` | `{feat['modality_group']}` | "
            f"{feat['mean_abs_shap']:.5f} |"
        )

    lines += [
        "",
        "> [!NOTE]",
        "> Feature names in the fused vector (`fused_gated_0..31`, `demo_enc_0..7`,",
        "> `presence_*`) refer to compressed neural representations, not raw biomarker",
        "> values. High importance on a `fused_gated_*` dimension indicates that the",
        "> gated modality fusion vector strongly influences the risk estimate, but cannot",
        "> be directly mapped to a single original feature (e.g., `jitter_pct`) without",
        "> layer-wise attribution.",
        "",
        "---",
        "",
        "## 6. Example Explanation (Synthetic Fixture)",
        "",
        "> [!WARNING]",
        f"> The following explanation uses a **clearly labeled synthetic test fixture**",
        f"> (`participant_id: {sample_pid}`, `synthetic_example: true`).",
        "> It does NOT represent a real participant. It is used for software validation only.",
        "",
        f"**Participant ID:** `{sample_pid}`  ",
        f"**Research Risk Estimate:** `{sample_score:.4f}` (elevated risk signal)  ",
        f"**Missing modalities:** `{sample_missing if sample_missing else 'none'}`  ",
        "",
        "### Top-5 features by |SHAP|:",
        "",
        "| Feature | Group | SHAP Value | Direction |",
        "|---|---|---|---|",
    ]
    for feat in sample_top_feats:
        arrow = "↑" if feat["direction"] == "positive" else "↓"
        lines.append(
            f"| `{feat['feature_name']}` | `{feat['modality_group']}` | "
            f"`{feat['shap_value']:+.4f}` | {arrow} {feat['direction']} |"
        )

    lines += [
        "",
        "### Modality contributions:",
        "",
        "| Modality | Importance | % | Direction | Missing? |",
        "|---|---|---|---|---|",
    ]
    for m in sample_top_mods:
        miss = "⚠ YES" if m["missing"] else "No"
        arrow = "↑" if m["direction"] == "positive" else ("↓" if m["direction"] == "negative" else "~")
        lines.append(
            f"| `{m['modality']}` | {m['importance']:.5f} | {m['percent_contribution']:.1f}% | "
            f"{arrow} {m['direction']} | {miss} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 7. Missing-Modality Behaviour",
        "",
        "When one or more modalities are absent:",
        "",
        "1. **Learnable missing token** — the GatedMultimodalFusion encoder substitutes",
        "   a learned placeholder embedding for the absent modality's encoder output.",
        "2. **Presence flag** — the corresponding flag (index 40–44) is set to `0`.",
        "   SHAP quantifies the direct effect of this flag on the risk estimate.",
        "3. **Gate weight redistribution** — the attention gate down-weights absent",
        "   modalities; remaining present modalities receive proportionally higher weight.",
        "4. **Uncertainty increase** — all outputs include an explicit warning that",
        "   missing modalities increase uncertainty in the research risk estimate.",
        "",
        "In the example above, **retinal data was absent**. The presence flag",
        "`presence_retina` was set to 0, and the explanation notes that the model",
        "relied more heavily on olfactory, RBD, voice, and motor signals.",
        "",
        "---",
        "",
        "## 8. Limitations",
        "",
    ]
    for lim in global_data["limitations"]:
        lines.append(f"- {lim}")

    lines += [
        "",
        "Additional limitations:",
        "- Layer-wise attribution from raw features to SHAP values in the fused space",
        "  is not implemented. Raw biomarker importance (e.g., `jitter_pct` or `vessel_density`)",
        "  cannot be directly read from these SHAP values.",
        "- Gate weights are soft attention scores and only approximate the modality",
        "  contribution to the gated vector; exact attribution would require gradient-based",
        "  or integrated-gradient methods applied to the encoder.",
        "- SHAP base value reflects the classifier's expected output on the training",
        "  distribution (synthetic fixture), not a clinically meaningful baseline.",
        "",
        "---",
        "",
        "## 9. Disclaimer",
        "",
        "> [!CAUTION]",
        "> **Explanations are decision-support artefacts for research review only.**",
        "> - Do not use these explanations to diagnose or screen for Parkinson's disease.",
        "> - Risk scores are research prototype estimates, not clinical findings.",
        "> - This system has not been validated on real patient cohorts.",
        "> - All outputs require clinician review if used in future clinical studies.",
        "",
        "---",
        "",
        "## 10. Commands to Reproduce",
        "",
        "```bash",
        "# Run full Phase 7 XAI pipeline (generates all evaluation outputs)",
        "python -m src.explainability.generate_report",
        "",
        "# Global importance only",
        "python -m src.explainability.global_importance",
        "",
        "# Sample explanation only",
        "python -m src.explainability.local_explanation",
        "",
        "# Run Phase 7 tests",
        "pytest tests/test_xai.py -v",
        "```",
        "",
        "---",
        "",
        "*MPF-PD Phase 7 XAI Report — Research Prototype — No clinical claims.*",
    ]

    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    logger.info("XAI report written to %s", report_path)


def main() -> None:
    """
    Run the full Phase 7 XAI pipeline.
    """
    logger.info("=== MPF-PD Phase 7 — Explainability Report Generator ===")

    # Load explainer once (avoids double-loading heavy artifacts)
    logger.info("Loading MPFSHAPExplainer...")
    explainer = MPFSHAPExplainer()

    # 1. Global importance
    logger.info("Step 1/3: Computing global SHAP importance...")
    global_data = compute_global_importance(
        explainer=explainer,
        output_path=GLOBAL_IMPORTANCE_PATH,
    )

    # 2. Sample explanation
    logger.info("Step 2/3: Generating sample explanation (synthetic fixture)...")
    sample_explanation = explain_single(
        inputs=SYNTHETIC_SAMPLE,
        participant_id=SYNTHETIC_PARTICIPANT_ID,
        explainer=explainer,
        is_synthetic=True,
    )
    save_sample_explanation(sample_explanation, output_path=SAMPLE_EXPLANATION_PATH)

    # 3. Markdown report
    logger.info("Step 3/3: Writing Markdown report...")
    generate_markdown_report(
        global_data=global_data,
        sample_explanation=sample_explanation,
        report_path=REPORT_PATH,
    )

    logger.info("=== Phase 7 report generation complete ===")
    logger.info("  Global importance: %s", GLOBAL_IMPORTANCE_PATH)
    logger.info("  Sample explanation: %s", SAMPLE_EXPLANATION_PATH)
    logger.info("  XAI report: %s", REPORT_PATH)

    # Summary to stdout
    print("\n" + "=" * 60)
    print("MPF-PD Phase 7 — XAI Report Summary")
    print("=" * 60)
    print(f"Explanation method : {global_data['explanation_method']}")
    print(f"Model type         : {global_data['model_type']}")
    print(f"Samples used       : {global_data['n_samples_used']}")
    print(f"Experiment type    : prototype_simulation")
    print()
    print("Top modalities (global):")
    for m in global_data["modality_importance"][:5]:
        print(f"  {m['modality']:30s}  {m['mean_abs_shap']:.5f}  ({m['percent_contribution']:.1f}%)")
    print()
    print(f"Sample explanation: participant={sample_explanation['participant_id']}, "
          f"risk_score={sample_explanation['risk_score']}")
    print(f"Missing modalities: {sample_explanation['missing_modalities']}")
    print()
    print("Outputs written:")
    print(f"  {GLOBAL_IMPORTANCE_PATH}")
    print(f"  {SAMPLE_EXPLANATION_PATH}")
    print(f"  {REPORT_PATH}")
    print()
    print("DISCLAIMER: Research prototype. Not a diagnostic device. No clinical claims.")
    print("=" * 60)


if __name__ == "__main__":
    main()
