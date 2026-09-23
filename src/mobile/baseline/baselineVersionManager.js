/**
 * MPF Mobile Extension — Baseline Version Manager (Phase 10)
 *
 * Enforces versioned reproducibility and provenance for personal baselines:
 * - baseline_version: Incremented on each accepted adaptive update
 * - baseline_created_at: Preserved timestamp when baseline was first established (Day 14)
 * - baseline_updated_at: Timestamp when baseline was last updated
 * - algorithm_version: Version of the baseline calculation algorithm ('1.0.0')
 * - sample_count: Cumulative number of observations incorporated into baseline
 *
 * NON-NEGOTIABLE COMPLIANCE:
 * - VERSIONED REPRODUCIBILITY: Every baseline state is uniquely versioned and traceable.
 */

export const DEFAULT_ALGORITHM_VERSION = '1.0.0';
export const INITIAL_BASELINE_VERSION = '1.0.0';

/**
 * Parses semantic version string 'major.minor.patch'.
 * @param {string} versionStr
 * @returns {{major: number, minor: number, patch: number}}
 */
export function parseSemanticVersion(versionStr) {
  if (typeof versionStr !== 'string') {
    return { major: 1, minor: 0, patch: 0 };
  }
  const parts = versionStr.split('.').map(p => parseInt(p, 10));
  return {
    major: Number.isInteger(parts[0]) ? parts[0] : 1,
    minor: Number.isInteger(parts[1]) ? parts[1] : 0,
    patch: Number.isInteger(parts[2]) ? parts[2] : 0,
  };
}

/**
 * Increments semantic version string by patch number.
 * e.g. '1.0.0' -> '1.0.1', '1.0.9' -> '1.0.10'
 * @param {string} currentVersion
 * @returns {string}
 */
export function incrementVersion(currentVersion) {
  const { major, minor, patch } = parseSemanticVersion(currentVersion);
  return `${major}.${minor}.${patch + 1}`;
}

/**
 * Creates initial baseline version metadata when baseline is first established (Day 14).
 *
 * @param {Object} [options]
 * @param {string} [options.algorithmVersion]
 * @param {number} [options.sampleCount=14]
 * @param {string|Date} [options.createdAt]
 * @returns {Object}
 */
export function createInitialBaselineVersion(options = {}) {
  const nowIso = options.createdAt
    ? (typeof options.createdAt === 'string' ? options.createdAt : options.createdAt.toISOString())
    : new Date().toISOString();

  return {
    baseline_version: INITIAL_BASELINE_VERSION,
    algorithm_version: options.algorithmVersion ?? DEFAULT_ALGORITHM_VERSION,
    baseline_created_at: nowIso,
    baseline_updated_at: nowIso,
    sample_count: options.sampleCount ?? 14,
  };
}

/**
 * Updates version metadata upon incorporating an adaptive observation (Day 15+).
 * Preserves the original `baseline_created_at` timestamp.
 *
 * @param {Object} currentMeta Existing version metadata
 * @param {Object} [options]
 * @param {string|Date} [options.updatedAt]
 * @param {number} [options.incrementSamples=1]
 * @returns {Object}
 */
export function updateBaselineVersion(currentMeta, options = {}) {
  const currentVer = currentMeta?.baseline_version ?? INITIAL_BASELINE_VERSION;
  const newVer = incrementVersion(currentVer);
  const nowIso = options.updatedAt
    ? (typeof options.updatedAt === 'string' ? options.updatedAt : options.updatedAt.toISOString())
    : new Date().toISOString();

  const originalCreatedAt = currentMeta?.baseline_created_at ?? nowIso;
  const currentCount = currentMeta?.sample_count ?? 14;
  const newCount = currentCount + (options.incrementSamples ?? 1);

  return {
    baseline_version: newVer,
    algorithm_version: currentMeta?.algorithm_version ?? DEFAULT_ALGORITHM_VERSION,
    baseline_created_at: originalCreatedAt,
    baseline_updated_at: nowIso,
    sample_count: newCount,
  };
}

/**
 * Validates baseline version metadata for consistency and completeness.
 * @param {Object} meta
 * @returns {{isValid: boolean, errors: Array<string>}}
 */
export function validateBaselineVersionMetadata(meta) {
  const errors = [];
  if (!meta || typeof meta !== 'object') {
    return { isValid: false, errors: ['Version metadata must be a non-null object'] };
  }

  if (typeof meta.baseline_version !== 'string' || !/^\d+\.\d+\.\d+$/.test(meta.baseline_version)) {
    errors.push(`Invalid baseline_version format: ${meta.baseline_version}`);
  }

  if (typeof meta.algorithm_version !== 'string') {
    errors.push('Missing or invalid algorithm_version');
  }

  if (!meta.baseline_created_at || Number.isNaN(Date.parse(meta.baseline_created_at))) {
    errors.push('Missing or invalid baseline_created_at timestamp');
  }

  if (!meta.baseline_updated_at || Number.isNaN(Date.parse(meta.baseline_updated_at))) {
    errors.push('Missing or invalid baseline_updated_at timestamp');
  }

  if (typeof meta.sample_count !== 'number' || meta.sample_count < 1) {
    errors.push(`sample_count must be an integer >= 1, got ${meta.sample_count}`);
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

// Dual CommonJS / ES Module export
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    DEFAULT_ALGORITHM_VERSION,
    INITIAL_BASELINE_VERSION,
    parseSemanticVersion,
    incrementVersion,
    createInitialBaselineVersion,
    updateBaselineVersion,
    validateBaselineVersionMetadata,
  };
}
