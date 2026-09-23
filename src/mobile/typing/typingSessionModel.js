/**
 * MPF Mobile Extension — Typing Session Model
 * 
 * Standardized data model and Supabase persistence client for typing dynamics.
 * 
 * Complies strictly with:
 * - Supabase `typing_sessions` table schema
 * - Privacy Model (ZERO text content, ONLY timing kinematics)
 * - Versioned reproducibility (feature_version = '1.0.0')
 * - Idempotent upload semantics via client-generated UUID session_id
 */

export const TASK_TYPES = {
  CONTROLLED_PHRASE: 'controlled_phrase',
  FREE_TYPING: 'free_typing'
};

export const CURRENT_FEATURE_VERSION = '1.0.0';

export class TypingSessionModel {
  /**
   * Constructs a typed, validated session record.
   * @param {Object} data
   */
  constructor(data = {}) {
    this.id = data.id || null;
    this.participant_id = data.participant_id;
    this.session_id = data.session_id || this._generateUUID();
    this.timestamp = data.timestamp || new Date().toISOString();
    this.task_type = data.task_type || TASK_TYPES.CONTROLLED_PHRASE;
    this.duration = Number(data.duration >= 0 ? data.duration : 0);
    this.typing_speed = Number(data.typing_speed >= 0 ? data.typing_speed : 0);
    this.mean_inter_key_interval = Number(data.mean_inter_key_interval >= 0 ? data.mean_inter_key_interval : 0);
    this.std_inter_key_interval = Number(data.std_inter_key_interval >= 0 ? data.std_inter_key_interval : 0);
    this.pause_rate = Number(data.pause_rate >= 0 ? data.pause_rate : 0);
    this.correction_rate = Number(data.correction_rate >= 0 ? data.correction_rate : 0);
    this.rhythm_variability = Number(data.rhythm_variability >= 0 ? data.rhythm_variability : 0);
    this.quality_score = Number(
      typeof data.quality_score === 'number' 
        ? Math.min(1.0, Math.max(0.0, data.quality_score))
        : 0.0
    );
    this.feature_version = data.feature_version || CURRENT_FEATURE_VERSION;
    this.synced = Boolean(data.synced || false);
  }

  /**
   * Factory method to build a validated model instance from raw features and quality score.
   */
  static fromFeatures({ participantId, sessionId, features, qualityResult }) {
    if (!participantId) {
      throw new Error("participant_id is mandatory to instantiate TypingSessionModel.");
    }

    return new TypingSessionModel({
      participant_id: participantId,
      session_id: sessionId,
      timestamp: new Date().toISOString(),
      task_type: TASK_TYPES.CONTROLLED_PHRASE,
      duration: features.session_duration,
      typing_speed: features.typing_speed,
      mean_inter_key_interval: features.mean_inter_key_interval,
      std_inter_key_interval: features.std_inter_key_interval,
      pause_rate: features.pause_rate,
      correction_rate: features.correction_rate,
      rhythm_variability: features.rhythm_variability,
      quality_score: qualityResult.quality_score,
      feature_version: features.feature_version || CURRENT_FEATURE_VERSION,
      synced: false
    });
  }

  /**
   * Validates data fields against PostgreSQL check constraints.
   * @returns {{ valid: boolean, errors: string[] }}
   */
  validate() {
    const errors = [];

    // UUID format verification
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!this.participant_id || !uuidRegex.test(this.participant_id)) {
      errors.push(`Invalid participant_id: must be a valid UUID string (got: ${this.participant_id})`);
    }
    if (!this.session_id || !uuidRegex.test(this.session_id)) {
      errors.push(`Invalid session_id: must be a valid UUID string (got: ${this.session_id})`);
    }

    // Task type check
    if (![TASK_TYPES.CONTROLLED_PHRASE, TASK_TYPES.FREE_TYPING].includes(this.task_type)) {
      errors.push(`Invalid task_type: must be 'controlled_phrase' or 'free_typing' (got: ${this.task_type})`);
    }

    // Numeric check constraints
    if (isNaN(this.duration) || this.duration < 0) errors.push("duration must be >= 0");
    if (isNaN(this.typing_speed) || this.typing_speed < 0) errors.push("typing_speed must be >= 0");
    if (isNaN(this.mean_inter_key_interval) || this.mean_inter_key_interval < 0) errors.push("mean_inter_key_interval must be >= 0");
    if (isNaN(this.std_inter_key_interval) || this.std_inter_key_interval < 0) errors.push("std_inter_key_interval must be >= 0");
    if (isNaN(this.pause_rate) || this.pause_rate < 0) errors.push("pause_rate must be >= 0");
    if (isNaN(this.correction_rate) || this.correction_rate < 0) errors.push("correction_rate must be >= 0");
    if (isNaN(this.rhythm_variability) || this.rhythm_variability < 0) errors.push("rhythm_variability must be >= 0");
    if (isNaN(this.quality_score) || this.quality_score < 0 || this.quality_score > 1.0) {
      errors.push("quality_score must be between 0.0 and 1.0");
    }

    return {
      valid: errors.length === 0,
      errors
    };
  }

  /**
   * Formats the record directly for Supabase table insertion.
   * Guaranteed ZERO text fields or PII.
   */
  toSupabasePayload() {
    const validation = this.validate();
    if (!validation.valid) {
      throw new Error(`TypingSession validation failed: ${validation.errors.join("; ")}`);
    }

    return {
      participant_id: this.participant_id,
      session_id: this.session_id,
      timestamp: this.timestamp,
      task_type: this.task_type,
      duration: this.duration,
      typing_speed: this.typing_speed,
      mean_inter_key_interval: this.mean_inter_key_interval,
      std_inter_key_interval: this.std_inter_key_interval,
      pause_rate: this.pause_rate,
      correction_rate: this.correction_rate,
      rhythm_variability: this.rhythm_variability,
      quality_score: this.quality_score,
      feature_version: this.feature_version,
      synced: this.synced
    };
  }

  /**
   * Uploads session to Supabase database.
   * Utilizes session_id idempotency to prevent duplicate insertion.
   * @param {Object} supabaseClient
   * @returns {Promise<{ success: boolean, data?: Object, error?: string, idempotent: boolean }>}
   */
  async syncToSupabase(supabaseClient) {
    if (!supabaseClient) {
      return { success: false, error: "Supabase client not provided.", idempotent: false };
    }

    const payload = this.toSupabasePayload();

    try {
      // Check for existing session with this session_id (idempotency key)
      const { data: existing, error: checkError } = await supabaseClient
        .from('typing_sessions')
        .select('id, session_id')
        .eq('session_id', this.session_id)
        .maybeSingle();

      if (checkError) {
        return { success: false, error: checkError.message, idempotent: false };
      }

      if (existing) {
        // Record already safely persisted
        this.synced = true;
        return { 
          success: true, 
          data: existing, 
          idempotent: true, 
          message: "Session already uploaded (idempotency enforced)." 
        };
      }

      // Insert new typing session
      const { data: inserted, error: insertError } = await supabaseClient
        .from('typing_sessions')
        .insert([{ ...payload, synced: true }])
        .select()
        .single();

      if (insertError) {
        return { success: false, error: insertError.message, idempotent: false };
      }

      this.synced = true;
      this.id = inserted.id;
      return { success: true, data: inserted, idempotent: false };
    } catch (err) {
      return { success: false, error: err.message, idempotent: false };
    }
  }

  _generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }
}
