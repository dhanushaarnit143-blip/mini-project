/**
 * MPF Mobile Extension — Retry Logic Module (Phase 13)
 * 
 * Implements exponential backoff retry strategy for Supabase synchronization:
 * - Exponential backoff progression: 1s, 2s, 4s, 8s, 16s, 32s, capped at max 60s
 * - Max retry limit: 5 attempts per record
 * - Differentiates retryable network/server faults from non-retryable client errors
 * - Dispatches alerts upon reaching max retry limit
 * - Preserves partial sync resilience: individual item failures do not halt batch sync
 */

export const RETRY_CONFIG = {
  BASE_DELAY_MS: 1000,    // 1 second base delay
  MAX_DELAY_MS: 60000,    // 60 seconds maximum cap
  MAX_RETRIES: 5,         // 5 retry attempts max
  BACKOFF_MULTIPLIER: 2,  // 2^n exponential scaling
};

/**
 * Calculates exponential backoff delay in milliseconds for a given attempt index.
 * Progression: 1s, 2s, 4s, 8s, 16s, 32s, max 60s.
 * 
 * @param {number} attempt - 0-indexed attempt count (0 is first retry)
 * @param {Object} [options]
 * @param {number} [options.baseDelayMs=1000]
 * @param {number} [options.maxDelayMs=60000]
 * @param {number} [options.jitter=0] - Jitter factor between 0.0 and 1.0 (default 0 for deterministic testing)
 * @returns {number} Delay in milliseconds
 */
export function calculateDelay(attempt, options = {}) {
  const baseDelay = options.baseDelayMs || RETRY_CONFIG.BASE_DELAY_MS;
  const maxDelay = options.maxDelayMs || RETRY_CONFIG.MAX_DELAY_MS;
  const multiplier = options.multiplier || RETRY_CONFIG.BACKOFF_MULTIPLIER;
  const jitter = options.jitter || 0;

  const expDelay = baseDelay * Math.pow(multiplier, Math.max(0, attempt));
  const cappedDelay = Math.min(expDelay, maxDelay);

  if (jitter > 0) {
    const randomJitter = (Math.random() * 2 - 1) * jitter * cappedDelay;
    return Math.max(0, Math.round(cappedDelay + randomJitter));
  }

  return cappedDelay;
}

/**
 * Evaluates whether an error is transient/retryable (network or server downtime),
 * or fatal/non-retryable (invalid schema, malformed payload, auth error).
 * 
 * @param {Error|Object|string} error 
 * @returns {boolean} True if the error warrants a retry attempt
 */
export function isRetryable(error) {
  if (!error) return false;

  const msg = (typeof error === 'string' ? error : (error.message || '')).toLowerCase();
  const status = error.status || error.statusCode || error.code;

  // Non-retryable HTTP client errors (4xx except 408 Request Timeout & 429 Rate Limit)
  if (status === 400 || status === 401 || status === 403 || status === 404 || status === 422) {
    return false;
  }
  if (msg.includes('bad request') || msg.includes('unauthorized') || msg.includes('forbidden') || msg.includes('invalid input') || msg.includes('violates foreign key')) {
    return false;
  }

  // Explicit retryable status codes: 408 (timeout), 429 (rate limit), 5xx (server error)
  if (status === 408 || status === 429 || (typeof status === 'number' && status >= 500 && status < 600)) {
    return true;
  }

  // Network drop / offline / DNS / socket error patterns
  const retryablePatterns = [
    'network',
    'failed to fetch',
    'econnrefused',
    'etimedout',
    'enotfound',
    'econnreset',
    'socket hang up',
    'timeout',
    'offline',
    'aborterror',
    'service unavailable',
    'gateway timeout',
    'rate limit',
    'server error',
  ];

  return retryablePatterns.some((pattern) => msg.includes(pattern));
}

/**
 * Sleep helper utility.
 * @param {number} ms 
 * @returns {Promise<void>}
 */
export function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Executes an asynchronous function with exponential backoff retries.
 * 
 * @param {Function} asyncFn - Async function returning a promise
 * @param {Object} [options]
 * @param {number} [options.maxRetries=5]
 * @param {number} [options.baseDelayMs=1000]
 * @param {number} [options.maxDelayMs=60000]
 * @param {Function} [options.onRetry] - Callback invoked on each retry (attempt, delayMs, error)
 * @param {Function} [options.onMaxRetriesExceeded] - Callback invoked when max retries are exceeded
 * @returns {Promise<any>} Result of asyncFn
 */
export async function executeWithRetry(asyncFn, options = {}) {
  const maxRetries = options.maxRetries !== undefined ? options.maxRetries : RETRY_CONFIG.MAX_RETRIES;
  const baseDelayMs = options.baseDelayMs || RETRY_CONFIG.BASE_DELAY_MS;
  const maxDelayMs = options.maxDelayMs || RETRY_CONFIG.MAX_DELAY_MS;
  const onRetry = options.onRetry || (() => {});
  const onMaxRetriesExceeded = options.onMaxRetriesExceeded || (() => {});

  let attempt = 0;

  while (true) {
    try {
      return await asyncFn();
    } catch (err) {
      const retryable = isRetryable(err);

      if (!retryable || attempt >= maxRetries) {
        if (attempt >= maxRetries) {
          onMaxRetriesExceeded(err, attempt);
        }
        throw err;
      }

      const delayMs = calculateDelay(attempt, { baseDelayMs, maxDelayMs });
      onRetry(attempt, delayMs, err);

      await sleep(delayMs);
      attempt += 1;
    }
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    RETRY_CONFIG,
    calculateDelay,
    isRetryable,
    sleep,
    executeWithRetry,
  };
}
