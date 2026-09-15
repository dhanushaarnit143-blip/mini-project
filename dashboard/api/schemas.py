"""
Pydantic Schemas for MPF-PD API (Phase 8).

Defines rigorous data models for:
- Participant demographics and identifiers
- Individual modality input & prediction payloads
- Multimodal neural fusion outputs
- Local SHAP explainability structures
- Healthcheck and system status
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Demographics(BaseModel):
    age: float = Field(..., ge=18, le=120, description="Participant age in years")
    sex: str = Field(..., description="Biological sex ('female' or 'male')")


class ModalityQuality(BaseModel):
    passed: bool = Field(True, description="Quality control check passed")
    issues: List[str] = Field(default_factory=list, description="Quality check issue messages")


class IndividualModalityResult(BaseModel):
    available: bool = Field(..., description="Whether modality was included in session")
    status: str = Field(..., description="Processing status ('success', 'missing', 'failed_qc', 'error')")
    risk_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Individual modality risk estimate")
    features: Dict[str, Any] = Field(default_factory=dict, description="Extracted features used by model")
    quality: Optional[ModalityQuality] = Field(None, description="Quality check results")
    warnings: List[str] = Field(default_factory=list, description="Modality-specific warnings")


class FusionResult(BaseModel):
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Fused multimodal risk score")
    risk_pattern: str = Field(..., description="Categorical risk pattern ('Elevated Parkinson's risk pattern detected' or 'Standard risk pattern observed')")
    fused_embedding: List[float] = Field(default_factory=list, description="Latent fused representation vector")
    modality_presence: Dict[str, bool] = Field(..., description="Presence flag per modality")
    gate_weights: Dict[str, float] = Field(..., description="Neural gating attention weights per modality")
    model_version: str = Field(..., description="Model version tag")
    experiment_type: str = Field(..., description="Experiment type ('prototype_simulation')")
    warnings: List[str] = Field(default_factory=list, description="Fusion warnings and notes")


class ExplainabilityFeature(BaseModel):
    feature_name: str
    feature_index: int
    modality_group: str
    shap_value: float
    feature_value: float
    direction: str = Field(..., description="'positive' or 'negative'")


class ExplainabilityModality(BaseModel):
    modality: str
    importance: float
    percent_contribution: float
    direction: str
    missing: bool


class ExplainabilityResult(BaseModel):
    participant_id: str
    risk_score: float
    important_modalities: List[ExplainabilityModality] = Field(default_factory=list)
    important_features: List[ExplainabilityFeature] = Field(default_factory=list)
    positive_contributors: List[ExplainabilityFeature] = Field(default_factory=list)
    negative_contributors: List[ExplainabilityFeature] = Field(default_factory=list)
    missing_modalities: List[str] = Field(default_factory=list)
    missing_modality_notes: List[str] = Field(default_factory=list)
    modality_presence: Dict[str, bool] = Field(default_factory=dict)
    gate_weights: Dict[str, float] = Field(default_factory=dict)
    shap_base_value: float = 0.5
    warnings: List[str] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    participant_id: str
    demographics: Demographics
    individual_modalities: Dict[str, IndividualModalityResult]
    fusion: FusionResult
    explainability: ExplainabilityResult
    missing_modalities: List[str]
    warnings: List[str]


class HealthResponse(BaseModel):
    status: str
    version: str
    models_loaded: Dict[str, bool]
    message: str
