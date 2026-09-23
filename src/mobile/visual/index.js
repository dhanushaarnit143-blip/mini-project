/**
 * MPF Mobile Extension — Visual Module Index (Phase 7)
 *
 * Public surface of the ocular/visual behavior collection module.
 *
 * SENSOR INTEGRITY & PRIVACY:
 *   - "Ocular/Visual Behavior Module" — NOT retinal imaging.
 *   - Video stream is processed in-memory locally.
 *   - ZERO video recordings or facial images stored or uploaded.
 *   - Camera active ONLY during explicit guided tasks.
 *   - "Research screening result — not a clinical diagnosis."
 *   - "Deviation from personal baseline."
 */

// ── React Screens ──────────────────────────────────────────────────────────
export { TrackingTaskScreen } from './TrackingTaskScreen.jsx';
export { BlinkTaskScreen }    from './BlinkTaskScreen.jsx';
export { ReactionTaskScreen } from './ReactionTaskScreen.jsx';

// ── Camera & Landmark Infrastructure ──────────────────────────────────────
export {
  FaceLandmarkDetector,
  DEFAULT_EAR_BLINK_THRESHOLD,
  LANDMARK_DETECTOR_VERSION,
} from './faceLandmarkDetector.js';

// ── Feature Extractors ─────────────────────────────────────────────────────
export {
  extractTrackingFeatures,
  extractBlinkFeatures,
  extractReactionFeatures,
  VISUAL_FEATURE_VERSION,
  EAR_BLINK_THRESHOLD,
  MIN_BLINK_DURATION_MS,
  MAX_BLINK_DURATION_MS,
  MIN_PLAUSIBLE_REACTION_MS,
  MAX_REACTION_TIMEOUT_MS,
} from './visualFeatureExtractor.js';

// ── Quality Scoring ────────────────────────────────────────────────────────
export {
  VisualQualityScorer,
  MIN_BASELINE_QUALITY_THRESHOLD,
  TASK_DURATION_TARGETS,
} from './visualQualityScorer.js';

// ── Data Model ─────────────────────────────────────────────────────────────
export {
  VisualSessionModel,
  VISUAL_TASK_TYPES,
  VALID_TASK_TYPES,
  CURRENT_FEATURE_VERSION,
} from './visualSessionModel.js';
