/**
 * MPF Mobile Extension — Voice Session Model (Phase 5)
 * 
 * Standardized data model and Supabase persistence client for acoustic voice biomarkers.
 * 
 * Complies strictly with:
 * - Supabase `voice_sessions` table schema
 * - Privacy Model (ZERO raw audio stored/uploaded, ONLY acoustic features)
 * - Versioned reproducibility (feature_version = '1.0.0')
 * - Idempotent upload semantics via client-generated UUID session_id
 */

export const TASK_TYPES = {
  SUSTAINED_VOWEL: 'sustained_vowel',
  READ_SENTENCE: 'read_sentence',
  FREE_SPEECH: 'free_speech'
};

export const CURRENT_FEATURE_VERSION = '1.0.0';

export class VoiceSessionModel {
  /**
   * Constructs a typed, validated voice session record.
   * @param {Object} data
   */
  constructor(data = {}) {
    this.id = data.id || null;
    this.participant_id = data.participant_id;
    this.session_id = data.session_id || this._generateUUID();
    this.timestamp = data.timestamp || new Date().toISOString();
    this.task_type = data.task_type || TASK_TYPES.SUSTAINED_VOWEL;
    this.duration = Number(data.duration >= 0 ? data.duration : 0);
    this.signal_quality = Number(
      typeof data.signal_quality === 'number'
        ? Math.min(1.0, Math.max(0.0, data.signal_quality))
        : 0.0
    );
    this.jitter = Number(data.jitter >= 0 ? data.jitter : 0);
    this.shimmer = Number(data.shimmer >= 0 ? data.shimmer : 0);
    this.hnr = Number(typeof data.hnr === 'number' ? data.hnr : 0);
    this.pitch_mean = Number(data.pitch_mean >= 0 ? data.pitch_mean : 0);
    this.pitch_std = Number(data.pitch_std >= 0 ? data.pitch_std : 0);
    this.mfcc_features = Array.isArray(data.mfcc_features) ? data.mfcc_features : [];
    this.spectral_features = (typeof data.spectral_features === 'object' && data.spectral_features !== null)
      ? data.spectral_features
      : { spectral_centroid: 0, spectral_bandwidth: 0, spectral_rolloff: 0 };
    this.quality_score = Number(
      typeof data.quality_score === 'number'
        ? Math.min(1.0, Math.max(0.0, data.quality_score))
        : 0.0
    );
    this.feature_version = data.feature_version || CURRENT_FEATURE_VERSION;
    this.synced = Boolean(data.synced || false);
  }

  /**
   * Factory method to build a validated model instance from extracted features and quality score.
   */
  static fromFeatures({ participantId, sessionId, taskType, features, qualityResult }) {
    if (!participantId) {
      throw new Error("participant_id is mandatory to instantiate VoiceSessionModel.");
    }

    return new VoiceSessionModel({
      participant_id: participantId,
      session_id: sessionId,
      timestamp: new Date().toISOString(),
      task_type: taskType || TASK_TYPES.SUSTAINED_VOWEL,
      duration: features.duration,
      signal_quality: features.signal_quality,
      jitter: features.jitter,
      shimmer: features.shimmer,
      hnr: features.hnr,
      pitch_mean: features.pitch_mean,
      pitch_std: features.pitch_std,
      mfcc_features: features.mfcc_features,
      spectral_features: features.spectral_features,
      quality_score: qualityResult ? qualityResult.quality_score : 0.0,
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
    const validTaskTypes = [TASK_TYPES.SUSTAINED_VOWEL, TASK_TYPES.READ_SENTENCE, TASK_TYPES.FREE_SPEECH];
    if (!validTaskTypes.includes(this.task_type)) {
      errors.push(`Invalid task_type: must be one of [${validTaskTypes.join(', ')}] (got: ${this.task_type})`);
    }

    // Numeric check constraints
    if (isNaN(this.duration) || this.duration < 0) errors.push("duration must be >= 0");
    if (isNaN(this.signal_quality) || this.signal_quality < 0 || this.signal_quality > 1.0) {
      errors.push("signal_quality must be between 0.0 and 1.0");
    }
    if (isNaN(this.jitter) || this.jitter < 0) errors.push("jitter must be >= 0");
    if (isNaN(this.shimmer) || this.shimmer < 0) errors.push("shimmer must be >= 0");
    if (isNaN(this.hnr)) errors.push("hnr must be a valid numeric value");
    if (isNaN(this.pitch_mean) || this.pitch_mean < 0) errors.push("pitch_mean must be >= 0");
    if (isNaN(this.pitch_std) || this.pitch_std < 0) errors.push("pitch_std must be >= 0");

    // Arrays & Objects
    if (!Array.isArray(this.mfcc_features) || this.mfcc_features.length === 0) {
      errors.push("mfcc_features must be a non-empty array of coefficients");
    }
    if (typeof this.spectral_features !== 'object' || this.spectral_features === null) {
      errors.push("spectral_features must be a JSON object");
    }

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
   * Guaranteed ZERO raw audio or PII fields.
   */
  toSupabasePayload() {
    const validation = this.validate();
    if (!validation.valid) {
      throw new Error(`VoiceSession validation failed: ${validation.errors.join("; ")}`);
    }

    return {
      participant_id: this.participant_id,
      session_id: this.session_id,
      timestamp: this.timestamp,
      task_type: this.task_type,
      duration: this.duration,
      signal_quality: this.signal_quality,
      jitter: this.jitter,
      shimmer: this.shimmer,
      hnr: this.hnr,
      pitch_mean: this.pitch_mean,
      pitch_std: this.pitch_std,
      mfcc_features: this.mfcc_features,
      spectral_features: this.spectral_features,
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
        .from('voice_sessions')
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
          message: "Session already synced (idempotent skip)."
        };
      }

      // Perform insertion
      const { data: inserted, error: insertError } = await supabaseClient
        .from('voice_sessions')
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
        message: "Voice session successfully uploaded."
      };
    } catch (err) {
      return {
        success: false,
        error: err.message || "Unknown error during Supabase sync.",
        idempotent: false
      };
    }
  }

  _generateUUID() {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      return crypto.randomUUID();
    }
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }
}
