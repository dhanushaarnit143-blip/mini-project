/**
 * MPF Mobile Extension — Motor Module Index (Phase 6)
 *
 * Public surface of the motor/sensor collection module.
 * Import screens and utilities from this single entry point.
 */

// ── React screens ──────────────────────────────────────────────────────────
export { WalkingTaskScreen }   from './WalkingTaskScreen.jsx';
export { TappingTaskScreen }   from './TappingTaskScreen.jsx';
export { TremorTaskScreen }    from './TremorTaskScreen.jsx';

// ── Sensor infrastructure ──────────────────────────────────────────────────
export { SensorCollector, ImuBuffer, SENSOR_SAMPLE_RATE_HZ } from './sensorCollector.js';

// ── Feature extractors ─────────────────────────────────────────────────────
export { extractWalkingFeatures, WALKING_FEATURE_VERSION } from './walkingFeatureExtractor.js';
export { extractTappingFeatures, TAPPING_FEATURE_VERSION } from './tappingFeatureExtractor.js';
export { extractTremorFeatures,  TREMOR_FEATURE_VERSION, TREMOR_BANDS } from './tremorFeatureExtractor.js';

// ── Quality scoring ────────────────────────────────────────────────────────
export { MotorQualityScorer, MIN_BASELINE_QUALITY_THRESHOLD } from './motorQualityScorer.js';

// ── Data model ─────────────────────────────────────────────────────────────
export { MotorSessionModel, MOTOR_TASK_TYPES, CURRENT_FEATURE_VERSION } from './motorSessionModel.js';
