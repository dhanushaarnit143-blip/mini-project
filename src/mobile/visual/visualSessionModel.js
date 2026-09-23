/**
 * MPF Mobile Extension — Visual Session Model (Phase 7)
 *
 * Standardized data model and Supabase persistence client for ocular/visual
 * behavior biomarkers collected from front-camera guided tasks.
 *
 * Complies strictly with:
 * - Supabase `visual_sessions` table schema (migrations 006 & 017)
 * - Privacy Model: ZERO video frames or facial images stored or uploaded
 * - Versioned reproducibility (feature_version = '1.0')
 * - Idempotent upload semantics via client-generated UUID session_id
 * - No diagnostic claims — strictly uses compliance language
 * - SENSOR INTEGRITY: Ocular/Visual Behavior Module — NOT retinal imaging.
 */

export const VISUAL_TASK_TYPES = {
  TRACKING: 'tracking',
  BLINK:    'blink',
  REACTION: 'reaction',
};

export const CURRENT_FEATURE_VERSION = '1.0';
export const VALID_TASK_TYPES = Object.values(VISUAL_TASK_TYPES);

function _nullable(val) {
  if (val === undefined || val === null) return null;
  const n = Number(val);
  return Number.isNaN(n) ? null : n;
}

function _requireParticipantId(id) {
  if (!id || typeof id !== 'string' || id.trim().length === 0) {
    throw new Error('participant_id is mandatory and cannot be empty.');
  }
}

/**
 * VisualSessionModel — typed, validated session record for the visual_sessions table.
 */
export class VisualSessionModel {
  /**
   * @param {Object} data - Raw session fields.
   */
  constructor(data = {}) {
    this.id             = data.id || null;
    this.participant_id = data.participant_id || null;
    this.session_id     = data.session_id || this._generateUUID();
    this.timestamp      = data.timestamp || new Date().toISOString();
    this.task_type      = data.task_type || VISUAL_TASK_TYPES.TRACKING;
    this.duration       = Number(data.duration >= 0 ? data.duration : 0);

    // Blink features (nullable for tracking/reaction)
    this.blink_rate                  = _nullable(data.blink_rate);
    this.blink_interval_variability  = _nullable(data.blink_interval_variability);
    this.blink_duration_mean         = _nullable(data.blink_duration_mean);

    // Tracking features (nullable for blink/reaction)
    this.gaze_stability              = _nullable(data.gaze_stability);
    this.tracking_accuracy           = _nullable(data.tracking_accuracy);
    this.gaze_movement_features      = data.gaze_movement_features || null;

    // Reaction features (nullable for tracking/blink)
    this.reaction_time               = _nullable(data.reaction_time);
    this.reaction_time_variability   = _nullable(data.reaction_time_variability);
    this.missed_targets              = data.missed_targets !== undefined && data.missed_targets !== null
      ? Number(data.missed_targets)
      : 0;

    // Quality and versioning
    this.quality_score    = Number(
      typeof data.quality_score === 'number'
        ? Math.min(1.0, Math.max(0.0, data.quality_score))
        : 0.0
    );
    this.feature_version  = data.feature_version || CURRENT_FEATURE_VERSION;
    this.synced           = Boolean(data.synced || false);
  }

  /**
   * Factory method — builds a VisualSessionModel from tracking task outputs.
   */
  static fromTracking({ participantId, sessionId, features, qualityResult }) {
    _requireParticipantId(participantId);
    return new VisualSessionModel({
      participant_id:         participantId,
      session_id:             sessionId,
      task_type:              VISUAL_TASK_TYPES.TRACKING,
      duration:               features.duration_seconds,
      gaze_stability:         features.gaze_stability,
      tracking_accuracy:      features.tracking_accuracy,
      gaze_movement_features: features.gaze_movement_features,
      quality_score:          qualityResult?.quality_score ?? 0,
      feature_version:        features.feature_version || CURRENT_FEATURE_VERSION,
    });
  }

  /**
   * Factory method — builds a VisualSessionModel from blink task outputs.
   */
  static fromBlink({ participantId, sessionId, features, qualityResult }) {
    _requireParticipantId(participantId);
    return new VisualSessionModel({
      participant_id:             participantId,
      session_id:                 sessionId,
      task_type:                  VISUAL_TASK_TYPES.BLINK,
      duration:                   features.duration_seconds,
      blink_rate:                 features.blink_rate,
      blink_interval_variability: features.blink_interval_variability,
      blink_duration_mean:        features.blink_duration_mean,
      quality_score:              qualityResult?.quality_score ?? 0,
      feature_version:            features.feature_version || CURRENT_FEATURE_VERSION,
    });
  }

  /**
   * Factory method — builds a VisualSessionModel from reaction task outputs.
   */
  static fromReaction({ participantId, sessionId, features, qualityResult }) {
    _requireParticipantId(participantId);
    return new VisualSessionModel({
      participant_id:             participantId,
      session_id:                 sessionId,
      task_type:                  VISUAL_TASK_TYPES.REACTION,
      duration:                   features.duration_seconds,
      reaction_time:              features.reaction_time_mean,
      reaction_time_variability:  features.reaction_time_variability,
      missed_targets:             features.missed_targets,
      quality_score:              qualityResult?.quality_score ?? 0,
      feature_version:            features.feature_version || CURRENT_FEATURE_VERSION,
    });
  }

  /**
   * Validates internal session state against schema integrity rules.
   *
   * @returns {{ valid: boolean, errors: string[] }}
   */
  validate() {
    const errors = [];

    if (!this.participant_id) {
      errors.push('participant_id is required.');
    } else if (
      !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(this.participant_id)
    ) {
      errors.push(`participant_id must be a valid UUID; got "${this.participant_id}".`);
    }

    if (!this.session_id) {
      errors.push('session_id is required.');
    } else if (
      !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(this.session_id)
    ) {
      errors.push(`session_id must be a valid UUID; got "${this.session_id}".`);
    }

    if (!VALID_TASK_TYPES.includes(this.task_type)) {
      errors.push(`task_type must be one of [${VALID_TASK_TYPES.join(', ')}]; got "${this.task_type}".`);
    }

    if (typeof this.duration !== 'number' || this.duration < 0) {
      errors.push(`duration must be non-negative; got "${this.duration}".`);
    }

    if (typeof this.quality_score !== 'number' || this.quality_score < 0 || this.quality_score > 1) {
      errors.push(`quality_score must be in range [0.0, 1.0]; got "${this.quality_score}".`);
    }

    if (this.gaze_stability !== null && (this.gaze_stability < 0 || this.gaze_stability > 1)) {
      errors.push(`gaze_stability must be in range [0.0, 1.0]; got "${this.gaze_stability}".`);
    }

    if (this.tracking_accuracy !== null && (this.tracking_accuracy < 0 || this.tracking_accuracy > 1)) {
      errors.push(`tracking_accuracy must be in range [0.0, 1.0]; got "${this.tracking_accuracy}".`);
    }

    return { valid: errors.length === 0, errors };
  }

  /**
   * Converts the model to the exact payload expected by the Supabase visual_sessions table.
   * ZERO video, frames, or image data are ever stored or uploaded.
   *
   * @returns {Object} Database row representation
   */
  toPayload() {
    const v = this.validate();
    if (!v.valid) {
      throw new Error(`Cannot export invalid VisualSessionModel: ${v.errors.join('; ')}`);
    }

    const payload = {
      participant_id:             this.participant_id,
      session_id:                 this.session_id,
      timestamp:                  this.timestamp,
      task_type:                  this.task_type,
      duration:                   this.duration,
      quality_score:              this.quality_score,
      feature_version:            this.feature_version,
      synced:                     this.synced,
    };

    if (this.blink_rate !== null)                 payload.blink_rate = this.blink_rate;
    if (this.blink_interval_variability !== null) payload.blink_interval_variability = this.blink_interval_variability;
    if (this.blink_duration_mean !== null)        payload.blink_duration_mean = this.blink_duration_mean;
    if (this.gaze_stability !== null)             payload.gaze_stability = this.gaze_stability;
    if (this.tracking_accuracy !== null)          payload.tracking_accuracy = this.tracking_accuracy;
    if (this.gaze_movement_features !== null)     payload.gaze_movement_features = this.gaze_movement_features;
    if (this.reaction_time !== null)              payload.reaction_time = this.reaction_time;
    if (this.reaction_time_variability !== null)  payload.reaction_time_variability = this.reaction_time_variability;
    if (this.missed_targets !== null)             payload.missed_targets = this.missed_targets;

    return payload;
  }

  /**
   * Synchronizes the session record to the Supabase visual_sessions table.
   * Uses idempotent upsert on session_id to guarantee exactly-once delivery.
   *
   * @param {Object} supabaseClient
   * @returns {Promise<{ success: boolean, data?: Object, error?: Object }>}
   */
  async syncToSupabase(supabaseClient) {
    if (!supabaseClient) {
      return { success: false, error: new Error('supabaseClient is required for sync.') };
    }

    const validation = this.validate();
    if (!validation.valid) {
      return {
        success: false,
        error: new Error(`Validation failed: ${validation.errors.join('; ')}`),
      };
    }

    try {
      const payload = { ...this.toPayload(), synced: true };
      const { data, error } = await supabaseClient
        .from('visual_sessions')
        .upsert(payload, { onConflict: 'session_id' })
        .select()
        .single();

      if (error) {
        return { success: false, error };
      }

      this.synced = true;
      if (data?.id) this.id = data.id;
      return { success: true, data };
    } catch (err) {
      return { success: false, error: err };
    }
  }

  /**
   * Cryptographically secure UUID generator for browser / node environments.
   */
  _generateUUID() {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      return crypto.randomUUID();
    }
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }
}
