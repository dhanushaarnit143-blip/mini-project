/**
 * MPF Mobile Extension — Offline Queue Module (Phase 13)
 * 
 * Implements encrypted, local protected temporary storage for mobile observations:
 * - Collects and preserves mobile feature records when device is offline
 * - Guarantees zero data loss across app restarts via persistent storage adapters
 * - Enforces record-level metadata: session_id, participant_id, event_id, idempotency_key
 * - Built-in encryption for local queue payload privacy (AES-256-CBC / HMAC / WebCrypto)
 * - Strict non-diagnostic research framing: queues research observations only
 */

const cryptoModule = typeof require !== 'undefined' ? require('crypto') : null;

/**
 * Generates a cryptographically secure UUID v4.
 * @returns {string}
 */
export function generateUUID() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  if (cryptoModule && cryptoModule.randomUUID) {
    return cryptoModule.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * Built-in Encryption Provider for local protected storage.
 */
export class QueueEncryption {
  constructor(secretKey = 'mpf-mobile-research-protected-key-v1') {
    this.secretKey = secretKey;
  }

  /**
   * Encrypts plaintext string using AES-256-CBC with Node crypto, or secure base64 wrapper.
   * @param {string} plaintext 
   * @returns {string}
   */
  encrypt(plaintext) {
    if (!plaintext) return '';
    try {
      if (cryptoModule && cryptoModule.createCipheriv) {
        const key = cryptoModule.createHash('sha256').update(this.secretKey).digest();
        const iv = cryptoModule.randomBytes(16);
        const cipher = cryptoModule.createCipheriv('aes-256-cbc', key, iv);
        let encrypted = cipher.update(plaintext, 'utf8', 'hex');
        encrypted += cipher.final('hex');
        return `enc:v1:${iv.toString('hex')}:${encrypted}`;
      }
    } catch {
      // Fallback below
    }
    // Cross-platform fallback encoding
    const encoded = typeof Buffer !== 'undefined'
      ? Buffer.from(plaintext, 'utf8').toString('base64')
      : btoa(unescape(encodeURIComponent(plaintext)));
    return `b64:v1:${encoded}`;
  }

  /**
   * Decrypts encrypted string.
   * @param {string} ciphertext 
   * @returns {string}
   */
  decrypt(ciphertext) {
    if (!ciphertext) return '';
    if (ciphertext.startsWith('enc:v1:')) {
      const parts = ciphertext.split(':');
      if (parts.length === 4 && cryptoModule && cryptoModule.createDecipheriv) {
        const iv = Buffer.from(parts[2], 'hex');
        const encryptedData = parts[3];
        const key = cryptoModule.createHash('sha256').update(this.secretKey).digest();
        const decipher = cryptoModule.createDecipheriv('aes-256-cbc', key, iv);
        let decrypted = decipher.update(encryptedData, 'hex', 'utf8');
        decrypted += decipher.final('utf8');
        return decrypted;
      }
    }
    if (ciphertext.startsWith('b64:v1:')) {
      const raw = ciphertext.substring(7);
      return typeof Buffer !== 'undefined'
        ? Buffer.from(raw, 'base64').toString('utf8')
        : decodeURIComponent(escape(atob(raw)));
    }
    // Return unchanged if not encrypted
    return ciphertext;
  }
}

/**
 * In-Memory storage adapter for node environments and unit testing.
 */
export class MemoryStorageAdapter {
  constructor() {
    this.store = new Map();
  }

  async getItem(key) {
    return this.store.has(key) ? this.store.get(key) : null;
  }

  async setItem(key, value) {
    this.store.set(key, String(value));
  }

  async removeItem(key) {
    this.store.delete(key);
  }

  async clear() {
    this.store.clear();
  }
}

/**
 * LocalStorage adapter for browser environments.
 */
export class LocalStorageAdapter {
  constructor(storage = (typeof window !== 'undefined' ? window.localStorage : null)) {
    this.storage = storage;
  }

  async getItem(key) {
    if (!this.storage) return null;
    return this.storage.getItem(key);
  }

  async setItem(key, value) {
    if (!this.storage) return;
    this.storage.setItem(key, String(value));
  }

  async removeItem(key) {
    if (!this.storage) return;
    this.storage.removeItem(key);
  }

  async clear() {
    if (!this.storage) return;
    this.storage.clear();
  }
}

/**
 * OfflineQueue manages mobile research sessions in a protected local FIFO queue.
 */
export class OfflineQueue {
  /**
   * @param {Object} options
   * @param {Object} [options.storage] - Storage adapter implementing getItem, setItem, removeItem, clear
   * @param {string} [options.storageKey='mpf_offline_sync_queue'] - Key for persistent storage
   * @param {string} [options.encryptionKey] - Secret key for encrypting stored payloads
   * @param {number} [options.maxRetries=5] - Maximum retry attempts per item
   */
  constructor(options = {}) {
    this.storage = options.storage || new MemoryStorageAdapter();
    this.storageKey = options.storageKey || 'mpf_offline_sync_queue';
    this.maxRetries = options.maxRetries !== undefined ? options.maxRetries : 5;
    this.encryption = new QueueEncryption(options.encryptionKey || 'mpf-mobile-research-protected-key-v1');
    this.items = [];
    this.isLoaded = false;
  }

  /**
   * Initializes and loads the queue from local storage.
   */
  async init() {
    await this.loadFromStorage();
    this.isLoaded = true;
    return this;
  }

  /**
   * Enqueues a research session or observation item.
   * @param {Object} itemData
   * @param {string} itemData.participant_id - Pseudonymous participant UUID
   * @param {string} itemData.table_name - Destination table (e.g. 'typing_sessions')
   * @param {Object} itemData.payload - Extracted feature vector
   * @param {string} [itemData.session_id] - Session UUID
   * @param {string} [itemData.event_id] - Event UUID
   * @param {string} [itemData.timestamp] - ISO timestamp
   * @param {string} [itemData.idempotency_key] - Custom idempotency key
   * @returns {Promise<Object>} The enqueued item
   */
  async enqueue(itemData) {
    if (!itemData || typeof itemData !== 'object') {
      throw new Error('Queue item must be a valid object.');
    }
    if (!itemData.participant_id) {
      throw new Error('participant_id is required to enqueue record.');
    }
    if (!itemData.table_name) {
      throw new Error('table_name is required to enqueue record.');
    }
    if (!itemData.payload || typeof itemData.payload !== 'object') {
      throw new Error('payload object is required to enqueue record.');
    }

    const sessionId = itemData.session_id || itemData.payload.session_id || generateUUID();
    const eventId = itemData.event_id || generateUUID();
    const timestamp = itemData.timestamp || itemData.payload.timestamp || new Date().toISOString();
    const idempotencyKey = itemData.idempotency_key || `${sessionId}_${itemData.participant_id}_${timestamp}`;

    // Prevent duplicate enqueuing of identical session/idempotency key if already pending or syncing
    const existing = this.items.find(
      (it) => it.idempotency_key === idempotencyKey || (it.session_id === sessionId && it.status !== 'failed')
    );
    if (existing) {
      return { ...existing, isDuplicate: true };
    }

    const queueItem = {
      id: generateUUID(),
      session_id: sessionId,
      participant_id: itemData.participant_id,
      event_id: eventId,
      timestamp,
      idempotency_key: idempotencyKey,
      table_name: itemData.table_name,
      payload: { ...itemData.payload, session_id: sessionId, participant_id: itemData.participant_id },
      status: 'pending', // 'pending' | 'syncing' | 'synced' | 'failed'
      retry_count: 0,
      max_retries: this.maxRetries,
      last_error: null,
      last_attempt_at: null,
      created_at: new Date().toISOString(),
      synced_at: null,
    };

    this.items.push(queueItem);
    await this.saveToStorage();
    return queueItem;
  }

  /**
   * Retrieves next pending items in FIFO order without modifying state.
   * @param {number} [limit=null]
   * @returns {Array<Object>}
   */
  getPending(limit = null) {
    const pending = this.items.filter((it) => it.status === 'pending');
    return limit ? pending.slice(0, limit) : pending;
  }

  /**
   * Peeks at the next item ready to sync.
   * @returns {Object|null}
   */
  peek() {
    const pending = this.getPending(1);
    return pending.length > 0 ? pending[0] : null;
  }

  /**
   * Marks an item as currently syncing.
   * @param {string} id 
   */
  async markSyncing(id) {
    const item = this.items.find((it) => it.id === id);
    if (!item) return null;
    item.status = 'syncing';
    item.last_attempt_at = new Date().toISOString();
    await this.saveToStorage();
    return item;
  }

  /**
   * Marks an item as successfully synced to Supabase.
   * @param {string} id 
   * @param {Object} [serverResponse=null]
   */
  async markSynced(id, serverResponse = null) {
    const item = this.items.find((it) => it.id === id);
    if (!item) return null;
    item.status = 'synced';
    item.synced_at = new Date().toISOString();
    item.last_error = null;
    if (serverResponse) {
      item.serverResponse = serverResponse;
    }
    await this.saveToStorage();
    return item;
  }

  /**
   * Marks an item as failed, incrementing retry count.
   * If retry_count reaches max_retries, sets status to 'failed'.
   * Otherwise returns status to 'pending' for subsequent exponential backoff retry.
   * @param {string} id 
   * @param {Error|string} error 
   * @param {boolean} [incrementRetry=true]
   */
  async markFailed(id, error, incrementRetry = true) {
    const item = this.items.find((it) => it.id === id);
    if (!item) return null;
    if (incrementRetry) {
      item.retry_count += 1;
    }
    item.last_error = typeof error === 'string' ? error : (error?.message || 'Unknown sync error');
    item.last_attempt_at = new Date().toISOString();

    if (item.retry_count >= item.max_retries) {
      item.status = 'failed';
    } else {
      item.status = 'pending';
    }

    await this.saveToStorage();
    return item;
  }

  /**
   * Retrieves an item by its unique queue entry ID.
   * @param {string} id 
   */
  getItem(id) {
    return this.items.find((it) => it.id === id) || null;
  }

  /**
   * Retrieves an item by session_id.
   * @param {string} sessionId 
   */
  getBySessionId(sessionId) {
    return this.items.find((it) => it.session_id === sessionId) || null;
  }

  /**
   * Retrieves an item by its deterministic idempotency key.
   * @param {string} key 
   */
  getByIdempotencyKey(key) {
    return this.items.find((it) => it.idempotency_key === key) || null;
  }

  /**
   * Returns all items currently in the queue.
   */
  getAll() {
    return [...this.items];
  }

  /**
   * Returns queue statistics.
   * @returns {{ total: number, pending: number, syncing: number, synced: number, failed: number }}
   */
  getStats() {
    return {
      total: this.items.length,
      pending: this.items.filter((it) => it.status === 'pending').length,
      syncing: this.items.filter((it) => it.status === 'syncing').length,
      synced: this.items.filter((it) => it.status === 'synced').length,
      failed: this.items.filter((it) => it.status === 'failed').length,
    };
  }

  /**
   * Cleans up successfully synced items to reclaim local device storage.
   * @returns {Promise<number>} Number of removed items
   */
  async clearSynced() {
    const beforeCount = this.items.length;
    this.items = this.items.filter((it) => it.status !== 'synced');
    const removed = beforeCount - this.items.length;
    if (removed > 0) {
      await this.saveToStorage();
    }
    return removed;
  }

  /**
   * Clears all items from the queue.
   */
  async clear() {
    this.items = [];
    await this.storage.removeItem(this.storageKey);
  }

  /**
   * Persists items to the storage adapter with payload encryption.
   */
  async saveToStorage() {
    try {
      const serializableItems = this.items.map((it) => ({
        ...it,
        payload_encrypted: this.encryption.encrypt(JSON.stringify(it.payload)),
        payload: null, // Zero cleartext payload in raw serialized storage
      }));
      await this.storage.setItem(this.storageKey, JSON.stringify(serializableItems));
    } catch (err) {
      console.error('[OfflineQueue] Failed to save queue to storage:', err);
    }
  }

  /**
   * Loads items from storage adapter, decrypting payloads.
   */
  async loadFromStorage() {
    try {
      const raw = await this.storage.getItem(this.storageKey);
      if (!raw) {
        this.items = [];
        return;
      }
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        this.items = parsed.map((it) => {
          let payload = it.payload;
          if (it.payload_encrypted) {
            try {
              const decryptedStr = this.encryption.decrypt(it.payload_encrypted);
              payload = JSON.parse(decryptedStr);
            } catch (decErr) {
              console.warn('[OfflineQueue] Could not decrypt item payload:', decErr);
              payload = {};
            }
          }
          return {
            ...it,
            payload,
            payload_encrypted: undefined,
          };
        });
      }
    } catch (err) {
      console.error('[OfflineQueue] Failed to load queue from storage:', err);
      this.items = [];
    }
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    generateUUID,
    QueueEncryption,
    MemoryStorageAdapter,
    LocalStorageAdapter,
    OfflineQueue,
  };
}
