/**
 * MPF Mobile Extension — Tremor Feature Extractor (Phase 6)
 *
 * Extracts frequency-domain tremor biomarkers from IMU data collected during
 * the 10-second tremor hold task using Fast Fourier Transform (FFT).
 *
 * Features extracted:
 *   dominant_frequency   – peak frequency in the 3-12 Hz pathological tremor band (Hz)
 *   peak_power           – spectral power at the dominant frequency (arbitrary units)
 *   tremor_amplitude     – RMS amplitude of signal in the 3-12 Hz band
 *   band_power_ratios    – power distribution across 4 frequency bands
 *
 * Algorithm:
 *   1. Compute resultant acceleration magnitude from ax, ay, az.
 *   2. Mean-subtract to remove gravity DC offset.
 *   3. Apply Hann window to reduce spectral leakage.
 *   4. Compute FFT (Cooley-Tukey radix-2, zero-padded to next power of 2).
 *   5. Convert to one-sided power spectral density.
 *   6. Identify dominant frequency in 3–12 Hz pathological tremor band.
 *   7. Compute band power ratios across physiological sub-bands.
 *
 * IMPORTANT: This module performs SPECTRAL ANALYSIS of wrist/hand tremor.
 *            It is NOT equivalent to clinical tremor assessment hardware.
 *            Results are research-grade indicators, not clinical diagnoses.
 *
 * Privacy: Raw IMU samples are NOT returned or stored.
 */

export const TREMOR_FEATURE_VERSION = '1.0';

// Tremor band definitions (Hz)
export const TREMOR_BANDS = {
  PHYSIOLOGICAL: { min: 0.5, max: 3.0,  label: 'physiological_tremor' },  // normal
  PATHOLOGICAL:  { min: 3.0, max: 8.0,  label: 'pathological_tremor' },   // Parkinson's range
  ESSENTIAL:     { min: 4.0, max: 12.0, label: 'essential_tremor' },       // essential tremor
  HIGH:          { min: 8.0, max: 20.0, label: 'high_frequency' },         // cerebellar
};

const DOMINANT_BAND_MIN_HZ = 3.0;
const DOMINANT_BAND_MAX_HZ = 12.0;

/**
 * Extracts tremor features from raw IMU samples using FFT.
 *
 * @param {Array<{ t: number, ax: number, ay: number, az: number,
 *                 gx?: number, gy?: number, gz?: number }>} samples
 *   Raw IMU samples. ax/ay/az in m/s² or g units.
 * @param {number} durationMs - Task duration in milliseconds.
 * @param {number} sampleRateHz - Nominal sampling rate in Hz (e.g., 50).
 * @returns {Object} Extracted tremor feature set.
 */
export function extractTremorFeatures(samples, durationMs, sampleRateHz = 50) {
  if (!samples || samples.length < 10) {
    return _emptyFeatures(durationMs, 'insufficient_samples');
  }

  // --- Step 1: Compute acceleration magnitude ---
  const mag = samples.map(s => Math.sqrt(s.ax ** 2 + s.ay ** 2 + s.az ** 2));

  // --- Step 2: Mean-subtract (remove gravity DC) ---
  const mu = mag.reduce((a, b) => a + b, 0) / mag.length;
  const detrended = mag.map(v => v - mu);

  // --- Step 3: Hann window ---
  const windowed = _applyHannWindow(detrended);

  // --- Step 4: FFT ---
  const N = _nextPowerOf2(windowed.length);
  const padded = [...windowed, ...new Array(N - windowed.length).fill(0)];
  const spectrum = _fft(padded); // returns complex array

  // --- Step 5: One-sided power spectral density ---
  const freqResolution = sampleRateHz / N; // Hz per bin
  const halfN = Math.floor(N / 2);
  const psd = [];
  for (let k = 0; k <= halfN; k++) {
    const re = spectrum[k * 2];
    const im = spectrum[k * 2 + 1];
    const power = (re * re + im * im) / N;
    psd.push({
      freq: k * freqResolution,
      power: k > 0 && k < halfN ? power * 2 : power, // double for one-sided except DC/Nyquist
    });
  }

  // --- Step 6: Dominant frequency in tremor band ---
  const tremorBin = psd.filter(
    b => b.freq >= DOMINANT_BAND_MIN_HZ && b.freq <= DOMINANT_BAND_MAX_HZ
  );

  if (tremorBin.length === 0) {
    return _emptyFeatures(durationMs, 'no_tremor_band_bins');
  }

  const dominantBin = tremorBin.reduce((best, b) => b.power > best.power ? b : best, tremorBin[0]);
  const dominantFrequency = dominantBin.freq;
  const peakPower = dominantBin.power;

  // --- Tremor amplitude: RMS of signal filtered to tremor band ---
  const bandSamples = _bandpassApprox(detrended, sampleRateHz, DOMINANT_BAND_MIN_HZ, DOMINANT_BAND_MAX_HZ);
  const tremorAmplitude = _rms(bandSamples);

  // --- Step 7: Band power ratios ---
  const totalPower = psd.reduce((s, b) => s + b.power, 0);
  const bandPowerRatios = _computeBandPowerRatios(psd, totalPower);

  const durationSec = durationMs / 1000;

  return {
    dominant_frequency: _round(dominantFrequency, 3),
    peak_power: _round(peakPower, 6),
    tremor_amplitude: _round(tremorAmplitude, 6),
    band_power_ratios: bandPowerRatios,
    duration_seconds: _round(durationSec, 2),
    sample_count: samples.length,
    feature_version: TREMOR_FEATURE_VERSION,
    _extraction_status: 'ok',
    // NOTE: raw samples are NOT returned — only derived frequency-domain features
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// FFT Implementation (Cooley-Tukey Radix-2 DIT)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Iterative Cooley-Tukey FFT.
 * Input: real-valued array (length must be power of 2).
 * Output: interleaved [re0, im0, re1, im1, ...] array.
 */
function _fft(realInput) {
  const N = realInput.length;
  // Interleaved real/imag
  const data = new Float64Array(N * 2);
  for (let i = 0; i < N; i++) {
    data[i * 2] = realInput[i];
    data[i * 2 + 1] = 0;
  }

  // Bit-reversal permutation
  const bits = Math.log2(N);
  for (let i = 0; i < N; i++) {
    const rev = _bitReverse(i, bits);
    if (rev > i) {
      // Swap
      const re = data[i * 2]; const im = data[i * 2 + 1];
      data[i * 2] = data[rev * 2]; data[i * 2 + 1] = data[rev * 2 + 1];
      data[rev * 2] = re; data[rev * 2 + 1] = im;
    }
  }

  // Butterfly stages
  for (let s = 1; s <= bits; s++) {
    const m = 1 << s;
    const half = m >> 1;
    const wRe = Math.cos(-2 * Math.PI / m);
    const wIm = Math.sin(-2 * Math.PI / m);

    for (let k = 0; k < N; k += m) {
      let twRe = 1.0;
      let twIm = 0.0;

      for (let j = 0; j < half; j++) {
        const u = k + j;
        const v = u + half;

        const uRe = data[u * 2];     const uIm = data[u * 2 + 1];
        const vRe = data[v * 2];     const vIm = data[v * 2 + 1];

        const tRe = twRe * vRe - twIm * vIm;
        const tIm = twRe * vIm + twIm * vRe;

        data[u * 2]     = uRe + tRe;
        data[u * 2 + 1] = uIm + tIm;
        data[v * 2]     = uRe - tRe;
        data[v * 2 + 1] = uIm - tIm;

        const newTwRe = twRe * wRe - twIm * wIm;
        twIm = twRe * wIm + twIm * wRe;
        twRe = newTwRe;
      }
    }
  }

  return data;
}

function _bitReverse(n, bits) {
  let rev = 0;
  for (let i = 0; i < bits; i++) {
    rev = (rev << 1) | (n & 1);
    n >>= 1;
  }
  return rev;
}

function _nextPowerOf2(n) {
  let p = 1;
  while (p < n) p <<= 1;
  return p;
}

// ─────────────────────────────────────────────────────────────────────────────
// Signal processing helpers
// ─────────────────────────────────────────────────────────────────────────────

function _applyHannWindow(signal) {
  const N = signal.length;
  return signal.map((v, i) => v * 0.5 * (1 - Math.cos((2 * Math.PI * i) / (N - 1))));
}

/**
 * Approximate bandpass via frequency-domain zeroing.
 * Applies FFT, zeros bins outside [minHz, maxHz], inverse FFT.
 */
function _bandpassApprox(signal, sampleRateHz, minHz, maxHz) {
  const N = _nextPowerOf2(signal.length);
  const padded = [...signal, ...new Array(N - signal.length).fill(0)];
  const spectrum = _fft(padded);
  const freqRes = sampleRateHz / N;

  // Zero bins outside band
  for (let k = 0; k < N; k++) {
    const freq = k * freqRes;
    const mirrorFreq = (N - k) * freqRes;
    if (!((freq >= minHz && freq <= maxHz) || (mirrorFreq >= minHz && mirrorFreq <= maxHz))) {
      spectrum[k * 2] = 0;
      spectrum[k * 2 + 1] = 0;
    }
  }

  // Inverse FFT (conjugate → FFT → conjugate / N)
  for (let k = 0; k < N; k++) {
    spectrum[k * 2 + 1] = -spectrum[k * 2 + 1]; // conjugate
  }
  const invData = _fft(Array.from({ length: N }, (_, i) => spectrum[i * 2]));
  return Array.from({ length: signal.length }, (_, i) => invData[i * 2] / N);
}

function _rms(arr) {
  if (arr.length === 0) return 0;
  return Math.sqrt(arr.reduce((s, v) => s + v * v, 0) / arr.length);
}

function _computeBandPowerRatios(psd, totalPower) {
  const ratio = (minHz, maxHz) => {
    if (totalPower === 0) return 0;
    const bandPower = psd
      .filter(b => b.freq >= minHz && b.freq < maxHz)
      .reduce((s, b) => s + b.power, 0);
    return _round(bandPower / totalPower, 4);
  };

  return {
    [TREMOR_BANDS.PHYSIOLOGICAL.label]: ratio(TREMOR_BANDS.PHYSIOLOGICAL.min, TREMOR_BANDS.PHYSIOLOGICAL.max),
    [TREMOR_BANDS.PATHOLOGICAL.label]:  ratio(TREMOR_BANDS.PATHOLOGICAL.min,  TREMOR_BANDS.PATHOLOGICAL.max),
    [TREMOR_BANDS.ESSENTIAL.label]:     ratio(TREMOR_BANDS.ESSENTIAL.min,     TREMOR_BANDS.ESSENTIAL.max),
    [TREMOR_BANDS.HIGH.label]:          ratio(TREMOR_BANDS.HIGH.min,          TREMOR_BANDS.HIGH.max),
  };
}

function _round(val, dp) {
  return Math.round(val * 10 ** dp) / 10 ** dp;
}

function _emptyFeatures(durationMs, reason) {
  return {
    dominant_frequency: null,
    peak_power: null,
    tremor_amplitude: null,
    band_power_ratios: null,
    duration_seconds: durationMs / 1000,
    sample_count: 0,
    feature_version: TREMOR_FEATURE_VERSION,
    _extraction_status: reason,
  };
}
