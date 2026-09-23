/**
 * MPF Mobile Extension — Sync Manager Module (Phase 13)
 * 
 * Orchestrates offline-first synchronization between the mobile app and Supabase:
 * - Collects and preserves mobile feature records in encrypted local queue
 * - Verifies network availability prior to remote communication
 * - Idempotency enforcement via session_id, event_id, and deterministic idempotency_key
 * - Conflict resolution with authoritative "Server Wins" policy
 * - Partial sync resilience: failure of an individual record does not abort the batch
 * - Exponential backoff retry logic (1s, 2s, 4s, 8s, 16s, 32s, max 60s) with 5-retry limit
 * - Alerts user upon reaching max retries while preserving data locally without loss
 * - Periodic background synchronization and automatic trigger upon network reconnect
 * - Strictly non-diagnostic research framing: zero diagnostic claims in logs, status, or alerts
 */

import { OfflineQueue } from './offlineQueue.js';
import { ConflictResolver } from './conflictResolver.js';
import { calculateDelay, isRetryable, RETRY_CONFIG } from './retryLogic.js';
import { SyncStatusTracker, SYNC_STATES } from './syncStatusTracker.js';

export class SyncManager {
  /**
   * @param {Object} options
   * @param {Object} [options.supabaseClient] - Supabase JS client instance
   * @param {OfflineQueue} [options.queue] - OfflineQueue instance
   * @param {ConflictResolver} [options.conflictResolver] - ConflictResolver instance
   * @param {SyncStatusTracker} [options.statusTracker] - SyncStatusTracker instance
   * @param {boolean} [options.autoSync=true] - Trigger sync immediately on task completion
   * @param {number} [options.periodicIntervalMs=60000] - Periodic sync interval (default 60s)
   * @param {boolean} [options.enableAuditLog=true] - Log sync transactions to sync_audit_log
   */
  constructor(options = {}) {
    this.supabase = options.supabaseClient || null;
    this.queue = options.queue || new OfflineQueue();
    this.conflictResolver = options.conflictResolver || new ConflictResolver({ strategy: 'server_wins' });
    this.statusTracker = options.statusTracker || new SyncStatusTracker();
    this.autoSync = options.autoSync !== undefined ? options.autoSync : true;
    this.periodicIntervalMs = options.periodicIntervalMs || 60000;
    this.enableAuditLog = options.enableAuditLog !== undefined ? options.enableAuditLog : true;

    this._periodicTimer = null;
    this._isSyncInProgress = false;

    // Listen to network changes from tracker: auto-sync when connection restores
    this.statusTracker.on('network_change', async ({ isOnline }) => {
      if (isOnline && this.autoSync) {
        await this.syncNow();
      }
    });
  }

  /**
   * Initializes queue and checks for un-synced items from prior sessions.
   */
  async init() {
    await this.queue.init();
    this._updateTrackerStats();
    return this;
  }

  /**
   * Collects an observation record from a completed task and enqueues it locally.
   * If online and autoSync is enabled, immediately triggers synchronization.
   * 
   * @param {Object} recordData
   * @param {string} recordData.participant_id - Pseudonymous participant UUID
   * @param {string} recordData.table_name - Supabase table (e.g. 'typing_sessions')
   * @param {Object} recordData.payload - Extracted feature vector
   * @param {string} [recordData.session_id] - Unique session UUID
   * @param {string} [recordData.event_id] - Unique event UUID
   * @param {string} [recordData.timestamp] - ISO timestamp
   * @returns {Promise<Object>} Status of the collection and sync operation
   */
  async collectAndEnqueue(recordData) {
    // Step 1: Enqueue to local protected storage (never lose data)
    const enqueuedItem = await this.queue.enqueue(recordData);
    this._updateTrackerStats();

    // Step 2: Trigger immediate sync if network is available and autoSync is enabled
    if (this.statusTracker.isOnline && this.autoSync) {
      // Run sync in foreground or return result
      const syncResult = await this.syncNow();
      const updatedItem = this.queue.getItem(enqueuedItem.id) || enqueuedItem;
      return {
        enqueued: true,
        item: updatedItem,
        syncResult,
      };
    }

    // Network is offline: data securely stored in queue
    return {
      enqueued: true,
      item: enqueuedItem,
      synced: false,
      message: 'Network offline. Observation securely preserved in local queue.',
    };
  }

  /**
   * Synchronizes all pending items from the local queue to Supabase.
   * 
   * Implements:
   * - Pre-flight network check
   * - FIFO queue consumption
   * - Partial sync resilience: one failed item does not abort the remaining items
   * - Authoritative server-wins conflict resolution
   * - Exponential backoff retry recording
   * - User alerting upon max retries (5)
   * 
   * @returns {Promise<{ totalProcessed: number, syncedCount: number, failedCount: number, results: Array<Object> }>}
   */
  async syncNow() {
    if (this._isSyncInProgress) {
      return {
        totalProcessed: 0,
        syncedCount: 0,
        failedCount: 0,
        reason: 'Sync already in progress.',
        results: [],
      };
    }

    if (!this.statusTracker.isOnline) {
      this.statusTracker.setState(SYNC_STATES.OFFLINE);
      return {
        totalProcessed: 0,
        syncedCount: 0,
        failedCount: 0,
        reason: 'Network unavailable.',
        results: [],
      };
    }

    this._isSyncInProgress = true;
    this.statusTracker.setState(SYNC_STATES.SYNCING);

    const pendingItems = this.queue.getPending();
    const results = [];
    let syncedCount = 0;
    let failedCount = 0;

    for (const item of pendingItems) {
      try {
        await this.queue.markSyncing(item.id);

        // Upload to Supabase using conflict resolver
        const syncResponse = await this._syncSingleItem(item);

        if (syncResponse.success) {
          await this.queue.markSynced(item.id, syncResponse);
          syncedCount += 1;
          results.push({
            id: item.id,
            session_id: item.session_id,
            status: 'synced',
            resolution: syncResponse.resolution,
            conflict: syncResponse.conflict,
          });

          // Log to Supabase audit log if available
          await this._logSyncAudit({
            participant_id: item.participant_id,
            session_id: item.session_id,
            event_id: item.event_id,
            idempotency_key: item.idempotency_key,
            table_name: item.table_name,
            status: 'synced',
            conflict_resolved: syncResponse.conflict,
            resolution_strategy: this.conflictResolver.strategy,
            retry_count: item.retry_count,
            client_timestamp: item.timestamp,
            metadata: {
              resolution: syncResponse.resolution,
              differences: syncResponse.differences || [],
            },
          });
        } else {
          // Sync attempt failed for this individual record
          failedCount += 1;
          const error = syncResponse.error || new Error('Remote synchronization failed');
          await this._handleItemFailure(item, error);
          results.push({
            id: item.id,
            session_id: item.session_id,
            status: item.retry_count >= item.max_retries ? 'failed' : 'retry_scheduled',
            error: error.message,
            retry_count: item.retry_count,
          });
        }
      } catch (err) {
        // Partial sync: catch error for this item and continue processing remaining items
        failedCount += 1;
        await this._handleItemFailure(item, err);
        results.push({
          id: item.id,
          session_id: item.session_id,
          status: item.retry_count >= item.max_retries ? 'failed' : 'retry_scheduled',
          error: err.message,
          retry_count: item.retry_count,
        });
      }
    }

    this._isSyncInProgress = false;
    this._updateTrackerStats();

    if (this.queue.getStats().failed > 0) {
      this.statusTracker.setState(SYNC_STATES.ERROR, { failedCount });
    } else {
      this.statusTracker.setState(SYNC_STATES.IDLE);
    }

    return {
      totalProcessed: pendingItems.length,
      syncedCount,
      failedCount,
      results,
    };
  }

  /**
   * Syncs a single item to Supabase.
   * @private
   */
  async _syncSingleItem(item) {
    if (!this.supabase) {
      // Mock / Local simulated success if Supabase client not provided
      return {
        success: true,
        resolution: 'local_mock_synced',
        conflict: false,
        data: item.payload,
      };
    }

    return await this.conflictResolver.syncRecord(
      this.supabase,
      item.table_name,
      item.payload
    );
  }

  /**
   * Handles failure for an individual queue item:
   * - Evaluates error retryability
   * - Enforces max 5 retries
   * - Dispatches user alert when max retries exceeded
   * @private
   */
  async _handleItemFailure(item, error) {
    const retryable = isRetryable(error);
    const updated = await this.queue.markFailed(item.id, error, true);

    if (updated.status === 'failed' || !retryable) {
      // Max retries exceeded or fatal error -> alert user
      this.statusTracker.createMaxRetriesExceededAlert({
        sessionId: item.session_id,
        eventId: item.event_id,
        tableName: item.table_name,
        retryCount: updated.retry_count,
        errorMessage: updated.last_error,
      });

      // Audit log failed outcome
      await this._logSyncAudit({
        participant_id: item.participant_id,
        session_id: item.session_id,
        event_id: item.event_id,
        idempotency_key: item.idempotency_key,
        table_name: item.table_name,
        status: 'failed',
        conflict_resolved: false,
        resolution_strategy: this.conflictResolver.strategy,
        retry_count: updated.retry_count,
        error_message: updated.last_error,
        client_timestamp: item.timestamp,
        metadata: { fatal: !retryable },
      });
    }
  }

  /**
   * Records a sync transaction in Supabase sync_audit_log if client is active.
   * @private
   */
  async _logSyncAudit(auditEntry) {
    if (!this.enableAuditLog || !this.supabase) return;

    try {
      await this.supabase.from('sync_audit_log').insert(auditEntry);
    } catch {
      // Non-blocking: audit table failure should never crash the mobile sync flow
    }
  }

  /**
   * Starts periodic background synchronization.
   * @param {number} [intervalMs]
   */
  startPeriodicSync(intervalMs = null) {
    if (intervalMs) {
      this.periodicIntervalMs = intervalMs;
    }
    this.stopPeriodicSync();

    this._periodicTimer = setInterval(async () => {
      if (this.statusTracker.isOnline && !this._isSyncInProgress) {
        await this.syncNow();
      }
    }, this.periodicIntervalMs);

    return this;
  }

  /**
   * Stops periodic background synchronization.
   */
  stopPeriodicSync() {
    if (this._periodicTimer) {
      clearInterval(this._periodicTimer);
      this._periodicTimer = null;
    }
    return this;
  }

  /**
   * Synchronizes tracker statistics with queue stats.
   * @private
   */
  _updateTrackerStats() {
    const queueStats = this.queue.getStats();
    this.statusTracker.updateStats(queueStats);
  }

  /**
   * Returns current sync manager overview.
   */
  getStatus() {
    return {
      ...this.statusTracker.getSnapshot(),
      periodicSyncActive: this._periodicTimer !== null,
      periodicIntervalMs: this.periodicIntervalMs,
    };
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    SyncManager,
  };
}
