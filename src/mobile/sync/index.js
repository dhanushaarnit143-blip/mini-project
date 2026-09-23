/**
 * MPF Mobile Extension — Sync Package Index (Phase 13)
 * 
 * Exports all offline-first synchronization and Supabase persistence components:
 * - OfflineQueue: Encrypted local FIFO temporary queue with pluggable storage
 * - ConflictResolver: Idempotency enforcement and authoritative "Server Wins" policy
 * - RetryLogic: Exponential backoff (1s, 2s, 4s, 8s, 16s, 32s, max 60s) and error classification
 * - SyncStatusTracker: Network state, sync status machine, and non-diagnostic user alerts
 * - SyncManager: High-level orchestrator with partial sync resilience and periodic sync
 */

export * from './offlineQueue.js';
export * from './retryLogic.js';
export * from './conflictResolver.js';
export * from './syncStatusTracker.js';
export * from './syncManager.js';

if (typeof module !== 'undefined' && module.exports) {
  const offlineQueue = require('./offlineQueue.js');
  const retryLogic = require('./retryLogic.js');
  const conflictResolver = require('./conflictResolver.js');
  const syncStatusTracker = require('./syncStatusTracker.js');
  const syncManager = require('./syncManager.js');

  module.exports = {
    ...offlineQueue,
    ...retryLogic,
    ...conflictResolver,
    ...syncStatusTracker,
    ...syncManager,
  };
}
