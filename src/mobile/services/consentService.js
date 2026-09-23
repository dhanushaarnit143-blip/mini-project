/**
 * MPF Mobile Extension — Consent Management Service
 * 
 * Manages participant informed consent lifecycle:
 * - Versioned consent recording (consent_version, timestamp, granted)
 * - Granular permission registration (data_collection, audio_storage, research_export, sensors)
 * - Consent verification prior to any sensor activation or data collection
 * - Consent revocation workflow with timestamp tracking and immediate collection halt
 * 
 * Strict Compliance: Zero diagnostic claims; Research prototype disclaimer enforced.
 */

export const CURRENT_CONSENT_VERSION = '1.0.0';

export const CONSENT_TYPES = {
  DATA_COLLECTION: 'data_collection',
  AUDIO_STORAGE: 'audio_storage',
  RESEARCH_EXPORT: 'research_export',
  DELETION: 'deletion',
  CAMERA_ACCESS: 'camera_access',
  MICROPHONE_ACCESS: 'microphone_access',
  MOTION_ACCESS: 'motion_access',
  KEYBOARD_ACCESS: 'keyboard_access'
};

export const SENSOR_MODALITY_MAP = {
  typing: 'keyboard_access',
  voice: 'microphone_access',
  motor: 'motion_access',
  visual: 'camera_access'
};

export class ConsentService {
  constructor(supabaseClient = null) {
    this.supabase = supabaseClient;
    // Local in-memory cache for fast offline permission gating
    this._consentCache = new Map();
  }

  /**
   * Generates a pseudonymous identifier from UUID or cryptographic salt.
   * Never stores or links raw personal identifiers (PII).
   */
  static generatePseudonymousId(seed = null) {
    const raw = seed || (typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2));
    let hash = 0;
    for (let i = 0; i < raw.length; i++) {
      hash = ((hash << 5) - hash) + raw.charCodeAt(i);
      hash |= 0;
    }
    const hex = Math.abs(hash).toString(16).padStart(8, '0');
    return `ps_${hex}_${Date.now().toString(36)}`;
  }

  /**
   * Records initial informed consent for a participant across all chosen categories.
   * @param {Object} params
   * @param {string} params.participantId - UUID of the participant
   * @param {string} params.consentVersion - Version string (e.g. '1.0.0')
   * @param {Object} params.consents - Object mapping consent types to boolean grant states
   * @returns {Promise<Object>} Created consent records summary
   */
  async recordConsent({ participantId, consentVersion = CURRENT_CONSENT_VERSION, consents = {} }) {
    if (!participantId) {
      throw new Error('participantId is required to record consent.');
    }

    if (!consents[CONSENT_TYPES.DATA_COLLECTION]) {
      throw new Error('Informed consent for basic data collection is required to participate in MPF research.');
    }

    const timestamp = new Date().toISOString();
    const recordsToInsert = [];

    // Always record basic data collection consent
    recordsToInsert.push({
      participant_id: participantId,
      consent_type: CONSENT_TYPES.DATA_COLLECTION,
      consent_version: consentVersion,
      granted: true,
      timestamp: timestamp,
      revoked_at: null
    });

    // Process optional and granular sensor consents
    const optionalTypes = [
      CONSENT_TYPES.AUDIO_STORAGE,
      CONSENT_TYPES.RESEARCH_EXPORT,
      CONSENT_TYPES.CAMERA_ACCESS,
      CONSENT_TYPES.MICROPHONE_ACCESS,
      CONSENT_TYPES.MOTION_ACCESS,
      CONSENT_TYPES.KEYBOARD_ACCESS
    ];

    for (const type of optionalTypes) {
      if (consents[type] === true) {
        recordsToInsert.push({
          participant_id: participantId,
          consent_type: type,
          consent_version: consentVersion,
          granted: true,
          timestamp: timestamp,
          revoked_at: null
        });
      }
    }

    // Update in-memory cache
    const activeSet = new Set(recordsToInsert.map(r => r.consent_type));
    this._consentCache.set(participantId, activeSet);

    // Persist to Supabase if client is supplied
    if (this.supabase) {
      // 1. Update participant consent version and timestamp
      const { error: partErr } = await this.supabase
        .from('participants')
        .update({
          consent_version: consentVersion,
          consent_timestamp: timestamp
        })
        .eq('id', participantId);

      if (partErr) {
        throw new Error(`Failed to update participant consent header: ${partErr.message}`);
      }

      // 2. Insert granular consent records
      const { data, error: consentErr } = await this.supabase
        .from('consent_records')
        .insert(recordsToInsert)
        .select();

      if (consentErr) {
        throw new Error(`Failed to insert consent records: ${consentErr.message}`);
      }

      return {
        success: true,
        participantId,
        consentVersion,
        timestamp,
        grantedTypes: Array.from(activeSet),
        records: data
      };
    }

    return {
      success: true,
      participantId,
      consentVersion,
      timestamp,
      grantedTypes: Array.from(activeSet),
      records: recordsToInsert
    };
  }

  /**
   * Checks whether a participant has active, unrevoked consent for a specific category or sensor.
   * @param {string} participantId 
   * @param {string} consentType 
   * @returns {Promise<boolean>}
   */
  async checkConsent(participantId, consentType) {
    if (!participantId || !consentType) return false;

    // Fast check if basic data collection was revoked
    if (this._consentCache.has(participantId)) {
      const active = this._consentCache.get(participantId);
      if (!active.has(CONSENT_TYPES.DATA_COLLECTION)) {
        return false;
      }
      return active.has(consentType);
    }

    if (this.supabase) {
      const { data, error } = await this.supabase
        .from('consent_records')
        .select('granted, revoked_at')
        .eq('participant_id', participantId)
        .eq('consent_type', consentType)
        .order('timestamp', { ascending: false })
        .limit(1)
        .maybeSingle();

      if (error || !data) return false;
      return data.granted === true && data.revoked_at === null;
    }

    return false;
  }

  /**
   * Validates whether data collection is authorized for a specific modality before starting sensor capture.
   * Throws an explicit error if consent is absent or revoked.
   * @param {string} participantId 
   * @param {string} modality - 'typing' | 'voice' | 'motor' | 'visual'
   */
  async assertAuthorizedCollection(participantId, modality) {
    const hasBase = await this.checkConsent(participantId, CONSENT_TYPES.DATA_COLLECTION);
    if (!hasBase) {
      throw new Error(`Data collection unauthorized: Participant ${participantId} has not granted or has revoked basic research data collection consent.`);
    }

    const sensorType = SENSOR_MODALITY_MAP[modality];
    if (sensorType) {
      const hasSensor = await this.checkConsent(participantId, sensorType);
      if (!hasSensor) {
        throw new Error(`Sensor access unauthorized: Participant ${participantId} has not granted permission for ${sensorType} (${modality} tasks).`);
      }
    }

    return true;
  }

  /**
   * Revokes a specific consent category or all consents for a participant.
   * @param {string} participantId 
   * @param {string} consentType - Specific type to revoke, or 'all' to halt everything
   * @param {string} reason - Optional audit note
   * @returns {Promise<Object>}
   */
  async revokeConsent(participantId, consentType = 'all', reason = 'Participant requested revocation') {
    if (!participantId) {
      throw new Error('participantId is required to revoke consent.');
    }

    const revokedAt = new Date().toISOString();

    if (this._consentCache.has(participantId)) {
      const active = this._consentCache.get(participantId);
      if (consentType === 'all' || consentType === CONSENT_TYPES.DATA_COLLECTION) {
        active.clear();
      } else {
        active.delete(consentType);
      }
    }

    if (this.supabase) {
      let query = this.supabase
        .from('consent_records')
        .update({
          revoked_at: revokedAt,
          granted: false
        })
        .eq('participant_id', participantId)
        .is('revoked_at', null);

      if (consentType !== 'all') {
        query = query.eq('consent_type', consentType);
      }

      const { data, error } = await query.select();
      if (error) {
        throw new Error(`Failed to revoke consent in database: ${error.message}`);
      }

      return {
        success: true,
        participantId,
        revokedType: consentType,
        revokedAt,
        reason,
        affectedRecords: data ? data.length : 0
      };
    }

    return {
      success: true,
      participantId,
      revokedType: consentType,
      revokedAt,
      reason,
      affectedRecords: 1
    };
  }

  /**
   * Retrieves full consent audit history and current state for a participant.
   * @param {string} participantId 
   */
  async getConsentStatus(participantId) {
    if (!participantId) throw new Error('participantId required.');

    if (this.supabase) {
      const { data, error } = await this.supabase
        .from('consent_records')
        .select('*')
        .eq('participant_id', participantId)
        .order('timestamp', { ascending: false });

      if (error) throw new Error(`Failed to retrieve consent status: ${error.message}`);

      const activeConsents = {};
      for (const rec of (data || [])) {
        if (!activeConsents.hasOwnProperty(rec.consent_type)) {
          activeConsents[rec.consent_type] = rec.granted && rec.revoked_at === null;
        }
      }

      return {
        participantId,
        activeConsents,
        history: data || []
      };
    }

    return {
      participantId,
      activeConsents: Object.fromEntries(
        (this._consentCache.get(participantId) || new Set()).entries()
      ),
      history: []
    };
  }
}

export default ConsentService;
