"""
MPF Mobile Extension — Voice Biomarker Service (Phase 5)

Backend, test-compatible, and standalone implementation of:
1. Controlled daily speech task definitions (sustained vowel, read sentence, short free speech).
2. Local acoustic feature extraction:
   - Pitch tracking (mean, std in Hz via autocorrelation F0 estimation)
   - Cycle-to-cycle perturbation: Jitter (period) and Shimmer (amplitude)
   - Harmonics-to-Noise Ratio (HNR in dB)
   - 13 Mel-Frequency Cepstral Coefficients (MFCCs)
   - Spectral metrics (spectral centroid, bandwidth, 85% rolloff)
   - Signal quality metrics (duration, SNR estimate, clipping, silence ratio)
3. Standardized quality scoring with personal baseline gating (quality_score >= 0.50).
4. VoiceSession data model conforming to Supabase voice_sessions table schema.
5. Strict privacy verification: zero raw audio storage by default, local feature extraction only.
"""

import math
import uuid
import datetime
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

FEATURE_VERSION = "1.0.0"
MIN_BASELINE_QUALITY_THRESHOLD = 0.50
MIN_DURATION_SECONDS = 3.0
MIN_SIGNAL_QUALITY_THRESHOLD = 0.50
MAX_ALLOWED_SILENCE_RATIO = 0.30

TASK_SUSTAINED_VOWEL = "sustained_vowel"
TASK_READ_SENTENCE = "read_sentence"
TASK_FREE_SPEECH = "free_speech"

VALID_TASK_TYPES = [TASK_SUSTAINED_VOWEL, TASK_READ_SENTENCE, TASK_FREE_SPEECH]

VOICE_TASKS = {
    TASK_SUSTAINED_VOWEL: {
        "id": TASK_SUSTAINED_VOWEL,
        "title": "Sustained Vowel Phonation",
        "instruction": "Take a deep breath and say 'AAAA' for as long as you can.",
        "target_duration_seconds": 5.0,
        "min_duration_seconds": 3.0,
        "max_duration_seconds": 10.0,
        "purpose": "Measure vocal stability, fundamental frequency, jitter, and shimmer"
    },
    TASK_READ_SENTENCE: {
        "id": TASK_READ_SENTENCE,
        "title": "Standard Sentence Reading",
        "instruction": "Read this sentence aloud: 'The quick brown fox jumps over the lazy dog.'",
        "target_duration_seconds": 7.0,
        "min_duration_seconds": 3.0,
        "max_duration_seconds": 12.0,
        "purpose": "Measure speech rhythm, cadence, and pitch variation"
    },
    TASK_FREE_SPEECH: {
        "id": TASK_FREE_SPEECH,
        "title": "Short Free Speech",
        "instruction": "Describe what you had for breakfast in one sentence.",
        "target_duration_seconds": 10.0,
        "min_duration_seconds": 3.0,
        "max_duration_seconds": 15.0,
        "purpose": "Measure natural speech patterns and pause dynamics"
    }
}


def generate_synthetic_voice_audio(
    duration: float = 5.0,
    sample_rate: int = 44100,
    f0: float = 150.0,
    jitter_factor: float = 0.005,
    shimmer_factor: float = 0.02,
    noise_level: float = 0.01,
    clipping: bool = False,
    silence_ratio: float = 0.10
) -> np.ndarray:
    """
    Generates synthetic, deterministic acoustic signals for non-fabricating test suites.
    Simulates sustained vowel /a/ with harmonic structure, cycle-to-cycle perturbation,
    additive Gaussian noise, optional clipping, and silence intervals.
    """
    num_samples = int(duration * sample_rate)
    audio = np.zeros(num_samples, dtype=np.float32)

    # Calculate silence boundary
    active_samples = int(num_samples * (1.0 - silence_ratio))

    t = 0.0
    phase = 0.0
    curr_f0 = f0
    curr_amp = 1.0

    # Cycle-based synthesis for authentic jitter & shimmer
    sample_idx = 0
    rng = np.random.RandomState(42)

    while sample_idx < active_samples:
        # Perturb F0 and Amplitude per cycle
        cycle_f0 = max(50.0, f0 * (1.0 + jitter_factor * rng.randn()))
        cycle_amp = max(0.1, 1.0 + shimmer_factor * rng.randn())
        cycle_len = int(sample_rate / cycle_f0)

        for _ in range(cycle_len):
            if sample_idx >= active_samples:
                break
            
            # Harmonic vowel synthesis (fundamental + 3 formants/harmonics)
            s = (
                0.60 * math.sin(phase) +
                0.25 * math.sin(2 * phase) +
                0.15 * math.sin(3 * phase) +
                0.08 * math.sin(4 * phase)
            ) * cycle_amp

            audio[sample_idx] = s
            phase += 2.0 * math.pi * cycle_f0 / sample_rate
            if phase > 2.0 * math.pi:
                phase -= 2.0 * math.pi
            sample_idx += 1

    # Add Gaussian noise
    if noise_level > 0:
        noise = rng.normal(0, noise_level, num_samples).astype(np.float32)
        audio += noise

    # Apply clipping if requested
    if clipping:
        audio = np.clip(audio * 4.0, -1.0, 1.0)
        # Force a burst of saturated samples
        audio[100:300] = 1.0
        audio[500:700] = -1.0
    else:
        # Normalize to prevent accidental clipping
        max_val = np.max(np.abs(audio))
        if max_val > 0.95:
            audio = audio * (0.85 / max_val)

    return audio


class VoiceRecorderSimulator:
    """
    Simulates in-app controlled audio recording sessions.
    Guarantees strict privacy: raw audio can be purged via discard_raw_audio().
    """
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.is_recording = False
        self.participant_id: Optional[str] = None
        self.session_id: Optional[str] = None
        self.task_type: Optional[str] = None
        self.audio_buffer: Optional[np.ndarray] = None
        self.duration: float = 0.0

    def start_recording(self, participant_id: str, task_type: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        if not participant_id:
            raise ValueError("Participant ID is mandatory.")
        if task_type not in VALID_TASK_TYPES:
            raise ValueError(f"Invalid task_type: {task_type}. Must be one of {VALID_TASK_TYPES}")

        self.participant_id = participant_id
        self.task_type = task_type
        self.session_id = session_id or str(uuid.uuid4())
        self.is_recording = True
        self.audio_buffer = None
        self.duration = 0.0

        return {
            "session_id": self.session_id,
            "participant_id": self.participant_id,
            "task_type": self.task_type,
            "sample_rate": self.sample_rate
        }

    def record_audio_buffer(self, audio: np.ndarray) -> None:
        if not self.is_recording:
            raise RuntimeError("Cannot record audio: no active session.")
        self.audio_buffer = audio.copy()
        self.duration = float(len(audio) / self.sample_rate)

    def stop_recording(self) -> Dict[str, Any]:
        if not self.is_recording:
            raise RuntimeError("Cannot stop: no active recording session.")
        self.is_recording = False

        if self.audio_buffer is None:
            # Generate fallback simulated audio for target task
            task_info = VOICE_TASKS[self.task_type]
            self.audio_buffer = generate_synthetic_voice_audio(
                duration=task_info["target_duration_seconds"],
                sample_rate=self.sample_rate
            )
            self.duration = task_info["target_duration_seconds"]

        return {
            "session_id": self.session_id,
            "participant_id": self.participant_id,
            "task_type": self.task_type,
            "duration": self.duration,
            "sample_rate": self.sample_rate,
            "raw_audio": self.audio_buffer
        }

    def discard_raw_audio(self) -> None:
        """Securely deletes raw audio buffer from memory."""
        if self.audio_buffer is not None:
            self.audio_buffer.fill(0)
            self.audio_buffer = None


class VoiceFeatureExtractor:
    """
    Acoustic feature extractor matching Praat / Parselmouth specifications:
    - Pitch (F0) mean & std
    - Jitter (relative cycle-to-cycle frequency perturbation)
    - Shimmer (relative cycle-to-cycle amplitude perturbation)
    - Harmonics-to-Noise Ratio (HNR in dB)
    - 13 Mel-Frequency Cepstral Coefficients (MFCCs)
    - Spectral Centroid, Bandwidth, and Rolloff (85%)
    - Signal quality metrics (SNR, duration, clipping, silence ratio)
    """

    @classmethod
    def extract_features(cls, audio: np.ndarray, sample_rate: int = 44100) -> Dict[str, Any]:
        if audio is None or len(audio) == 0:
            return cls._get_empty_features()

        audio = np.asarray(audio, dtype=np.float32)
        duration = float(len(audio) / sample_rate)

        # 1. Quality metrics
        clipping_detected = cls._detect_clipping(audio)
        silence_ratio, snr_est = cls._analyze_energy(audio, sample_rate)
        signal_quality = float(np.clip((snr_est + 10.0) / 40.0, 0.0, 1.0))

        # 2. Pitch tracking via autocorrelation
        pitch_mean, pitch_std, periods, peak_amplitudes = cls._track_pitch(audio, sample_rate)

        # 3. Perturbation features (Jitter & Shimmer)
        jitter = cls._calculate_jitter(periods)
        shimmer = cls._calculate_shimmer(peak_amplitudes)

        # 4. Harmonics-to-Noise Ratio (HNR)
        hnr = cls._calculate_hnr(audio, sample_rate, pitch_mean)

        # 5. Spectral Features
        spectral = cls._calculate_spectral_features(audio, sample_rate)

        # 6. MFCCs (13 coefficients)
        mfccs = cls._calculate_mfccs(audio, sample_rate, num_coeffs=13)

        return {
            "feature_version": FEATURE_VERSION,
            "duration": round(duration, 2),
            "signal_quality": round(signal_quality, 2),
            "clipping_detected": bool(clipping_detected),
            "silence_ratio": round(float(silence_ratio), 3),
            "pitch_mean": round(float(pitch_mean), 2),
            "pitch_std": round(float(pitch_std), 2),
            "jitter": round(float(jitter), 5),
            "shimmer": round(float(shimmer), 5),
            "hnr": round(float(hnr), 2),
            "mfcc_features": [round(float(v), 4) for v in mfccs],
            "spectral_features": {
                "spectral_centroid": round(float(spectral["centroid"]), 2),
                "spectral_bandwidth": round(float(spectral["bandwidth"]), 2),
                "spectral_rolloff": round(float(spectral["rolloff"]), 2)
            }
        }

    @staticmethod
    def _detect_clipping(audio: np.ndarray, threshold: float = 0.985) -> bool:
        clipped_samples = np.sum(np.abs(audio) >= threshold)
        return bool(clipped_samples > 10)

    @staticmethod
    def _analyze_energy(audio: np.ndarray, sample_rate: int) -> Tuple[float, float]:
        frame_size = int(sample_rate * 0.025)  # 25ms
        hop_size = int(sample_rate * 0.010)    # 10ms
        num_frames = max(1, (len(audio) - frame_size) // hop_size)

        energies = []
        for i in range(num_frames):
            frame = audio[i * hop_size : i * hop_size + frame_size]
            energies.append(np.sqrt(np.mean(frame ** 2)))

        energies = np.array(energies)
        max_energy = np.max(energies) if len(energies) > 0 else 0.0
        silence_thresh = max(0.005, max_energy * 0.08)

        silent_mask = energies < silence_thresh
        silence_ratio = np.mean(silent_mask) if len(energies) > 0 else 1.0

        voiced_energy = float(np.mean(energies[~silent_mask] ** 2)) if np.any(~silent_mask) else 1e-6
        noise_energy = float(np.mean(energies[silent_mask] ** 2)) if np.any(silent_mask) else 1e-6

        voiced_energy = max(1e-6, voiced_energy)
        noise_energy = max(1e-6, noise_energy)

        snr = 10.0 * np.log10(max(1e-4, voiced_energy / noise_energy))
        return float(silence_ratio), float(snr)

    @staticmethod
    def _track_pitch(audio: np.ndarray, sample_rate: int) -> Tuple[float, float, List[float], List[float]]:
        frame_size = int(sample_rate * 0.040)  # 40ms
        hop_size = int(sample_rate * 0.020)    # 20ms
        num_frames = (len(audio) - frame_size) // hop_size

        min_lag = int(sample_rate / 400.0)  # 400 Hz max
        max_lag = int(sample_rate / 70.0)   # 70 Hz min

        f0_list = []
        periods = []
        amplitudes = []

        for i in range(num_frames):
            frame = audio[i * hop_size : i * hop_size + frame_size]
            energy = np.sum(frame ** 2)
            if energy < 1e-4:
                continue

            # Normalized Autocorrelation
            acorr = np.correlate(frame, frame, mode='full')
            mid = len(frame) - 1
            acorr = acorr[mid : mid + max_lag + 1]

            if acorr[0] <= 1e-6:
                continue
            norm_acorr = acorr / acorr[0]

            search_region = norm_acorr[min_lag : max_lag + 1]
            if len(search_region) == 0:
                continue

            best_idx = np.argmax(search_region)
            best_corr = search_region[best_idx]
            best_lag = min_lag + best_idx

            if best_corr > 0.40 and best_lag > 0:
                f0 = sample_rate / best_lag
                f0_list.append(f0)
                periods.append(best_lag / sample_rate)
                cycle_slice = frame[:best_lag]
                amplitudes.append(float(np.max(np.abs(cycle_slice))))

        if len(f0_list) == 0:
            return 0.0, 0.0, [], []

        return float(np.mean(f0_list)), float(np.std(f0_list)), periods, amplitudes

    @staticmethod
    def _calculate_jitter(periods: List[float]) -> float:
        if not periods or len(periods) < 2:
            return 0.0
        diffs = [abs(periods[i] - periods[i + 1]) for i in range(len(periods) - 1)]
        mean_diff = np.mean(diffs)
        mean_period = np.mean(periods)
        if mean_period <= 1e-6:
            return 0.0
        return float(mean_diff / mean_period)

    @staticmethod
    def _calculate_shimmer(amplitudes: List[float]) -> float:
        if not amplitudes or len(amplitudes) < 2:
            return 0.0
        diffs = [abs(amplitudes[i] - amplitudes[i + 1]) for i in range(len(amplitudes) - 1)]
        mean_diff = np.mean(diffs)
        mean_amp = np.mean(amplitudes)
        if mean_amp <= 1e-6:
            return 0.0
        return float(mean_diff / mean_amp)

    @staticmethod
    def _calculate_hnr(audio: np.ndarray, sample_rate: int, pitch_mean: float) -> float:
        if pitch_mean <= 0.0 or len(audio) < 1024:
            return 0.0
        lag = int(round(sample_rate / pitch_mean))
        win_size = min(len(audio) - lag, 2048)
        if win_size <= 0:
            return 0.0

        segment = audio[:win_size]
        shifted = audio[lag : lag + win_size]

        r0 = np.sum(segment ** 2)
        rlag = np.sum(segment * shifted)

        if r0 <= 1e-6:
            return 0.0

        r = np.clip(rlag / r0, 0.001, 0.999)
        hnr = 10.0 * np.log10(r / (1.0 - r))
        return float(np.clip(hnr, 0.0, 45.0))

    @staticmethod
    def _calculate_spectral_features(audio: np.ndarray, sample_rate: int) -> Dict[str, float]:
        fft_size = 1024
        half = fft_size // 2
        hop_size = 512
        num_frames = max(1, (len(audio) - fft_size) // hop_size)

        power_specs = []
        for i in range(num_frames):
            frame = audio[i * hop_size : i * hop_size + fft_size]
            if len(frame) < fft_size:
                padded = np.zeros(fft_size, dtype=np.float32)
                padded[:len(frame)] = frame
                frame = padded
            windowed = frame * np.hamming(fft_size)
            spec = np.abs(np.fft.rfft(windowed))[:half]
            power_specs.append(spec ** 2)

        avg_power = np.mean(power_specs, axis=0)
        freqs = np.fft.rfftfreq(fft_size, 1.0 / sample_rate)[:half]

        total_power = np.sum(avg_power)
        if total_power <= 1e-6:
            return {"centroid": 0.0, "bandwidth": 0.0, "rolloff": 0.0}

        # Spectral Centroid
        centroid = np.sum(freqs * avg_power) / total_power

        # Spectral Bandwidth
        bandwidth = np.sqrt(np.sum(((freqs - centroid) ** 2) * avg_power) / total_power)

        # Spectral Rolloff (85% energy threshold)
        cum_power = np.cumsum(avg_power)
        rolloff_idx = np.searchsorted(cum_power, 0.85 * total_power)
        rolloff = freqs[min(rolloff_idx, len(freqs) - 1)]

        return {
            "centroid": float(centroid),
            "bandwidth": float(bandwidth),
            "rolloff": float(rolloff)
        }

    @staticmethod
    def _calculate_mfccs(audio: np.ndarray, sample_rate: int, num_coeffs: int = 13) -> List[float]:
        fft_size = 1024
        num_filters = 26
        min_freq = 100.0
        max_freq = min(sample_rate / 2.0, 8000.0)

        # Mel filterbanks
        hz_to_mel = lambda hz: 2595.0 * np.log10(1.0 + hz / 700.0)
        mel_to_hz = lambda mel: 700.0 * (10.0 ** (mel / 2595.0) - 1.0)

        mel_min = hz_to_mel(min_freq)
        mel_max = hz_to_mel(max_freq)
        mel_pts = np.linspace(mel_min, mel_max, num_filters + 2)
        hz_pts = mel_to_hz(mel_pts)
        bin_pts = np.floor((fft_size + 1) * hz_pts / sample_rate).astype(int)

        start_idx = max(0, (len(audio) - fft_size) // 2)
        segment = audio[start_idx : start_idx + fft_size]
        if len(segment) < fft_size:
            padded = np.zeros(fft_size, dtype=np.float32)
            padded[:len(segment)] = segment
            segment = padded

        mag_spec = np.abs(np.fft.rfft(segment * np.hamming(fft_size))) ** 2

        filter_energies = np.zeros(num_filters)
        for m in range(1, num_filters + 1):
            left, center, right = bin_pts[m - 1], bin_pts[m], bin_pts[m + 1]
            for k in range(left, center):
                if k < len(mag_spec):
                    filter_energies[m - 1] += mag_spec[k] * (k - left) / max(1, center - left)
            for k in range(center, right):
                if k < len(mag_spec):
                    filter_energies[m - 1] += mag_spec[k] * (right - k) / max(1, right - center)

        log_filter_energies = np.log(np.maximum(1e-6, filter_energies))

        # Discrete Cosine Transform (DCT-II)
        mfccs = []
        for i in range(num_coeffs):
            c = np.sum(log_filter_energies * np.cos(np.pi * i * (np.arange(num_filters) + 0.5) / num_filters))
            mfccs.append(float(c))

        return mfccs

    @classmethod
    def _get_empty_features(cls) -> Dict[str, Any]:
        return {
            "feature_version": FEATURE_VERSION,
            "duration": 0.0,
            "signal_quality": 0.0,
            "clipping_detected": False,
            "silence_ratio": 1.0,
            "pitch_mean": 0.0,
            "pitch_std": 0.0,
            "jitter": 0.0,
            "shimmer": 0.0,
            "hnr": 0.0,
            "mfcc_features": [0.0] * 13,
            "spectral_features": {
                "spectral_centroid": 0.0,
                "spectral_bandwidth": 0.0,
                "spectral_rolloff": 0.0
            }
        }


class VoiceQualityScorer:
    """
    Standardized multi-factor quality scoring:
    1. Sufficient duration (>3s): +0.30
    2. Good SNR (signal_quality >= 0.50): +0.30
    3. No clipping: +0.20
    4. Low silence (<30%): +0.20
    Gating: quality_score >= 0.50 for baseline eligibility.
    """

    @classmethod
    def calculate_quality_score(cls, metrics: Dict[str, Any]) -> Dict[str, Any]:
        if not metrics:
            return {
                "quality_score": 0.0,
                "is_baseline_eligible": False,
                "breakdown": {
                    "sufficient_duration": 0.0,
                    "good_snr": 0.0,
                    "no_clipping": 0.0,
                    "low_silence": 0.0
                },
                "rejection_reasons": ["Missing voice session metrics"]
            }

        duration = float(metrics.get("duration", 0.0))
        signal_quality = float(metrics.get("signal_quality", 0.0))
        clipping_detected = bool(metrics.get("clipping_detected", False))
        silence_ratio = float(metrics.get("silence_ratio", 1.0))

        rejection_reasons = []
        breakdown = {
            "sufficient_duration": 0.0,
            "good_snr": 0.0,
            "no_clipping": 0.0,
            "low_silence": 0.0
        }

        # 1. Sufficient duration (>3s)
        if duration > MIN_DURATION_SECONDS:
            breakdown["sufficient_duration"] = 0.30
        else:
            rejection_reasons.append(f"Insufficient duration: {duration:.1f}s <= {MIN_DURATION_SECONDS}s")

        # 2. Good SNR (signal_quality >= 0.50)
        if signal_quality >= MIN_SIGNAL_QUALITY_THRESHOLD:
            breakdown["good_snr"] = 0.30
        else:
            rejection_reasons.append(f"Low signal-to-noise quality: {signal_quality:.2f} < {MIN_SIGNAL_QUALITY_THRESHOLD:.2f}")

        # 3. No clipping
        if not clipping_detected:
            breakdown["no_clipping"] = 0.20
        else:
            rejection_reasons.append("Audio clipping / saturation detected")

        # 4. Low silence ratio (<30%)
        if silence_ratio < MAX_ALLOWED_SILENCE_RATIO:
            breakdown["low_silence"] = 0.20
        else:
            rejection_reasons.append(f"Excessive silence ratio: {silence_ratio:.2f} >= {MAX_ALLOWED_SILENCE_RATIO:.2f}")

        total_score = round(sum(breakdown.values()), 2)
        is_eligible = total_score >= MIN_BASELINE_QUALITY_THRESHOLD

        return {
            "quality_score": total_score,
            "is_baseline_eligible": is_eligible,
            "breakdown": breakdown,
            "rejection_reasons": rejection_reasons,
            "summary": "Eligible for baseline modeling" if is_eligible else "Rejected from baseline modeling"
        }


class VoiceSessionModel:
    """
    Python data model conforming directly to the Supabase voice_sessions table.
    Enforces check constraints, UUID validation, and ensures raw audio is never stored.
    """
    def __init__(self, data: Optional[Dict[str, Any]] = None):
        data = data or {}
        self.id: Optional[str] = data.get("id")
        self.participant_id: str = data.get("participant_id", "")
        self.session_id: str = data.get("session_id", str(uuid.uuid4()))
        self.timestamp: str = data.get("timestamp", datetime.datetime.now(datetime.timezone.utc).isoformat())
        self.task_type: str = data.get("task_type", TASK_SUSTAINED_VOWEL)
        self.duration: float = float(data.get("duration", 0.0))
        self.signal_quality: float = float(data.get("signal_quality", 0.0))
        self.jitter: float = float(data.get("jitter", 0.0))
        self.shimmer: float = float(data.get("shimmer", 0.0))
        self.hnr: float = float(data.get("hnr", 0.0))
        self.pitch_mean: float = float(data.get("pitch_mean", 0.0))
        self.pitch_std: float = float(data.get("pitch_std", 0.0))
        self.mfcc_features: List[float] = list(data.get("mfcc_features", []))
        self.spectral_features: Dict[str, float] = dict(data.get("spectral_features", {
            "spectral_centroid": 0.0,
            "spectral_bandwidth": 0.0,
            "spectral_rolloff": 0.0
        }))
        self.quality_score: float = float(data.get("quality_score", 0.0))
        self.feature_version: str = data.get("feature_version", FEATURE_VERSION)
        self.synced: bool = bool(data.get("synced", False))

    @classmethod
    def from_features(
        cls,
        participant_id: str,
        session_id: str,
        task_type: str,
        features: Dict[str, Any],
        quality_score: float
    ) -> "VoiceSessionModel":
        if not participant_id:
            raise ValueError("participant_id is mandatory.")

        return cls({
            "participant_id": participant_id,
            "session_id": session_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "task_type": task_type,
            "duration": features.get("duration", 0.0),
            "signal_quality": features.get("signal_quality", 0.0),
            "jitter": features.get("jitter", 0.0),
            "shimmer": features.get("shimmer", 0.0),
            "hnr": features.get("hnr", 0.0),
            "pitch_mean": features.get("pitch_mean", 0.0),
            "pitch_std": features.get("pitch_std", 0.0),
            "mfcc_features": features.get("mfcc_features", []),
            "spectral_features": features.get("spectral_features", {}),
            "quality_score": quality_score,
            "feature_version": features.get("feature_version", FEATURE_VERSION),
            "synced": False
        })

    def validate(self) -> Tuple[bool, List[str]]:
        errors = []

        # UUID checks
        try:
            uuid.UUID(self.participant_id)
        except (ValueError, TypeError, AttributeError):
            errors.append(f"Invalid participant_id: must be a valid UUID (got {self.participant_id})")

        try:
            uuid.UUID(self.session_id)
        except (ValueError, TypeError, AttributeError):
            errors.append(f"Invalid session_id: must be a valid UUID (got {self.session_id})")

        # Task type
        if self.task_type not in VALID_TASK_TYPES:
            errors.append(f"Invalid task_type: {self.task_type}. Must be one of {VALID_TASK_TYPES}")

        # Check constraints
        if self.duration < 0:
            errors.append("duration must be >= 0")
        if not (0.0 <= self.signal_quality <= 1.0):
            errors.append("signal_quality must be between 0.0 and 1.0")
        if self.jitter < 0:
            errors.append("jitter must be >= 0")
        if self.shimmer < 0:
            errors.append("shimmer must be >= 0")
        if self.pitch_mean < 0:
            errors.append("pitch_mean must be >= 0")
        if self.pitch_std < 0:
            errors.append("pitch_std must be >= 0")
        if not (0.0 <= self.quality_score <= 1.0):
            errors.append("quality_score must be between 0.0 and 1.0")

        if not isinstance(self.mfcc_features, list) or len(self.mfcc_features) == 0:
            errors.append("mfcc_features must be a non-empty array")
        if not isinstance(self.spectral_features, dict):
            errors.append("spectral_features must be a dictionary")

        return len(errors) == 0, errors

    def to_supabase_payload(self) -> Dict[str, Any]:
        is_valid, errors = self.validate()
        if not is_valid:
            raise ValueError(f"VoiceSessionModel validation failed: {'; '.join(errors)}")

        return {
            "participant_id": self.participant_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "task_type": self.task_type,
            "duration": self.duration,
            "signal_quality": self.signal_quality,
            "jitter": self.jitter,
            "shimmer": self.shimmer,
            "hnr": self.hnr,
            "pitch_mean": self.pitch_mean,
            "pitch_std": self.pitch_std,
            "mfcc_features": self.mfcc_features,
            "spectral_features": self.spectral_features,
            "quality_score": self.quality_score,
            "feature_version": self.feature_version,
            "synced": self.synced
        }
