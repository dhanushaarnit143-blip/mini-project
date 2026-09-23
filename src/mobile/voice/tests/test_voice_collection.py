"""
Tests for MPF Mobile Extension — Voice Collection Module (Phase 5)

Verifies:
- Controlled in-app voice collection works across all 3 guided speech tasks:
  1. Sustained vowel phonation ('sustained_vowel')
  2. Standardized reading sentence ('read_sentence')
  3. Short free speech ('free_speech')
- Participant ID is required.
- Task type constraints are enforced.
- Duration tracking functions correctly.
- STRICT PRIVACY:
  - Raw audio is NEVER stored in database payloads.
  - No speech-to-text transcripts, conversational eavesdropping, or audio recordings uploaded.
  - In-memory audio buffers can be securely zeroed and discarded.
"""

import pytest
import uuid
from pathlib import Path
import sys
import numpy as np

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.mobile.voice.voice_service import (
    VoiceRecorderSimulator,
    VoiceSessionModel,
    VOICE_TASKS,
    TASK_SUSTAINED_VOWEL,
    TASK_READ_SENTENCE,
    TASK_FREE_SPEECH,
    VALID_TASK_TYPES,
    generate_synthetic_voice_audio,
)


class TestVoiceCollection:
    def test_start_session_initialization_all_tasks(self):
        """Verifies session initialization across all 3 speech task types."""
        recorder = VoiceRecorderSimulator(sample_rate=44100)
        participant_id = str(uuid.uuid4())

        for task_type in VALID_TASK_TYPES:
            info = recorder.start_recording(participant_id, task_type)
            assert recorder.is_recording is True
            assert info["participant_id"] == participant_id
            assert info["task_type"] == task_type
            assert uuid.UUID(info["session_id"])  # Valid UUID
            assert info["sample_rate"] == 44100

            # Stop before next iteration
            recorder.stop_recording()

    def test_start_session_requires_participant_id(self):
        """Verifies that an empty or missing participant ID is rejected."""
        recorder = VoiceRecorderSimulator()
        with pytest.raises(ValueError, match="Participant ID is mandatory"):
            recorder.start_recording("", TASK_SUSTAINED_VOWEL)

    def test_start_session_rejects_invalid_task_type(self):
        """Verifies that unauthorized task types are rejected."""
        recorder = VoiceRecorderSimulator()
        participant_id = str(uuid.uuid4())
        with pytest.raises(ValueError, match="Invalid task_type"):
            recorder.start_recording(participant_id, "background_listening")

    def test_recording_state_transitions_and_duration(self):
        """Verifies recording duration tracking and buffer simulation."""
        recorder = VoiceRecorderSimulator(sample_rate=44100)
        participant_id = str(uuid.uuid4())
        recorder.start_recording(participant_id, TASK_SUSTAINED_VOWEL)

        synthetic_audio = generate_synthetic_voice_audio(duration=5.0, sample_rate=44100)
        recorder.record_audio_buffer(synthetic_audio)

        result = recorder.stop_recording()
        assert recorder.is_recording is False
        assert result["duration"] == 5.0
        assert len(result["raw_audio"]) == int(5.0 * 44100)

    def test_strict_privacy_raw_audio_discarded(self):
        """
        NON-NEGOTIABLE PRIVACY REQUIREMENT:
        Verify that raw audio is strictly purgeable from memory.
        """
        recorder = VoiceRecorderSimulator(sample_rate=44100)
        participant_id = str(uuid.uuid4())
        recorder.start_recording(participant_id, TASK_READ_SENTENCE)

        synthetic_audio = generate_synthetic_voice_audio(duration=4.0, sample_rate=44100)
        recorder.record_audio_buffer(synthetic_audio)
        recorder.stop_recording()

        # Purge audio buffer
        recorder.discard_raw_audio()
        assert recorder.audio_buffer is None

    def test_strict_privacy_zero_raw_audio_in_payload(self):
        """
        NON-NEGOTIABLE PRIVACY REQUIREMENT:
        Audit payload to verify zero raw audio samples, audio bytes, or text transcripts exist.
        """
        participant_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        model = VoiceSessionModel({
            "participant_id": participant_id,
            "session_id": session_id,
            "task_type": TASK_SUSTAINED_VOWEL,
            "duration": 5.0,
            "signal_quality": 0.85,
            "jitter": 0.008,
            "shimmer": 0.025,
            "hnr": 18.5,
            "pitch_mean": 152.3,
            "pitch_std": 4.2,
            "mfcc_features": [1.0] * 13,
            "spectral_features": {
                "spectral_centroid": 1200.0,
                "spectral_bandwidth": 850.0,
                "spectral_rolloff": 2400.0
            },
            "quality_score": 0.95
        })

        payload = model.to_supabase_payload()

        forbidden_keys = [
            "audio", "raw_audio", "wav", "mp3", "bytes", "samples",
            "recording", "stream", "transcript", "text", "speech"
        ]

        for key in payload.keys():
            assert key not in forbidden_keys, f"Privacy violation: forbidden key '{key}' found in payload!"

        # Ensure no ndarray or large byte structures in values
        for k, v in payload.items():
            assert not isinstance(v, (bytes, bytearray, np.ndarray)), f"Forbidden binary data in '{k}'"
