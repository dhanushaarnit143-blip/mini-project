/**
 * MPF Mobile Extension — Sleep Session Model (Phase 8)
 *
 * Standardized data model and Supabase persistence client for daily sleep
 * and probable RBD self-report sessions.
 *
 * Complies strictly with:
 * - Supabase `sleep_sessions` table schema (migrations 007 & 018)
 * - Research non-diagnostic disclaimer standards
 * - Idempotent upsert semantics via client-generated UUID `session_id`
 * - Versioned reproducibility (`questionnaire_version = "1.0"`)
 * - Privacy first: explicit participant-initiated survey, no sensitive telemetry
 */

import {
  computeSleepScore,
  QUESTIONNAIRE_VERSION,
  SLEEP_LABELS,
  MOVEMENT_RESPONSES,
} from './sleepScorer.js';

export const CURRENT_QUESTIONNAIRE_VERSION = QUESTIONNAIRE_VERSION;

function _requireParticipantId(id) {
  if (!id || typeof id !== 'string' || id.trim().length === 0) {
    throw new Error('participant_id is mandatory and cannot be empty.');
  }
}

/**
 * SleepSessionModel — validated session record for the sleep_sessions table.
 */
export class SleepSessionModel {
  /**
   * @param {Object} data - Raw session parameters.
   */
  constructor(data = {}) {
    this.id                          = data.id || null;
    this.participant_id              = data.participant_id || null;
    this.session_id                  = data.session_id || this._generateUUID();
    this.timestamp                   = data.timestamp || new Date().toISOString();
    this.sleep_duration              = Number(data.sleep_duration !== undefined ? data.sleep_duration : 0);
    this.sleep_quality               = Number(data.sleep_quality !== undefined ? data.sleep_quality : 3);
    this.unusual_movement_self_report= Boolean(data.unusual_movement_self_report || false);
    this.movement_response           = data.movement_response || (this.unusual_movement_self_report ? 'yes' : 'no');
    this.daytime_sleepiness          = Number(data.daytime_sleepiness !== undefined ? data.daytime_sleepiness : 1);
    this.medication_change           = data.medication_change !== undefined && data.medication_change !== null
      ? Boolean(data.medication_change)
      : null;
    this.medication_change_details   = data.medication_change_details || null;
    this.questionnaire_version       = data.questionnaire_version || CURRENT_QUESTIONNAIRE_VERSION;
    this.score                       = Number(data.score !== undefined ? data.score : 0);
    this.rbd_flag_label              = data.rbd_flag_label || SLEEP_LABELS.NO_PATTERN;
    this.synced                      = Boolean(data.synced || false);
  }

  /**
   * Factory method — creates and scores a SleepSessionModel from completed questionnaire responses.
   *
   * @param {Object} params
   * @param {string} params.participantId - UUID of the participant
   * @param {string} [params.sessionId] - Client-generated UUID
   * @param {number} params.sleepDuration - Hours slept (0 to 14)
   * @param {number} params.sleepQuality - Rating 1 to 5
   * @param {string} params.movementResponse - 'yes', 'no', 'not_sure', 'dont_know'
   * @param {number} params.daytimeSleepiness - Rating 1 to 5
   * @param {boolean|null} [params.medicationChange] - Optional medication change status
   * @param {string|null} [params.medicationDetails] - Optional medication details
   * @param {string} [params.rbdFlagLabel] - Longitudinal RBD concern flag if evaluated
   * @returns {SleepSessionModel}
   */
  static fromQuestionnaire({
    participantId,
    sessionId,
    sleepDuration,
    sleepQuality,
    movementResponse,
    daytimeSleepiness,
    medicationChange = null,
    medicationDetails = null,
    rbdFlagLabel = SLEEP_LABELS.NO_PATTERN,
  }) {
    _requireParticipantId(participantId);

    const normResponse = String(movementResponse || 'no').trim().toLowerCase();
    const unusualMovementBool = normResponse === MOVEMENT_RESPONSES.YES;

    const scoreResult = computeSleepScore({
      sleepDuration,
      sleepQuality,
      unusualMovement: normResponse,
      daytimeSleepiness,
    });

    return new SleepSessionModel({
      participant_id: participantId,
      session_id: sessionId,
      sleep_duration: Number(sleepDuration),
      sleep_quality: Number(sleepQuality),
      unusual_movement_self_report: unusualMovementBool,
      movement_response: normResponse,
      daytime_sleepiness: Number(daytimeSleepiness),
      medication_change: medicationChange !== null ? Boolean(medicationChange) : null,
      medication_change_details: medicationDetails ? String(medicationDetails).trim() : null,
      questionnaire_version: CURRENT_QUESTIONNAIRE_VERSION,
      score: scoreResult.score,
      rbd_flag_label: rbdFlagLabel,
      synced: false,
    });
  }

  /**
   * Validates the session model against database constraints and clinical logic.
   *
   * @returns {{ valid: boolean, errors: string[] }}
   */
  validate() {
    const errors = [];

    if (!this.participant_id || typeof this.participant_id !== 'string') {
      errors.push('participant_id is required.');
    } else if (
      !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(this.participant_id)
    ) {
      errors.push(`participant_id must be a valid UUID; got "${this.participant_id}".`);
    }

    if (!this.session_id || typeof this.session_id !== 'string') {
      errors.push('session_id is required.');
    } else if (
      !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(this.session_id)
    ) {
      errors.push(`session_id must be a valid UUID; got "${this.session_id}".`);
    }

    if (typeof this.sleep_duration !== 'number' || this.sleep_duration < 0 || this.sleep_duration > 24) {
      errors.push(`sleep_duration must be between 0.0 and 24.0 hours; got "${this.sleep_duration}".`);
    }

    if (typeof this.sleep_quality !== 'number' || this.sleep_quality < 1 || this.sleep_quality > 5) {
      errors.push(`sleep_quality must be between 1.0 and 5.0; got "${this.sleep_quality}".`);
    }

    if (typeof this.unusual_movement_self_report !== 'boolean') {
      errors.push('unusual_movement_self_report must be a boolean.');
    }

    if (typeof this.daytime_sleepiness !== 'number' || this.daytime_sleepiness < 1 || this.daytime_sleepiness > 5) {
      errors.push(`daytime_sleepiness must be between 1.0 and 5.0; got "${this.daytime_sleepiness}".`);
    }

    if (this.medication_change !== null && typeof this.medication_change !== 'boolean') {
      errors.push('medication_change must be null or a boolean.');
    }

    if (typeof this.score !== 'number' || this.score < 0 || this.score > 100) {
      errors.push(`score must be between 0 and 100; got "${this.score}".`);
    }

    return { valid: errors.length === 0, errors };
  }

  /**
   * Converts the model to the exact payload expected by the Supabase `sleep_sessions` table.
   *
   * @returns {Object} Database row representation
   */
  toPayload() {
    const v = this.validate();
    if (!v.valid) {
      throw new Error(`Cannot export invalid SleepSessionModel: ${v.errors.join('; ')}`);
    }

    return {
      participant_id:               this.participant_id,
      session_id:                   this.session_id,
      timestamp:                    this.timestamp,
      sleep_duration:               this.sleep_duration,
      sleep_quality:                this.sleep_quality,
      unusual_movement_self_report: this.unusual_movement_self_report,
      movement_response:            this.movement_response,
      daytime_sleepiness:           this.daytime_sleepiness,
      medication_change:            this.medication_change,
      medication_change_details:    this.medication_change_details,
      questionnaire_version:        this.questionnaire_version,
      score:                        this.score,
      rbd_flag_label:               this.rbd_flag_label,
      synced:                       this.synced,
    };
  }

  /**
   * Synchronizes the session record to the Supabase sleep_sessions table.
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
        .from('sleep_sessions')
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
