/**
 * MPF Mobile Extension — Motor Session Model (Phase 6)
 *
 * Standardized data model and Supabase persistence client for motor/kinematic
 * biomarkers collected from smartphone accelerometer/gyroscope tasks.
 *
 * Complies strictly with:
 * - Supabase `motor_sessions` table schema (migration 005_create_motor_sessions.sql)
 * - Privacy Model: ZERO raw sensor data stored or uploaded — only derived features
 * - Versioned reproducibility (feature_version = '1.0')
 * - Idempotent upload semantics via client-generated UUID session_id
 * - No diagnostic claims — compliance language used throughout
 */

export const MOTOR_TASK_TYPES = {
  WALKING:     'walking',
  TAPPING:     'tapping',
  TREMOR_HOLD: 'tremor_hold',
};

export const CURRENT_FEATURE_VERSION = '1.0';
export const VALID_TASK_TYPES = Object.values(MOTOR_TASK_TYPES);

/**
 * MotorSessionModel — typed, validated session record for the motor_sessions table.
 */
export class MotorSessionModel {
  /**
   * @param {Object} data - Raw session fields.
   */
  constructor(data = {}) {
    this.id             = data.id || null;
    this.participant_id = data.participant_id || null;
    this.session_id     = data.session_id || this._generateUUID();
    this.timestamp      = data.timestamp || new Date().toISOString();
    this.task_type      = data.task_type || MOTOR_TASK_TYPES.WALKING;
    this.duration       = Number(data.duration >= 0 ? data.duration : 0);

    // Walking features (nullable for non-walking tasks)
    this.cadence                      = _nullable(data.cadence);
    this.stride_interval_mean         = _nullable(data.stride_interval_mean);
    this.stride_interval_variability  = _nullable(data.stride_interval_variability);

    // Shared movement variability
    this.movement_variability = Number(
      typeof data.movement_variability === 'number' ? data.movement_variability : 0
    );

    // Tapping features (nullable for non-tapping tasks)
    this.tapping_rate                 = _nullable(data.tapping_rate);
    this.tapping_interval_variability = _nullable(data.tapping_interval_variability);

    // Tremor features (nullable for non-tremor tasks)
    this.tremor_frequency  = _nullable(data.tremor_frequency);
    this.tremor_amplitude  = _nullable(data.tremor_amplitude);

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
   * Factory method — builds a MotorSessionModel from walking task outputs.
   *
   * @param {Object} p
   * @param {string} p.participantId
   * @param {string} [p.sessionId]
   * @param {Object} p.features - Output of extractWalkingFeatures()
   * @param {Object} p.qualityResult - Output of MotorQualityScorer.scoreWalking()
   * @returns {MotorSessionModel}
   */
  static fromWalking({ participantId, sessionId, features, qualityResult }) {
    _requireParticipantId(participantId);
    return new MotorSessionModel({
      participant_id:             participantId,
      session_id:                 sessionId,
      task_type:                  MOTOR_TASK_TYPES.WALKING,
      duration:                   features.duration_seconds,
      cadence:                    features.cadence,
      stride_interval_mean:       features.stride_interval_mean,
      stride_interval_variability: features.stride_interval_variability,
      movement_variability:       features.stride_interval_variability ?? 0,
      quality_score:              qualityResult?.quality_score ?? 0,
      feature_version:            features.feature_version || CURRENT_FEATURE_VERSION,
    });
  }

  /**
   * Factory method — builds a MotorSessionModel from tapping task outputs.
   *
   * @param {Object} p
   * @param {string} p.participantId
   * @param {string} [p.sessionId]
   * @param {Object} p.features - Output of extractTappingFeatures()
   * @param {Object} p.qualityResult - Output of MotorQualityScorer.scoreTapping()
   * @returns {MotorSessionModel}
   */
  static fromTapping({ participantId, sessionId, features, qualityResult }) {
    _requireParticipantId(participantId);
    return new MotorSessionModel({
      participant_id:               participantId,
      session_id:                   sessionId,
      task_type:                    MOTOR_TASK_TYPES.TAPPING,
      duration:                     features.duration_seconds,
      tapping_rate:                 features.tapping_rate,
      tapping_interval_variability: features.inter_tap_interval_variability,
      movement_variability:         features.inter_tap_interval_variability ?? 0,
      quality_score:                qualityResult?.quality_score ?? 0,
      feature_version:              features.feature_version || CURRENT_FEATURE_VERSION,
    });
  }

  /**
   * Factory method — builds a MotorSessionModel from tremor task outputs.
   *
   * @param {Object} p
   * @param {string} p.participantId
   * @param {string} [p.sessionId]
   * @param {Object} p.features - Output of extractTremorFeatures()
   * @param {Object} p.qualityResult - Output of MotorQualityScorer.scoreTremor()
   * @returns {MotorSessionModel}
   */
  static fromTremor({ participantId, sessionId, features, qualityResult }) {
    _requireParticipantId(participantId);
    return new MotorSessionModel({
      participant_id:   participantId,
      session_id:       sessionId,
      task_type:        MOTOR_TASK_TYPES.TREMOR_HOLD,
      duration:         features.duration_seconds,
      tremor_frequency: features.dominant_frequency,
      tremor_amplitude: features.tremor_amplitude,
      movement_variability: features.tremor_amplitude ?? 0,
      quality_score:    qualityResult?.quality_score ?? 0,
      feature_version:  features.feature_version || CURRENT_FEATURE_VERSION,
    });
  }

  /**
   * Validates data fields against Supabase PostgreSQL check constraints.
   * @returns {{ valid: boolean, errors: string[] }}
   */
  validate() {
    const errors = [];
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

    if (!this.participant_id || !uuidRegex.test(this.participant_id)) {
      errors.push(`Invalid participant_id: must be a UUID (got: ${this.participant_id})`);
    }
    if (!this.session_id || !uuidRegex.test(this.session_id)) {
      errors.push(`Invalid session_id: must be a UUID (got: ${this.session_id})`);
    }
    if (!VALID_TASK_TYPES.includes(this.task_type)) {
      errors.push(`Invalid task_type: must be one of [${VALID_TASK_TYPES.join(', ')}] (got: ${this.task_type})`);
    }
    if (isNaN(this.duration) || this.duration < 0) {
      errors.push('duration must be >= 0');
    }
    if (isNaN(this.movement_variability)) {
      errors.push('movement_variability must be a numeric value');
    }
    if (isNaN(this.quality_score) || this.quality_score < 0 || this.quality_score > 1.0) {
      errors.push('quality_score must be between 0.0 and 1.0');
    }
    if (!this.feature_version) {
      errors.push('feature_version must be specified');
    }

    return { valid: errors.length === 0, errors };
  }

  /**
   * Returns a Supabase-ready insertion payload.
   * Guaranteed to contain ZERO raw sensor data or PII.
   * @returns {Object}
   */
  toSupabasePayload() {
    const { valid, errors } = this.validate();
    if (!valid) {
      throw new Error(`MotorSession validation failed: ${errors.join('; ')}`);
    }

    return {
      participant_id:               this.participant_id,
      session_id:                   this.session_id,
      timestamp:                    this.timestamp,
      task_type:                    this.task_type,
      duration:                     this.duration,
      cadence:                      this.cadence,
      stride_variability:           this.stride_interval_variability,
      movement_variability:         this.movement_variability,
      tapping_rate:                 this.tapping_rate,
      tapping_interval_variability: this.tapping_interval_variability,
      tremor_frequency:             this.tremor_frequency,
      tremor_amplitude:             this.tremor_amplitude,
      quality_score:                this.quality_score,
      feature_version:              this.feature_version,
      synced:                       false, // always false on initial upload
    };
  }

  /**
   * Idempotent upload to Supabase motor_sessions table.
   * @param {Object} supabaseClient
   * @returns {Promise<{ success: boolean, data?, error?, idempotent: boolean }>}
   */
  async syncToSupabase(supabaseClient) {
    if (!supabaseClient) {
      return { success: false, error: 'Supabase client not provided.', idempotent: false };
    }

    const payload = this.toSupabasePayload();

    try {
      // Check for existing record (idempotency guard)
      const { data: existing, error: checkError } = await supabaseClient
        .from('motor_sessions')
        .select('id, session_id')
        .eq('session_id', this.session_id)
        .maybeSingle();

      if (checkError) {
        return { success: false, error: checkError.message, idempotent: false };
      }

      if (existing) {
        this.synced = true;
        return {
          success: true,
          data: existing,
          idempotent: true,
          message: 'Motor session already synced (idempotent skip).',
        };
      }

      const { data: inserted, error: insertError } = await supabaseClient
        .from('motor_sessions')
        .insert([payload])
        .select()
        .single();

      if (insertError) {
        return { success: false, error: insertError.message, idempotent: false };
      }

      this.synced = true;
      this.id = inserted.id;

      return {
        success: true,
        data: inserted,
        idempotent: false,
        message: 'Motor session successfully uploaded. Research screening result — not a clinical diagnosis.',
      };
    } catch (err) {
      return {
        success: false,
        error: err.message || 'Unknown error during Supabase sync.',
        idempotent: false,
      };
    }
  }

  _generateUUID() {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      return crypto.randomUUID();
    }
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function _nullable(val) {
  if (val === null || val === undefined || (typeof val === 'number' && isNaN(val))) {
    return null;
  }
  return Number(val);
}

function _requireParticipantId(participantId) {
  if (!participantId) {
    throw new Error('participant_id is mandatory to instantiate MotorSessionModel.');
  }
}
