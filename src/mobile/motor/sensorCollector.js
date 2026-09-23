/**
 * MPF Mobile Extension — Sensor Collector (Phase 6)
 *
 * Manages short-duration, consent-gated accelerometer + gyroscope collection
 * using the Web DeviceMotion/DeviceOrientation APIs (mobile browser / React Native bridge).
 *
 * PRIVACY RULES ENFORCED:
 * - Sensors are ONLY active during an explicit guided task window.
 * - NO background sensor collection.
 * - Raw sensor streams are NEVER persisted or uploaded.
 * - Only derived features leave this module.
 * - Collection stops automatically when the task window closes.
 */

export const SENSOR_SAMPLE_RATE_HZ = 50; // 50 Hz — sufficient for gait/tremor, preserves battery
export const MAX_TASK_DURATION_MS = 35_000; // hard cap: 35 seconds per task

/**
 * Raw IMU sample structure (internal only — never exported to storage).
 * @typedef {{ t: number, ax: number, ay: number, az: number,
 *             gx: number, gy: number, gz: number }} ImuSample
 */

/**
 * Lightweight ring-buffer that holds raw IMU samples during a single task window.
 * Automatically discards samples after feature extraction is complete.
 */
export class ImuBuffer {
  constructor(maxSamples = 5000) {
    this._maxSamples = maxSamples;
    this._samples = [];
  }

  push(sample) {
    if (this._samples.length >= this._maxSamples) {
      this._samples.shift(); // drop oldest if buffer full
    }
    this._samples.push(sample);
  }

  /** Returns a frozen snapshot copy for feature extraction, then flushes. */
  flushAndGet() {
    const snapshot = Object.freeze([...this._samples]);
    this._samples = [];
    return snapshot;
  }

  get length() {
    return this._samples.length;
  }

  clear() {
    this._samples = [];
  }
}

/**
 * SensorCollector — wraps DeviceMotionEvent for in-task IMU capture.
 *
 * Usage:
 *   const collector = new SensorCollector();
 *   await collector.requestPermission();     // iOS 13+ requires explicit permission
 *   collector.startTask('walking');
 *   // ... 30 seconds pass / user stops task ...
 *   const { samples, durationMs } = collector.stopTask();
 *   // Pass samples to feature extractor. Raw samples are discarded after extraction.
 */
export class SensorCollector {
  constructor() {
    this._isCollecting = false;
    this._taskType = null;
    this._startTime = null;
    this._imuBuffer = new ImuBuffer();
    this._motionHandler = null;
    this._hardStopTimer = null;
    this._onSampleCallback = null;
  }

  /**
   * Requests DeviceMotion permission on iOS 13+.
   * On Android / non-iOS browsers this resolves immediately.
   * @returns {Promise<{ granted: boolean, reason?: string }>}
   */
  async requestPermission() {
    if (
      typeof DeviceMotionEvent !== 'undefined' &&
      typeof DeviceMotionEvent.requestPermission === 'function'
    ) {
      try {
        const response = await DeviceMotionEvent.requestPermission();
        if (response === 'granted') {
          return { granted: true };
        }
        return { granted: false, reason: 'User denied DeviceMotion permission' };
      } catch (err) {
        return { granted: false, reason: err.message };
      }
    }
    // Android and most non-iOS environments — permission not required
    return { granted: true };
  }

  /**
   * Checks if DeviceMotionEvent is available in this environment.
   * @returns {boolean}
   */
  isAvailable() {
    return typeof window !== 'undefined' && typeof DeviceMotionEvent !== 'undefined';
  }

  /**
   * Starts a sensor collection window for the given task type.
   * An automatic hard-stop fires after MAX_TASK_DURATION_MS to prevent runaway collection.
   *
   * @param {'walking'|'tremor_hold'} taskType
   * @param {Function} [onSample] - Optional callback called with each ImuSample (for live UI meters)
   */
  startTask(taskType, onSample = null) {
    if (this._isCollecting) {
      throw new Error('SensorCollector: already collecting — call stopTask() first.');
    }

    this._taskType = taskType;
    this._startTime = performance.now();
    this._isCollecting = true;
    this._onSampleCallback = onSample;
    this._imuBuffer.clear();

    this._motionHandler = (event) => {
      if (!this._isCollecting) return;

      const acc = event.accelerationIncludingGravity || {};
      const rot = event.rotationRate || {};

      const sample = {
        t: performance.now() - this._startTime, // ms since task start
        ax: acc.x ?? 0,
        ay: acc.y ?? 0,
        az: acc.z ?? 0,
        gx: rot.alpha ?? 0,
        gy: rot.beta ?? 0,
        gz: rot.gamma ?? 0,
      };

      this._imuBuffer.push(sample);
      if (this._onSampleCallback) {
        this._onSampleCallback(sample);
      }
    };

    window.addEventListener('devicemotion', this._motionHandler, { passive: true });

    // Hard stop to prevent runaway collection
    this._hardStopTimer = setTimeout(() => {
      if (this._isCollecting) {
        console.warn(`SensorCollector: hard-stop fired after ${MAX_TASK_DURATION_MS}ms for task="${this._taskType}"`);
        this.stopTask();
      }
    }, MAX_TASK_DURATION_MS);
  }

  /**
   * Stops collection and returns the raw sample buffer + task metadata.
   * The caller is responsible for extracting features immediately and discarding the raw samples.
   *
   * @returns {{ samples: ImuSample[], taskType: string, durationMs: number, sampleCount: number }}
   */
  stopTask() {
    if (!this._isCollecting) {
      return { samples: [], taskType: this._taskType, durationMs: 0, sampleCount: 0 };
    }

    // Stop event listener first
    if (this._motionHandler) {
      window.removeEventListener('devicemotion', this._motionHandler);
      this._motionHandler = null;
    }

    if (this._hardStopTimer) {
      clearTimeout(this._hardStopTimer);
      this._hardStopTimer = null;
    }

    const durationMs = performance.now() - this._startTime;
    this._isCollecting = false;

    // Flush and return — caller must discard samples after feature extraction
    const samples = this._imuBuffer.flushAndGet();

    return {
      samples,
      taskType: this._taskType,
      durationMs,
      sampleCount: samples.length,
    };
  }

  get isCollecting() {
    return this._isCollecting;
  }

  /** Emergency release: stops collection and discards all samples. */
  dispose() {
    if (this._isCollecting) {
      this.stopTask();
    }
    this._imuBuffer.clear();
  }
}
