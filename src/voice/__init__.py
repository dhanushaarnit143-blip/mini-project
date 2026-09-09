"""
Voice modality module for MPF-PD (Phase 3).

Provides audio quality checking, preprocessing, feature extraction,
model training, evaluation, and prediction for voice-based PD risk screening.

RESEARCH PROTOTYPE ONLY — NOT A CLINICAL DIAGNOSTIC TOOL.
All outputs are investigational risk estimates without clinical validation.

Dataset used: UCI Parkinson's Telemonitoring Dataset (uci_voice)
  - Category B: Modality-Specific Dataset
  - 42 PD patients, 5,875 recordings
  - NO healthy controls in Telemonitoring set
  - Continuous UPDRS labels (regression), binarized for classification

When real data is unavailable locally, falls back to synthetic_fixture (Category E)
and marks all metrics as experiment_type='simulation'.
"""

from src.voice.quality import check_audio_quality
from src.voice.preprocess import load_audio, preprocess_audio
from src.voice.features import extract_voice_features
from src.voice.predict import predict_voice

__all__ = [
    "check_audio_quality",
    "load_audio",
    "preprocess_audio",
    "extract_voice_features",
    "predict_voice",
]
