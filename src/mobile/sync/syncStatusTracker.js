/**
 * MPF Mobile Extension — Sync Status Tracker Module (Phase 13)
 * 
 * Tracks network availability, synchronization status, and dispatches user alerts:
 * - Real-time network state monitoring (online/offline)
 * - State machine tracking: 'idle', 'syncing', 'paused', 'error', 'offline'
 * - Event subscription pipeline for UI notifications and background daemons
 * - Non-diagnostic user alert generation when max retry thresholds are reached
 * - Preserves comprehensive audit stats: pending, syncing, synced, and failed counts
 */

export const SYNC_STATES = {
  IDLE: 'idle',
  SYNCING: 'syncing',
  PAUSED: 'paused',
  ERROR: 'error',
  OFFLINE: 'offline',
};

export const ALERT_SEVERITY = {
  INFO: 'info',
  WARNING: 'warning',
  ERROR: 'error',
};

/**
 * SyncStatusTracker manages network state and sync status observability.
 */
export class SyncStatusTracker {
  /**
   * @param {Object} [options]
   * @param {boolean} [options.initialOnline=true]
   * @param {Function} [options.onAlert] - Optional default alert handler
   */
  constructor(options = {}) {
    this.isOnline = options.initialOnline !== undefined ? options.initialOnline : true;
    this.syncState = this.isOnline ? SYNC_STATES.IDLE : SYNC_STATES.OFFLINE;
    this.lastSyncTime = null;
    this.lastError = null;
    this.listeners = new Map();
    this.alerts = [];
    this.stats = {
      pending: 0,
      syncing: 0,
      synced: 0,
      failed: 0,
      total: 0,
    };

    if (options.onAlert) {
      this.on('alert', options.onAlert);
    }

    // Auto-detect browser environment connectivity if available
    this._initBrowserListeners();
  }

  /**
   * Initializes browser network listeners if in browser window context.
   * @private
   */
  _initBrowserListeners() {
    if (typeof window !== 'undefined' && typeof window.addEventListener === 'function') {
      if (typeof navigator !== 'undefined' && typeof navigator.onLine === 'boolean') {
        this.isOnline = navigator.onLine;
        this.syncState = this.isOnline ? SYNC_STATES.IDLE : SYNC_STATES.OFFLINE;
      }
      window.addEventListener('online', () => this.setOnline(true));
      window.addEventListener('offline', () => this.setOnline(false));
    }
  }

  /**
   * Updates network connectivity state.
   * @param {boolean} online 
   */
  setOnline(online) {
    const prev = this.isOnline;
    this.isOnline = Boolean(online);

    if (this.isOnline) {
      if (this.syncState === SYNC_STATES.OFFLINE) {
        this.syncState = SYNC_STATES.IDLE;
      }
    } else {
      this.syncState = SYNC_STATES.OFFLINE;
    }

    if (prev !== this.isOnline) {
      this.emit('network_change', { isOnline: this.isOnline });
      this.emit('state_change', { state: this.syncState });
    }
  }

  /**
   * Transitions sync state.
   * @param {string} state - One of SYNC_STATES
   * @param {any} [metadata=null]
   */
  setState(state, metadata = null) {
    if (!Object.values(SYNC_STATES).includes(state)) {
      throw new Error(`Invalid sync state: ${state}`);
    }
    const prevState = this.syncState;
    this.syncState = state;

    if (state === SYNC_STATES.IDLE && prevState === SYNC_STATES.SYNCING) {
      this.lastSyncTime = new Date().toISOString();
    }

    this.emit('state_change', {
      previousState: prevState,
      state: this.syncState,
      metadata,
      timestamp: new Date().toISOString(),
    });
  }

  /**
   * Updates tracking statistics.
   * @param {Object} newStats 
   */
  updateStats(newStats) {
    this.stats = {
      ...this.stats,
      ...newStats,
    };
    this.emit('stats_update', { stats: { ...this.stats } });
  }

  /**
   * Dispatches a user alert when an item exceeds maximum retries.
   * STRICT NON-DIAGNOSTIC RESEARCH FRAMING ENFORCED.
   * 
   * @param {Object} details
   * @param {string} details.sessionId
   * @param {string} [details.eventId]
   * @param {string} [details.tableName]
   * @param {number} [details.retryCount]
   * @param {string} [details.errorMessage]
   * @returns {Object} Created alert object
   */
  createMaxRetriesExceededAlert(details) {
    const alert = {
      id: `alert_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
      type: 'MAX_RETRIES_EXCEEDED',
      severity: ALERT_SEVERITY.WARNING,
      title: 'Synchronization Paused',
      message: 'Unable to synchronize research session after 5 retry attempts. Measurements are securely preserved on your device and will sync automatically when connection improves.',
      session_id: details.sessionId,
      event_id: details.eventId || null,
      table_name: details.tableName || null,
      retry_count: details.retryCount || 5,
      error_message: details.errorMessage || 'Network timeout or unreachable server.',
      timestamp: new Date().toISOString(),
      dismissed: false,
    };

    this.alerts.push(alert);
    this.emit('alert', alert);
    return alert;
  }

  /**
   * Dispatches a generic research alert.
   * @param {Object} alertPayload 
   * @returns {Object}
   */
  createAlert(alertPayload) {
    const alert = {
      id: `alert_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
      severity: ALERT_SEVERITY.INFO,
      timestamp: new Date().toISOString(),
      dismissed: false,
      ...alertPayload,
    };

    this.alerts.push(alert);
    this.emit('alert', alert);
    return alert;
  }

  /**
   * Subscribes a listener to an event.
   * @param {string} event 
   * @param {Function} callback 
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event).add(callback);
    return () => this.off(event, callback);
  }

  /**
   * Unsubscribes a listener.
   * @param {string} event 
   * @param {Function} callback 
   */
  off(event, callback) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).delete(callback);
    }
  }

  /**
   * Emits an event to registered listeners.
   * @param {string} event 
   * @param {any} data 
   */
  emit(event, data) {
    if (this.listeners.has(event)) {
      for (const listener of this.listeners.get(event)) {
        try {
          listener(data);
        } catch (err) {
          console.error(`[SyncStatusTracker] Listener error for event ${event}:`, err);
        }
      }
    }
  }

  /**
   * Dismisses an active alert.
   * @param {string} alertId 
   */
  dismissAlert(alertId) {
    const alert = this.alerts.find((a) => a.id === alertId);
    if (alert) {
      alert.dismissed = true;
      this.emit('alert_dismissed', { alertId });
      return true;
    }
    return false;
  }

  /**
   * Retrieves active, non-dismissed alerts.
   */
  getActiveAlerts() {
    return this.alerts.filter((a) => !a.dismissed);
  }

  /**
   * Returns current snapshot of the tracker state.
   */
  getSnapshot() {
    return {
      isOnline: this.isOnline,
      syncState: this.syncState,
      lastSyncTime: this.lastSyncTime,
      stats: { ...this.stats },
      activeAlertsCount: this.getActiveAlerts().length,
    };
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    SYNC_STATES,
    ALERT_SEVERITY,
    SyncStatusTracker,
  };
}
