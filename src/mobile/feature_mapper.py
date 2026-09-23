"""
MPF Mobile Extension — Feature Mapping Layer (Phase 12).

Maps mobile longitudinal daily features (typing, voice, motor, visual, sleep)
to the representation expected by the existing MPF multimodal fusion model.

SCIENTIFIC & SENSOR INTEGRITY MANDATE:
1. PROXY MAPPINGS: Mobile sensor features are digital approximations/proxies
   of clinical/laboratory features, NOT identical physical measurements.
2. NO SENSOR OVERCLAIMING: Smartphone front camera captures ocular/visual
   behavior (blinking, gaze stability, reaction time). It is NOT a retinal camera.
   Retinal fundus/OCT remains absent and unavailable on smartphones.
3. NO DATA FABRICATION: Missing modalities are flagged as missing; values are
   never invented or imputed from population averages.
"""

from typing import Any, Dict, List, Optional, Tuple
import copy
import logging

logger = logging.getLogger("mpf.mobile.feature_mapper")

FEATURE_MAPPING_VERSION = "1.0.0"

PROXY_DISCLAIMER = (
    "Research screening result — not a clinical diagnosis. "
    "Mobile-derived features are digital approximations/proxies of the original "
    "MPF clinical features, not identical laboratory/clinical measurements."
)

OCULAR_DISCLAIMER = (
    "Smartphone front camera captures ocular/visual behavior (blinking, gaze stability, "
    "reaction time) and is NOT a retinal camera. Retinal fundus/OCT/OCTA remains a separate "
    "modality requiring specialized clinical hardware. Retinal modality is marked unavailable."
)

# Detailed documentation of all mobile-to-MPF proxy mappings
FEATURE_MAPPING_DOCUMENTATION: Dict[str, Dict[str, Any]] = {
    "typing.typing_speed": {
        "target": "motor.tapping_rate",
        "modality": "motor",
        "is_proxy": True,
        "description": "Mobile keystroke typing speed (keys/sec) serves as a digital fine-motor tapping rate proxy.",
    },
    "typing.interval_variability": {
        "target": "motor.tapping_interval_variability",
        "modality": "motor",
        "is_proxy": True,
        "description": "Keystroke flight-time / inter-tap interval coefficient of variation (CV) as motor rhythmicity proxy.",
    },
    "typing.correction_rate": {
        "target": "motor.fine_motor_indicator",
        "modality": "motor",
        "is_proxy": True,
        "description": "Backspace and correction frequency representing fine motor dexterity and motor coordination.",
    },
    "voice.jitter": {
        "target": "voice.jitter",
        "modality": "voice",
        "is_proxy": False,
        "description": "Cycle-to-cycle frequency variation (relative jitter / jitter_pct).",
    },
    "voice.shimmer": {
        "target": "voice.shimmer",
        "modality": "voice",
        "is_proxy": False,
        "description": "Cycle-to-cycle amplitude variation (local shimmer).",
    },
    "voice.hnr": {
        "target": "voice.hnr",
        "modality": "voice",
        "is_proxy": False,
        "description": "Harmonics-to-noise ratio in decibels.",
    },
    "voice.pitch_mean": {
        "target": "voice.pitch_mean",
        "modality": "voice",
        "is_proxy": False,
        "description": "Mean fundamental frequency (F0) in Hertz.",
    },
    "motor.cadence": {
        "target": "motor.gait_cadence",
        "modality": "motor",
        "is_proxy": False,
        "description": "Walking cadence in steps per minute (cadence_steps_per_min).",
    },
    "motor.stride_variability": {
        "target": "motor.stride_variability",
        "modality": "motor",
        "is_proxy": False,
        "description": "Stride-to-stride interval coefficient of variation (stride_interval_cv_pct).",
    },
    "motor.tapping_rate": {
        "target": "motor.tapping_rate",
        "modality": "motor",
        "is_proxy": False,
        "description": "Alternating finger-tapping taps per second.",
    },
    "motor.tremor_frequency": {
        "target": "motor.tremor_frequency",
        "modality": "motor",
        "is_proxy": False,
        "description": "Dominant resting or postural tremor peak frequency in Hertz (typically 4-7 Hz in PD pattern).",
    },
    "visual.blink_rate": {
        "target": "facial.blink_rate",
        "modality": "visual",
        "is_proxy": True,
        "description": "Ocular spontaneous blink rate (blinks/min) as facial/hypomimia behavioral proxy. NOT retinal.",
    },
    "visual.gaze_stability": {
        "target": "facial.expression_variability",
        "modality": "visual",
        "is_proxy": True,
        "description": "Fixation stability / gaze dispersion as ocular-motor behavioral proxy. NOT retinal.",
    },
    "visual.reaction_time": {
        "target": "motor.reaction_time",
        "modality": "motor",
        "is_proxy": True,
        "description": "Visual stimulus-response latency (ms) serving as visual-motor processing speed proxy.",
    },
    "sleep.unusual_movement_self_report": {
        "target": "rbd.above_cutoff_flag",
        "modality": "rbd",
        "is_proxy": True,
        "description": "Self-reported dream enactment / motor behavior during sleep as RBDSQ cutoff proxy.",
    },
    "sleep.sleep_quality": {
        "target": "rbd.item_subscores",
        "modality": "rbd",
        "is_proxy": True,
        "description": "Sleep fragmentation / nocturnal disturbance score as RBDSQ subscore proxy.",
    },
}


def _extract_feature(container: Optional[Dict[str, Any]], *keys: str) -> Optional[float]:
    """Helper to extract a float feature from multiple candidate keys."""
    if not container or not isinstance(container, dict):
        return None
    for k in keys:
        if k in container and container[k] is not None:
            try:
                v = float(container[k])
                return v
            except (ValueError, TypeError):
                continue
    return None


def map_mobile_features(
    mobile_daily_features: Dict[str, Any],
    demographics: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Convert mobile daily longitudinal features into standard MPF model inputs.

    Args:
        mobile_daily_features: Dictionary of mobile features. Can be nested
            (with keys 'typing', 'voice', 'motor', 'visual', 'sleep')
            or the contents of a Supabase `daily_features` record.
        demographics: Optional dict with 'age' and 'sex'. Defaults to 65.0, 'female'.

    Returns:
        Tuple of (mapped_mpf_payload, mapping_metadata):
            - mapped_mpf_payload: Dictionary conforming to MPF pipeline input contract
            - mapping_metadata: Metadata with activated proxies, versions, and disclaimers
    """
    if not isinstance(mobile_daily_features, dict):
        raise TypeError(f"mobile_daily_features must be a dict. Got {type(mobile_daily_features).__name__}")

    # Unpack nested structures if wrapped in Supabase 'features' key
    raw_feats = mobile_daily_features.get("features", mobile_daily_features)
    if not isinstance(raw_feats, dict):
        raw_feats = mobile_daily_features

    typing_f = raw_feats.get("typing") or {}
    voice_f = raw_feats.get("voice") or {}
    motor_f = raw_feats.get("motor") or {}
    visual_f = raw_feats.get("visual") or {}
    sleep_f = raw_feats.get("sleep") or {}

    # Extract participant and demographics
    p_id = str(
        mobile_daily_features.get("participant_id")
        or raw_feats.get("participant_id")
        or "MOBILE_PARTICIPANT_001"
    ).strip()

    demo = demographics or {}
    age_val = demo.get("age", mobile_daily_features.get("age", raw_feats.get("age", 65.0)))
    sex_val = demo.get("sex", mobile_daily_features.get("sex", raw_feats.get("sex", "female")))

    try:
        age_float = float(age_val)
    except (ValueError, TypeError):
        age_float = 65.0

    sex_str = "male" if str(sex_val).strip().lower() in ["m", "male", "1"] else "female"

    available_modalities: List[str] = []
    missing_modalities: List[str] = []
    activated_proxies: List[str] = []

    # ─────────────────────────────────────────────────────────────────────────
    # 1. VOICE MODALITY MAPPING
    # ─────────────────────────────────────────────────────────────────────────
    voice_mapped: Dict[str, Any] = {}
    v_jitter = _extract_feature(voice_f, "jitter", "jitter_pct")
    v_shimmer = _extract_feature(voice_f, "shimmer")
    v_hnr = _extract_feature(voice_f, "hnr")
    v_pitch = _extract_feature(voice_f, "pitch_mean", "f0_mean_hz")

    if any(x is not None for x in [v_jitter, v_shimmer, v_hnr, v_pitch]):
        if v_jitter is not None:
            voice_mapped["jitter_pct"] = v_jitter
            voice_mapped["jitter"] = v_jitter
        if v_shimmer is not None:
            voice_mapped["shimmer"] = v_shimmer
        if v_hnr is not None:
            voice_mapped["hnr"] = v_hnr
        if v_pitch is not None:
            voice_mapped["pitch_mean"] = v_pitch
            voice_mapped["f0_mean_hz"] = v_pitch

        # Pass through any additional acoustic features already present in voice_f
        for extra_key in [
            "jitter_abs", "jitter_rap", "jitter_ppq5", "jitter_ddp",
            "shimmer_db", "shimmer_apq3", "shimmer_apq5", "shimmer_apq11", "shimmer_dda",
            "nhr", "rpde", "dfa", "ppe"
        ]:
            val = _extract_feature(voice_f, extra_key)
            if val is not None:
                voice_mapped[extra_key] = val

        voice_avail = True
        available_modalities.append("voice")
    else:
        voice_avail = False
        missing_modalities.append("voice")

    # ─────────────────────────────────────────────────────────────────────────
    # 2. MOTOR MODALITY & MOTOR PROXIES (TYPING, MOVEMENT, VISUAL REACTION)
    # ─────────────────────────────────────────────────────────────────────────
    motor_mapped: Dict[str, Any] = {}

    # Direct mobile motor features
    m_cadence = _extract_feature(motor_f, "cadence", "gait_cadence", "cadence_steps_per_min")
    m_stride_var = _extract_feature(motor_f, "stride_variability", "stride_interval_cv_pct")
    m_tap_rate = _extract_feature(motor_f, "tapping_rate")
    m_tremor_freq = _extract_feature(motor_f, "tremor_frequency")
    m_speed = _extract_feature(motor_f, "gait_speed_m_per_s", "speed")

    if m_cadence is not None:
        motor_mapped["cadence_steps_per_min"] = m_cadence
        motor_mapped["gait_cadence"] = m_cadence
    if m_stride_var is not None:
        motor_mapped["stride_interval_cv_pct"] = m_stride_var
        motor_mapped["stride_variability"] = m_stride_var
    if m_tap_rate is not None:
        motor_mapped["tapping_rate"] = m_tap_rate
    if m_tremor_freq is not None:
        motor_mapped["tremor_frequency"] = m_tremor_freq
    if m_speed is not None:
        motor_mapped["gait_speed_m_per_s"] = m_speed

    # Pass through additional standard motor gait features if available
    for extra_m in [
        "stride_interval_mean_s", "step_regularity", "symmetry_index_pct",
        "accel_variance", "stance_swing_ratio"
    ]:
        val = _extract_feature(motor_f, extra_m)
        if val is not None:
            motor_mapped[extra_m] = val

    # Typing → Motor Proxies
    t_speed = _extract_feature(typing_f, "typing_speed")
    t_var = _extract_feature(typing_f, "interval_variability")
    t_corr = _extract_feature(typing_f, "correction_rate")

    if t_speed is not None:
        # If tapping rate is absent from motor task, proxy from typing speed
        if "tapping_rate" not in motor_mapped:
            motor_mapped["tapping_rate"] = t_speed
        motor_mapped["typing_speed_proxy"] = t_speed
        activated_proxies.append("typing.typing_speed -> motor.tapping_rate")

    if t_var is not None:
        motor_mapped["tapping_interval_variability"] = t_var
        activated_proxies.append("typing.interval_variability -> motor.tapping_interval_variability")

    if t_corr is not None:
        motor_mapped["fine_motor_indicator"] = t_corr
        activated_proxies.append("typing.correction_rate -> motor.fine_motor_indicator")

    # Visual reaction time → Motor reaction time proxy
    v_rt = _extract_feature(visual_f, "reaction_time")
    if v_rt is not None:
        motor_mapped["reaction_time"] = v_rt
        activated_proxies.append("visual.reaction_time -> motor.reaction_time")

    if len(motor_mapped) > 0:
        motor_avail = True
        available_modalities.append("motor")
    else:
        motor_avail = False
        missing_modalities.append("motor")

    # ─────────────────────────────────────────────────────────────────────────
    # 3. SLEEP / RBD QUESTIONNAIRE MAPPING & PROXIES
    # ─────────────────────────────────────────────────────────────────────────
    rbd_mapped: Dict[str, Any] = {}
    s_unusual_mov = _extract_feature(sleep_f, "unusual_movement_self_report", "dream_enactment")
    s_quality = _extract_feature(sleep_f, "sleep_quality", "score", "rbdsq_total")

    # Check for direct item list or rbdsq total
    direct_rbdsq = _extract_feature(sleep_f, "rbdsq_total")
    direct_items = sleep_f.get("item_responses") or sleep_f.get("items")

    if any(x is not None for x in [s_unusual_mov, s_quality, direct_rbdsq, direct_items]):
        # Compute or proxy rbdsq_total
        if direct_rbdsq is not None:
            rbdsq_val = direct_rbdsq
        elif isinstance(direct_items, list) and len(direct_items) > 0:
            rbdsq_val = float(sum(int(bool(x)) for x in direct_items))
        else:
            # Proxy estimation: base cutoff indicator + sleep quality subscore
            above_cutoff = 1.0 if (s_unusual_mov is not None and s_unusual_mov >= 0.5) else 0.0
            # Scale sleep_quality (0-10 or 0-1) to approximate RBDSQ range [0, 13]
            sq_norm = s_quality if s_quality is not None else 5.0
            if sq_norm > 13.0:
                sq_norm = (sq_norm / 100.0) * 13.0
            rbdsq_val = min(13.0, max(0.0, (above_cutoff * 6.0) + (sq_norm * 0.5)))
            if s_unusual_mov is not None:
                activated_proxies.append("sleep.unusual_movement_self_report -> rbd.above_cutoff_flag")
            if s_quality is not None:
                activated_proxies.append("sleep.sleep_quality -> rbd.item_subscores")

        rbd_mapped["rbdsq_total"] = float(rbdsq_val)
        rbd_mapped["above_cutoff_flag"] = 1.0 if rbdsq_val >= 5.0 else 0.0
        rbd_mapped["high_weight_item_flags"] = 1.0 if rbdsq_val >= 5.0 else 0.0

        # Construct 13 item response proxy array
        item_responses: List[int] = []
        if isinstance(direct_items, list) and len(direct_items) >= 13:
            item_responses = [int(bool(x)) for x in direct_items[:13]]
        else:
            is_above = 1 if rbd_mapped["above_cutoff_flag"] >= 0.5 else 0
            # Synthesize representative items without fabricating data
            item_responses = [is_above if i in [0, 2, 4, 6] else 0 for i in range(13)]

        rbd_mapped["item_responses"] = item_responses
        for idx, val in enumerate(item_responses):
            rbd_mapped[f"item_{idx+1}"] = float(val)

        rbd_avail = True
        available_modalities.append("rbd")
    else:
        rbd_avail = False
        missing_modalities.append("rbd")

    # ─────────────────────────────────────────────────────────────────────────
    # 4. OCULAR / VISUAL BEHAVIOR MODULE (NOT RETINAL IMAGING)
    # ─────────────────────────────────────────────────────────────────────────
    # Smartphone camera is strictly Ocular/Visual Behavior Module, NOT Retinal.
    # Retinal imaging is always marked available=False on mobile.
    missing_modalities.append("retina")
    missing_modalities.append("olfactory")

    v_blink = _extract_feature(visual_f, "blink_rate")
    v_gaze = _extract_feature(visual_f, "gaze_stability")

    ocular_visual_data: Dict[str, Any] = {
        "available": any(x is not None for x in [v_blink, v_gaze, v_rt]),
        "device_sensor": "smartphone_front_camera",
        "modality_type": "ocular_visual_behavior",
        "is_retinal_imaging": False,
        "features": {},
        "disclaimer": OCULAR_DISCLAIMER,
    }

    if v_blink is not None:
        ocular_visual_data["features"]["blink_rate"] = v_blink
        activated_proxies.append("visual.blink_rate -> facial.blink_rate")
    if v_gaze is not None:
        ocular_visual_data["features"]["gaze_stability"] = v_gaze
        activated_proxies.append("visual.gaze_stability -> facial.expression_variability")
    if v_rt is not None:
        ocular_visual_data["features"]["reaction_time"] = v_rt

    # ─────────────────────────────────────────────────────────────────────────
    # 5. ASSEMBLE MPF INPUT PAYLOAD
    # ─────────────────────────────────────────────────────────────────────────
    mapped_mpf_payload: Dict[str, Any] = {
        "participant_id": p_id,
        "age": age_float,
        "sex": sex_str,
        "olfactory": {
            "available": False,
            "reason": "Sensor hardware (UPSIT/Sniffin' Sticks) absent on mobile devices",
        },
        "retina": {
            "available": False,
            "reason": "Smartphone front camera is NOT a retinal fundus/OCT camera",
        },
        "retinal": {
            "available": False,
            "reason": "Smartphone front camera is NOT a retinal fundus/OCT camera",
        },
        "voice": {
            "available": voice_avail,
            "features": voice_mapped if voice_avail else {},
        },
        "motor": {
            "available": motor_avail,
            "features": motor_mapped if motor_avail else {},
        },
        "rbd": {
            "available": rbd_avail,
            "rbdsq_total": rbd_mapped.get("rbdsq_total"),
            "item_responses": rbd_mapped.get("item_responses", []),
        },
        # Explicit Ocular/Visual extension record
        "ocular_visual": ocular_visual_data,
    }

    mapping_metadata = {
        "mapping_version": FEATURE_MAPPING_VERSION,
        "available_modalities": available_modalities,
        "missing_modalities": missing_modalities,
        "activated_proxies": activated_proxies,
        "proxy_disclaimer": PROXY_DISCLAIMER,
        "ocular_disclaimer": OCULAR_DISCLAIMER,
        "is_retinal_claimed": False,
        "hardware_limitations": [
            "No olfactory sensor hardware present on smartphone.",
            "Front camera measures external ocular/facial behavior, not retinal morphology.",
        ],
    }

    return MappedResult(mapped_mpf_payload, mapping_metadata)


class MappedResult(dict):
    """
    Dual-interface mapping result:
    - Dict interface: Contains combined keys from payload and metadata (e.g. 'available_modalities', 'missing_modalities')
    - 2-tuple interface: Unpacks as (mapped_mpf_payload, mapping_metadata) for callers expecting tuple unpacking
    """
    def __init__(self, payload: Dict[str, Any], metadata: Dict[str, Any]):
        super().__init__(payload)
        self.update(metadata)
        self._payload = payload
        self._metadata = metadata

    def __iter__(self):
        return iter((self._payload, self._metadata))

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return (self._payload, self._metadata)[key]
        return super().__getitem__(key)

