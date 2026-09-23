/**
 * MPF Mobile Extension — Conflict Resolver Module (Phase 13)
 * 
 * Implements idempotency enforcement and conflict resolution for Supabase sync:
 * - Deterministic idempotency key: session_id + participant_id + timestamp
 * - Authoritative conflict resolution strategy: SERVER WINS (server data takes precedence)
 * - Identifies and gracefully handles duplicate uploads without creating duplicate database rows
 * - Generates conflict audit metadata logging divergent fields and resolution decisions
 */

const cryptoModule = typeof require !== 'undefined' ? require('crypto') : null;

/**
 * Generates a deterministic idempotency key from session_id, participant_id, and timestamp.
 * 
 * @param {string} sessionId - Unique session UUID
 * @param {string} participantId - Pseudonymous participant UUID
 * @param {string|Date} timestamp - ISO-8601 timestamp string or Date object
 * @returns {string} Deterministic idempotency key string
 */
export function generateIdempotencyKey(sessionId, participantId, timestamp) {
  if (!sessionId || !participantId) {
    throw new Error('sessionId and participantId are required to generate an idempotency key.');
  }

  const isoTime = timestamp instanceof Date ? timestamp.toISOString() : String(timestamp || '');
  const rawKey = `${sessionId}_${participantId}_${isoTime}`;

  // Optionally hash with SHA-256 for a compact fixed-length key if crypto is available
  try {
    if (cryptoModule && cryptoModule.createHash) {
      const hash = cryptoModule.createHash('sha256').update(rawKey).digest('hex').substring(0, 32);
      return `idmp_${hash}`;
    }
  } catch {
    // fallback to string format
  }

  return `idmp_${rawKey.replace(/[^a-zA-Z0-9_-]/g, '_')}`;
}

/**
 * Compares two objects and identifies differing keys.
 * Ignores system-managed timestamps like updated_at or created_at if requested.
 * 
 * @param {Object} objA 
 * @param {Object} objB 
 * @param {Array<string>} [ignoredFields=['updated_at', 'created_at', 'synced_at']]
 * @returns {Array<string>} Array of property names that differ
 */
export function getDivergentFields(objA, objB, ignoredFields = ['id', 'updated_at', 'created_at', 'synced_at', 'synced']) {
  if (!objA || !objB) return [];

  const allKeys = new Set([...Object.keys(objA), ...Object.keys(objB)]);
  const differences = [];

  for (const key of allKeys) {
    if (ignoredFields.includes(key)) continue;

    const valA = objA[key];
    const valB = objB[key];

    // Deep comparison for nested objects/arrays or JSON strings
    const strA = typeof valA === 'object' && valA !== null ? JSON.stringify(valA) : String(valA ?? '');
    const strB = typeof valB === 'object' && valB !== null ? JSON.stringify(valB) : String(valB ?? '');

    if (strA !== strB) {
      differences.push(key);
    }
  }

  return differences;
}

/**
 * ConflictResolver enforces the "Server Wins" policy for synchronization conflicts.
 */
export class ConflictResolver {
  /**
   * @param {Object} [options]
   * @param {string} [options.strategy='server_wins'] - Authoritative conflict strategy
   */
  constructor(options = {}) {
    this.strategy = options.strategy || 'server_wins';
  }

  /**
   * Resolves conflict between local queue payload and server-persisted record.
   * 
   * Strategy: "server wins"
   * - If server record exists, server record is authoritative.
   * - If records have identical content, flagged as idempotent match.
   * - If records diverge, server version is retained and differences are documented.
   * 
   * @param {Object} localRecord - Local feature vector payload
   * @param {Object|null} serverRecord - Existing record fetched from Supabase
   * @returns {{ conflict: boolean, resolution: string, resolvedRecord: Object, differences: Array<string> }}
   */
  resolve(localRecord, serverRecord) {
    if (!serverRecord) {
      return {
        conflict: false,
        resolution: 'local_inserted',
        resolvedRecord: localRecord,
        differences: [],
      };
    }

    const differences = getDivergentFields(localRecord, serverRecord);

    if (differences.length === 0) {
      return {
        conflict: false,
        resolution: 'idempotent_match',
        resolvedRecord: serverRecord,
        differences: [],
      };
    }

    // Differences detected -> Server Wins
    return {
      conflict: true,
      resolution: 'server_wins',
      resolvedRecord: { ...serverRecord },
      differences,
      audit: {
        resolved_at: new Date().toISOString(),
        strategy: this.strategy,
        divergent_fields: differences,
      },
    };
  }

  /**
   * Synchronizes a single record with Supabase, applying idempotency checks and server-wins resolution.
   * 
   * @param {Object} supabaseClient 
   * @param {string} tableName 
   * @param {Object} payload 
   * @returns {Promise<{ success: boolean, resolution: string, data: Object, conflict: boolean, error?: any }>}
   */
  async syncRecord(supabaseClient, tableName, payload) {
    if (!supabaseClient) {
      throw new Error('Supabase client is required for remote synchronization.');
    }
    if (!tableName || !payload) {
      throw new Error('tableName and payload are required for synchronization.');
    }

    const sessionId = payload.session_id;
    if (!sessionId) {
      throw new Error('payload.session_id is required for idempotency enforcement.');
    }

    try {
      // Step 1: Check if record with this session_id already exists on server
      const { data: existing, error: checkError } = await supabaseClient
        .from(tableName)
        .select('*')
        .eq('session_id', sessionId)
        .maybeSingle();

      if (checkError && checkError.code !== 'PGRST116') {
        throw checkError;
      }

      if (existing) {
        // Record already exists -> execute conflict resolution (server wins)
        const resolutionResult = this.resolve(payload, existing);
        return {
          success: true,
          resolution: resolutionResult.resolution,
          conflict: resolutionResult.conflict,
          data: resolutionResult.resolvedRecord,
          differences: resolutionResult.differences,
        };
      }

      // Step 2: New record -> Insert cleanly
      const payloadToInsert = {
        ...payload,
        synced: true,
      };

      const res = await supabaseClient
        .from(tableName)
        .insert(payloadToInsert)
        .select()
        .single();

      const insertError = res?.error;
      const inserted = res?.data;

      if (insertError) {
        // Handle concurrent insert race condition (PostgreSQL 23505 unique constraint violation)
        if (insertError.code === '23505' || String(insertError.message).includes('duplicate key')) {
          const { data: racedExisting } = await supabaseClient
            .from(tableName)
            .select('*')
            .eq('session_id', sessionId)
            .single();

          if (racedExisting) {
            const resolved = this.resolve(payload, racedExisting);
            return {
              success: true,
              resolution: resolved.resolution,
              conflict: resolved.conflict,
              data: resolved.resolvedRecord,
              differences: resolved.differences,
            };
          }
        }
        throw insertError;
      }

      return {
        success: true,
        resolution: 'inserted',
        conflict: false,
        data: inserted || payloadToInsert,
        differences: [],
      };
    } catch (err) {
      // If error was a duplicate key exception thrown by mock or client
      if (err && (err.code === '23505' || String(err.message).includes('duplicate key'))) {
        try {
          const { data: racedExisting } = await supabaseClient
            .from(tableName)
            .select('*')
            .eq('session_id', sessionId)
            .single();

          if (racedExisting) {
            const resolved = this.resolve(payload, racedExisting);
            return {
              success: true,
              resolution: resolved.resolution,
              conflict: resolved.conflict,
              data: resolved.resolvedRecord,
              differences: resolved.differences,
            };
          }
        } catch {
          // fall through
        }
      }

      return {
        success: false,
        resolution: 'failed',
        conflict: false,
        data: null,
        error: err,
      };
    }
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    generateIdempotencyKey,
    getDivergentFields,
    ConflictResolver,
  };
}
