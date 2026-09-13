"""
Training Pipeline for Multimodal Prodromal Fusion (MPF-PD Phase 6).

Executes:
1. Multimodal data verification and synthetic fixture loading (simulation mode).
2. Disjoint participant-level train/validation/test split.
3. Preprocessor fitting strictly on training split.
4. Training & evaluating all 8 comparison models:
   - 5 single-modality models (olfactory, rbd, voice, motor, retina)
   - Simple concatenation + XGBoost
   - Weighted average of single modality risk scores
   - Gated Multimodal Fusion + XGBoost
5. Statistical significance comparison (bootstrap CI for ROC-AUC).
6. Serializing model artifacts to models/fusion/ and metrics to evaluation/fusion_results.json.

SCIENTIFIC HONESTY:
- Operates in PROTOTYPE SIMULATION mode.
- Explicitly states no clinical validity.
- Preserves participant-level disjoint splits with zero leakage.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
import joblib
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from xgboost import XGBClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression

from src.fusion.dataset import (
    build_multimodal_dataset,
    MODALITIES,
    RBD_FEATURES,
)
from src.fusion.gated_fusion import GatedMultimodalFusion
from src.fusion.evaluate import compute_binary_metrics, compare_auc_significance
from src.olfactory.features import FEATURE_COLUMNS as OLFACTORY_FEATURES
from src.voice.features import TABULAR_FEATURE_NAMES as VOICE_FEATURES
from src.motor.features import MOTOR_FEATURE_NAMES
from src.retina.vessel_features import RETINA_FEATURE_NAMES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("mpf.fusion.train")

MODALITY_FEATURE_COLS = {
    "olfactory": OLFACTORY_FEATURES,
    "rbd": RBD_FEATURES,
    "voice": VOICE_FEATURES,
    "motor": MOTOR_FEATURE_NAMES,
    "retina": RETINA_FEATURE_NAMES + [f"retina_emb_{d}" for d in range(16)],
}


def fit_preprocessors(
    df_train: pd.DataFrame
) -> Tuple[Dict[str, SimpleImputer], Dict[str, StandardScaler], SimpleImputer, StandardScaler]:
    """
    Fit modality-specific and demographic imputers and scalers ONLY on training data.
    """
    modality_imputers = {}
    modality_scalers = {}

    for mod, cols in MODALITY_FEATURE_COLS.items():
        imp = SimpleImputer(strategy="median")
        scaler = StandardScaler()
        
        # Fit on available training features for that modality
        X_train_mod = df_train[cols].values.astype(float)
        # If all values are NaN in training (unlikely), default to 0
        if np.all(np.isnan(X_train_mod)):
            imp.fit(np.zeros_like(X_train_mod))
            scaler.fit(np.zeros_like(X_train_mod))
        else:
            imp.fit(X_train_mod)
            X_imp = imp.transform(X_train_mod)
            scaler.fit(X_imp)

        modality_imputers[mod] = imp
        modality_scalers[mod] = scaler

    # Demographic preprocessors (age, sex, provenance dummy)
    demo_imp = SimpleImputer(strategy="median")
    demo_scaler = StandardScaler()

    X_demo = df_train[["age", "sex"]].values.astype(float)
    # Provenance dummy: 1 for simulation fixture
    prov_dummy = np.ones((len(df_train), 1), dtype=float)
    X_demo_full = np.hstack([X_demo, prov_dummy])

    demo_imp.fit(X_demo_full)
    demo_scaler.fit(demo_imp.transform(X_demo_full))

    return modality_imputers, modality_scalers, demo_imp, demo_scaler


def transform_data(
    df: pd.DataFrame,
    modality_imputers: Dict[str, SimpleImputer],
    modality_scalers: Dict[str, StandardScaler],
    demo_imp: SimpleImputer,
    demo_scaler: StandardScaler,
) -> Tuple[Dict[str, np.ndarray], np.ndarray, np.ndarray, np.ndarray]:
    """
    Transform DataFrame into normalized per-modality arrays, presence flags, demographics, and labels.
    Missing modalities are kept as zero vectors in normalized space.
    """
    modality_arrays = {}
    presence_list = []

    for mod in MODALITIES:
        cols = MODALITY_FEATURE_COLS[mod]
        X_raw = df[cols].values.astype(float)
        pres = df[f"{mod}_present"].values.astype(float)[:, None]
        presence_list.append(pres)

        # Impute and scale
        X_imp = modality_imputers[mod].transform(X_raw)
        X_scaled = modality_scalers[mod].transform(X_imp)

        # Zero out where modality is missing
        X_masked = X_scaled * pres
        modality_arrays[mod] = X_masked

    presence_flags = np.hstack(presence_list)  # (N, 5)

    # Demographics
    X_demo = df[["age", "sex"]].values.astype(float)
    prov_dummy = np.ones((len(df), 1), dtype=float)
    X_demo_full = np.hstack([X_demo, prov_dummy])
    X_demo_scaled = demo_scaler.transform(demo_imp.transform(X_demo_full))

    y = df["diagnosis"].values.astype(int)

    return modality_arrays, presence_flags, X_demo_scaled, y


def train_single_modality_baselines(
    modality_arrays_train: Dict[str, np.ndarray],
    modality_arrays_val: Dict[str, np.ndarray],
    modality_arrays_test: Dict[str, np.ndarray],
    df_train: pd.DataFrame,
    df_val: pd.DataFrame,
    df_test: pd.DataFrame,
    y_train: np.ndarray,
    y_val: np.ndarray,
    y_test: np.ndarray,
    seed: int = 42,
) -> Tuple[Dict[str, Any], Dict[str, np.ndarray], Dict[str, np.ndarray]]:
    """
    Train and evaluate 5 single-modality baseline models on participants who have that modality present.
    """
    metrics = {}
    val_probs = {}
    test_probs = {}

    for mod in MODALITIES:
        train_mask = df_train[f"{mod}_present"] == 1
        val_mask = df_val[f"{mod}_present"] == 1
        test_mask = df_test[f"{mod}_present"] == 1

        X_tr = modality_arrays_train[mod][train_mask]
        y_tr = y_train[train_mask]

        X_v = modality_arrays_val[mod]
        X_te = modality_arrays_test[mod]

        clf = XGBClassifier(
            n_estimators=50,
            max_depth=3,
            learning_rate=0.08,
            random_state=seed,
            eval_metric="logloss",
        )
        clf.fit(X_tr, y_tr)

        # Predict probabilities (for all participants, though missing modality will yield model output on 0)
        p_val = clf.predict_proba(X_v)[:, 1]
        p_test = clf.predict_proba(X_te)[:, 1]

        # For participants missing this modality, set uninformative 0.5 risk
        p_val_adj = np.where(val_mask, p_val, 0.5)
        p_test_adj = np.where(test_mask, p_test, 0.5)

        val_probs[mod] = p_val_adj
        test_probs[mod] = p_test_adj

        # Metrics on participants who actually had the modality
        val_m = compute_binary_metrics(y_val[val_mask], p_val[val_mask])
        test_m = compute_binary_metrics(y_test[test_mask], p_test[test_mask])

        metrics[f"{mod}_only"] = {
            "validation": val_m,
            "test": test_m,
            "participants_present_train": int(train_mask.sum()),
            "participants_present_val": int(val_mask.sum()),
            "participants_present_test": int(test_mask.sum()),
        }

    return metrics, val_probs, test_probs


def train_concatenation_baseline(
    modality_arrays_train: Dict[str, np.ndarray],
    modality_arrays_val: Dict[str, np.ndarray],
    modality_arrays_test: Dict[str, np.ndarray],
    presence_train: np.ndarray,
    presence_val: np.ndarray,
    presence_test: np.ndarray,
    demo_train: np.ndarray,
    demo_val: np.ndarray,
    demo_test: np.ndarray,
    y_train: np.ndarray,
    y_val: np.ndarray,
    y_test: np.ndarray,
    seed: int = 42,
) -> Tuple[Dict[str, Any], np.ndarray, np.ndarray, XGBClassifier]:
    """
    Concatenation Baseline: Concat all modality features + presence flags + demo into one wide vector.
    """
    def concat_all(arrays_dict, presence, demo):
        mods_stacked = np.hstack([arrays_dict[m] for m in MODALITIES])
        return np.hstack([mods_stacked, presence, demo])

    X_tr = concat_all(modality_arrays_train, presence_train, demo_train)
    X_v = concat_all(modality_arrays_val, presence_val, demo_val)
    X_te = concat_all(modality_arrays_test, presence_test, demo_test)

    clf = XGBClassifier(
        n_estimators=80,
        max_depth=3,
        learning_rate=0.05,
        random_state=seed,
        eval_metric="logloss",
    )
    clf.fit(X_tr, y_train)

    p_val = clf.predict_proba(X_v)[:, 1]
    p_test = clf.predict_proba(X_te)[:, 1]

    val_m = compute_binary_metrics(y_val, p_val)
    test_m = compute_binary_metrics(y_test, p_test)

    metrics = {
        "validation": val_m,
        "test": test_m,
        "feature_dim": int(X_tr.shape[1]),
    }

    return metrics, p_val, p_test, clf


def train_weighted_average_baseline(
    val_probs_dict: Dict[str, np.ndarray],
    test_probs_dict: Dict[str, np.ndarray],
    presence_val: np.ndarray,
    presence_test: np.ndarray,
    y_val: np.ndarray,
    y_test: np.ndarray,
) -> Tuple[Dict[str, Any], np.ndarray, np.ndarray]:
    """
    Weighted Average Baseline: Averages available modality probabilities.
    """
    val_matrix = np.column_stack([val_probs_dict[m] for m in MODALITIES])  # (N_val, 5)
    test_matrix = np.column_stack([test_probs_dict[m] for m in MODALITIES])  # (N_test, 5)

    # Weight proportional to presence flag
    denom_val = np.maximum(presence_val.sum(axis=1, keepdims=True), 1.0)
    denom_test = np.maximum(presence_test.sum(axis=1, keepdims=True), 1.0)

    p_val = (val_matrix * presence_val).sum(axis=1) / denom_val.squeeze(-1)
    p_test = (test_matrix * presence_test).sum(axis=1) / denom_test.squeeze(-1)

    val_m = compute_binary_metrics(y_val, p_val)
    test_m = compute_binary_metrics(y_test, p_test)

    metrics = {
        "validation": val_m,
        "test": test_m,
        "weighting_strategy": "uniform_over_present_modalities",
    }

    return metrics, p_val, p_test


def train_gated_fusion_model(
    modality_arrays_train: Dict[str, np.ndarray],
    modality_arrays_val: Dict[str, np.ndarray],
    modality_arrays_test: Dict[str, np.ndarray],
    presence_train: np.ndarray,
    presence_val: np.ndarray,
    presence_test: np.ndarray,
    demo_train: np.ndarray,
    demo_val: np.ndarray,
    demo_test: np.ndarray,
    y_train: np.ndarray,
    y_val: np.ndarray,
    y_test: np.ndarray,
    embedding_dim: int = 32,
    epochs: int = 40,
    lr: float = 1e-3,
    batch_size: int = 32,
    seed: int = 42,
) -> Tuple[GatedMultimodalFusion, XGBClassifier, Dict[str, Any], np.ndarray, np.ndarray, Dict[str, float]]:
    """
    Train GatedMultimodalFusion representation network using PyTorch with masked multimodal training,
    then train XGBoost classifier on extracted fused representations.
    """
    torch.manual_seed(seed)
    np.random.seed(seed)

    modality_dims = {m: modality_arrays_train[m].shape[1] for m in MODALITIES}

    fusion_net = GatedMultimodalFusion(
        modality_dims=modality_dims,
        embedding_dim=embedding_dim,
        demo_dim=demo_train.shape[1],
        fusion_mechanism="gated_attention",
        missing_modality_strategy="learnable_token",
        mask_dropout_rate=0.20,
        seed=seed,
    )

    optimizer = torch.optim.AdamW(fusion_net.parameters(), lr=lr, weight_decay=1e-4)
    criterion = nn.BCELoss()

    # Convert training data to tensors
    tensors_train = {m: torch.tensor(modality_arrays_train[m], dtype=torch.float32) for m in MODALITIES}
    t_pres_tr = torch.tensor(presence_train, dtype=torch.float32)
    t_demo_tr = torch.tensor(demo_train, dtype=torch.float32)
    t_y_tr = torch.tensor(y_train, dtype=torch.float32).unsqueeze(-1)

    tensors_val = {m: torch.tensor(modality_arrays_val[m], dtype=torch.float32) for m in MODALITIES}
    t_pres_v = torch.tensor(presence_val, dtype=torch.float32)
    t_demo_v = torch.tensor(demo_val, dtype=torch.float32)
    t_y_v = torch.tensor(y_val, dtype=torch.float32).unsqueeze(-1)

    dataset_tr = TensorDataset(
        tensors_train["olfactory"],
        tensors_train["rbd"],
        tensors_train["voice"],
        tensors_train["motor"],
        tensors_train["retina"],
        t_pres_tr,
        t_demo_tr,
        t_y_tr,
    )
    dataloader_tr = DataLoader(dataset_tr, batch_size=batch_size, shuffle=True)

    # Train representation network with early stopping on validation loss
    best_val_loss = float("inf")
    best_state = None

    fusion_net.train()
    for epoch in range(epochs):
        fusion_net.train()
        for b_olf, b_rbd, b_vox, b_mot, b_ret, b_pres, b_demo, b_y in dataloader_tr:
            optimizer.zero_grad()
            b_mods = {
                "olfactory": b_olf,
                "rbd": b_rbd,
                "voice": b_vox,
                "motor": b_mot,
                "retina": b_ret,
            }
            probs, _, _ = fusion_net(b_mods, b_pres, b_demo)
            loss = criterion(probs, b_y)
            loss.backward()
            optimizer.step()

        # Validation evaluation
        fusion_net.eval()
        with torch.no_grad():
            val_probs_pt, _, _ = fusion_net(tensors_val, t_pres_v, t_demo_v)
            val_loss = criterion(val_probs_pt, t_y_v).item()
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_state = {k: v.cpu().clone() for k, v in fusion_net.state_dict().items()}

    if best_state is not None:
        fusion_net.load_state_dict(best_state)

    fusion_net.eval()

    # Extract fused embeddings for XGBoost training
    tensors_test = {m: torch.tensor(modality_arrays_test[m], dtype=torch.float32) for m in MODALITIES}
    t_pres_te = torch.tensor(presence_test, dtype=torch.float32)
    t_demo_te = torch.tensor(demo_test, dtype=torch.float32)

    with torch.no_grad():
        fused_tr, _ = fusion_net.extract_fused_representation(tensors_train, t_pres_tr, t_demo_tr)
        fused_v, val_gates = fusion_net.extract_fused_representation(tensors_val, t_pres_v, t_demo_v)
        fused_te, _ = fusion_net.extract_fused_representation(tensors_test, t_pres_te, t_demo_te)

    X_fused_train = fused_tr.numpy()
    X_fused_val = fused_v.numpy()
    X_fused_test = fused_te.numpy()

    # Train XGBoost on fused representations
    final_clf = XGBClassifier(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=seed,
        eval_metric="logloss",
    )
    final_clf.fit(X_fused_train, y_train)

    p_val = final_clf.predict_proba(X_fused_val)[:, 1]
    p_test = final_clf.predict_proba(X_fused_test)[:, 1]

    val_m = compute_binary_metrics(y_val, p_val)
    test_m = compute_binary_metrics(y_test, p_test)

    # Calculate average gate weights across validation set
    avg_gate_weights = {
        m: float(np.round(val_gates[:, i].mean().item(), 4))
        for i, m in enumerate(MODALITIES)
    }

    metrics = {
        "validation": val_m,
        "test": test_m,
        "fused_embedding_dim": int(X_fused_train.shape[1]),
        "average_gate_weights": avg_gate_weights,
    }

    return fusion_net, final_clf, metrics, p_val, p_test, avg_gate_weights


def run_fusion_pipeline(
    output_model_dir: str = "models/fusion",
    output_eval_path: str = "evaluation/fusion_results.json",
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Execute full Phase 6 training, baseline comparison, and artifact saving.
    """
    Path(output_model_dir).mkdir(parents=True, exist_ok=True)
    Path(output_eval_path).parent.mkdir(parents=True, exist_ok=True)

    logger.info("Step 1: Building multimodal dataset fixture and participant splits...")
    dataset_dict = build_multimodal_dataset(seed=seed)
    df_train = dataset_dict["df_train"]
    df_val = dataset_dict["df_val"]
    df_test = dataset_dict["df_test"]

    logger.info(
        f"Participant counts — Train: {len(df_train)}, Val: {len(df_val)}, Test: {len(df_test)}"
    )

    logger.info("Step 2: Fitting preprocessors strictly on training data...")
    mod_imp, mod_scl, demo_imp, demo_scl = fit_preprocessors(df_train)

    mod_tr, pres_tr, demo_tr, y_tr = transform_data(df_train, mod_imp, mod_scl, demo_imp, demo_scl)
    mod_v, pres_v, demo_v, y_v = transform_data(df_val, mod_imp, mod_scl, demo_imp, demo_scl)
    mod_te, pres_te, demo_te, y_te = transform_data(df_test, mod_imp, mod_scl, demo_imp, demo_scl)

    all_metrics: Dict[str, Any] = {}

    logger.info("Step 3: Training single-modality baselines...")
    single_metrics, s_val_probs, s_test_probs = train_single_modality_baselines(
        mod_tr, mod_v, mod_te,
        df_train, df_val, df_test,
        y_tr, y_v, y_te,
        seed=seed,
    )
    all_metrics.update(single_metrics)

    logger.info("Step 4: Training concatenation baseline...")
    concat_metrics, concat_p_val, concat_p_test, concat_clf = train_concatenation_baseline(
        mod_tr, mod_v, mod_te,
        pres_tr, pres_v, pres_te,
        demo_tr, demo_v, demo_te,
        y_tr, y_v, y_te,
        seed=seed,
    )
    all_metrics["concatenation"] = concat_metrics

    logger.info("Step 5: Training weighted average baseline...")
    wt_avg_metrics, wt_p_val, wt_p_test = train_weighted_average_baseline(
        s_val_probs, s_test_probs,
        pres_v, pres_te,
        y_v, y_te,
    )
    all_metrics["weighted_average"] = wt_avg_metrics

    logger.info("Step 6: Training proposed Gated Multimodal Fusion + XGBoost...")
    fusion_net, final_clf, gated_metrics, gated_p_val, gated_p_test, gate_weights = train_gated_fusion_model(
        mod_tr, mod_v, mod_te,
        pres_tr, pres_v, pres_te,
        demo_tr, demo_v, demo_te,
        y_tr, y_v, y_te,
        embedding_dim=32,
        epochs=35,
        seed=seed,
    )
    all_metrics["gated_fusion"] = gated_metrics

    logger.info("Step 7: Evaluating significance vs baselines...")
    # Best single modality by test ROC-AUC
    single_aucs = {m: all_metrics[f"{m}_only"]["test"]["roc_auc"] for m in MODALITIES}
    best_single_name = max(single_aucs, key=single_aucs.get)
    best_single_test_p = s_test_probs[best_single_name]

    sig_vs_concat = compare_auc_significance(y_te, gated_p_test, concat_p_test, seed=seed)
    sig_vs_best_single = compare_auc_significance(y_te, gated_p_test, best_single_test_p, seed=seed)

    fusion_improved = (
        gated_metrics["test"]["roc_auc"] >= concat_metrics["test"]["roc_auc"] and
        gated_metrics["test"]["roc_auc"] >= single_aucs[best_single_name]
    )

    best_model_name = "gated_fusion" if fusion_improved else "concatenation"

    # Save artifacts
    logger.info("Step 8: Saving artifacts to models/fusion/...")
    model_artifact_path = Path(output_model_dir) / "classifier.joblib"
    encoder_artifact_path = Path(output_model_dir) / "fusion_encoder.pt"
    preprocessor_artifact_path = Path(output_model_dir) / "preprocessor.joblib"
    metadata_artifact_path = Path(output_model_dir) / "metadata.json"

    joblib.dump(final_clf, model_artifact_path)
    torch.save(fusion_net.state_dict(), encoder_artifact_path)
    joblib.dump({
        "modality_imputers": mod_imp,
        "modality_scalers": mod_scl,
        "demo_imputer": demo_imp,
        "demo_scaler": demo_scl,
        "modality_feature_cols": MODALITY_FEATURE_COLS,
    }, preprocessor_artifact_path)

    metadata_dict = {
        "model_type": "gated_multimodal_fusion",
        "modalities": MODALITIES,
        "embedding_dim": 32,
        "fusion_mechanism": "gated_attention",
        "missing_modality_strategy": "learnable_token",
        "training_dataset": "synthetic_fixture",
        "experiment_type": "prototype_simulation",
        "seed": seed,
        "metrics": {
            "validation": gated_metrics["validation"],
            "test": gated_metrics["test"],
        },
        "limitations": [
            "PROTOTYPE SIMULATION MODE: True same-participant multimodal data across all 5 modalities is unavailable locally.",
            "Trained on synthetic aligned multimodal fixture (Category E); metrics have ZERO clinical validity.",
            "Not a clinical diagnostic device. Risk scores are research prototype estimates only.",
            "Cross-modality interactions reflect simulated physiological correlations, not prospective patient cohorts.",
        ],
        "clinical_claim": False,
        "average_gate_weights": gate_weights,
    }

    with open(metadata_artifact_path, "w", encoding="utf-8") as f:
        json.dump(metadata_dict, f, indent=2)

    logger.info("Step 9: Saving evaluation results to evaluation/fusion_results.json...")
    fusion_results = {
        "phase": 6,
        "experiment_type": "prototype_simulation",
        "same_participant_multimodal": False,
        "dataset_provenance": dataset_dict["dataset_provenance"],
        "modalities": MODALITIES,
        "missing_modality_policy": "learnable_token_and_presence_gating",
        "models_compared": [
            "olfactory_only",
            "rbd_only",
            "voice_only",
            "motor_only",
            "retina_only",
            "concatenation",
            "weighted_average",
            "gated_fusion",
        ],
        "metrics": all_metrics,
        "best_model": best_model_name,
        "fusion_improved_over_baselines": bool(fusion_improved),
        "significance_vs_concat": sig_vs_concat,
        "significance_vs_best_single": {
            "best_single_modality": f"{best_single_name}_only",
            **sig_vs_best_single,
        },
        "missingness_rates": dataset_dict["missingness_rates"],
        "complete_samples_count": dataset_dict["complete_samples_count"],
        "total_participants": dataset_dict["total_participants"],
        "limitations": [
            "PROTOTYPE SIMULATION MODE: True same-participant multimodal data is unavailable locally.",
            "Trained on synthetic aligned multimodal fixture (Category E); metrics have ZERO clinical validity.",
            "Cross-modality interactions reflect simulated physiological correlations, not prospective patient cohorts.",
            "No clinical claims: all outputs are research prototype risk estimates only.",
        ],
        "clinical_claim": False,
        "artifact_paths": {
            "model_path": str(model_artifact_path),
            "encoder_path": str(encoder_artifact_path),
            "preprocessor_path": str(preprocessor_artifact_path),
            "metadata_path": str(metadata_artifact_path),
        },
    }

    with open(output_eval_path, "w", encoding="utf-8") as f:
        json.dump(fusion_results, f, indent=2)

    logger.info("Phase 6 training and evaluation pipeline completed successfully!")
    return fusion_results


if __name__ == "__main__":
    run_fusion_pipeline()
