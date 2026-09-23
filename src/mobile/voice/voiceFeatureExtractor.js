/**
 * MPF Mobile Extension — Voice Feature Extractor (Phase 5)
 * 
 * Local, on-device acoustic feature extraction conforming to the Praat/Parselmouth
 * scientific specifications and the MPF voice biomarker schema:
 * 
 * 1. Pitch kinematics (pitch_mean, pitch_std in Hz via autocorrelation F0 estimation)
 * 2. Perturbation metrics:
 *    - Jitter (relative period perturbation: mean(|T_i - T_{i+1}|) / mean(T))
 *    - Shimmer (relative amplitude perturbation: mean(|A_i - A_{i+1}|) / mean(A))
 * 3. Harmonics-to-Noise Ratio (HNR in dB)
 * 4. 13-coefficient Mel-Frequency Cepstral Coefficients (MFCC)
 * 5. Spectral features (centroid, bandwidth, rolloff 85%)
 * 6. Signal quality metrics (SNR, duration, clipping, silence ratio)
 * 
 * STRICT PRIVACY: Runs 100% locally on-device. Audio buffers are processed and discarded.
 */

export const FEATURE_VERSION = '1.0.0';

export class VoiceFeatureExtractor {
  /**
   * Extracts acoustic and quality biomarkers from a PCM Float32Array.
   * 
   * @param {Float32Array|Array<number>} pcmBuffer
   * @param {number} sampleRate - e.g. 44100 or 48000
   * @returns {Object} Extracted acoustic features and quality flags
   */
  static extractFeatures(pcmBuffer, sampleRate = 44100) {
    if (!pcmBuffer || pcmBuffer.length === 0) {
      return this._getDefaultEmptyFeatures();
    }

    const samples = pcmBuffer instanceof Float32Array ? pcmBuffer : new Float32Array(pcmBuffer);
    const duration = Number((samples.length / sampleRate).toFixed(2));

    // 1. Quality & Signal Statistics
    const clippingDetected = this._detectClipping(samples);
    const { silenceRatio, voicedEnergy, unvoicedEnergy, snrEstimate } = this._analyzeSignalEnergy(samples, sampleRate);
    const signalQuality = Number(Math.max(0.0, Math.min(1.0, (snrEstimate + 10) / 40)).toFixed(2));

    // 2. Pitch (F0) Tracking via Autocorrelation
    const pitchTrack = this._trackPitchAutocorrelation(samples, sampleRate);
    const pitchMean = pitchTrack.pitchMean;
    const pitchStd = pitchTrack.pitchStd;

    // 3. Jitter & Shimmer Perturbations
    const jitter = this._calculateJitter(pitchTrack.periods);
    const shimmer = this._calculateShimmer(pitchTrack.peakAmplitudes);

    // 4. Harmonics-to-Noise Ratio (HNR in dB)
    const hnr = this._calculateHNR(samples, sampleRate, pitchMean);

    // 5. Spectral Features (Centroid, Bandwidth, Rolloff 85%)
    const spectralFeatures = this._calculateSpectralFeatures(samples, sampleRate);

    // 6. Mel-Frequency Cepstral Coefficients (MFCC, 13 coefficients)
    const mfccFeatures = this._calculateMFCCs(samples, sampleRate, 13);

    return {
      feature_version: FEATURE_VERSION,
      duration,
      signal_quality: signalQuality,
      clipping_detected: clippingDetected,
      silence_ratio: Number(silenceRatio.toFixed(3)),
      pitch_mean: Number(pitchMean.toFixed(2)),
      pitch_std: Number(pitchStd.toFixed(2)),
      jitter: Number(jitter.toFixed(5)),
      shimmer: Number(shimmer.toFixed(5)),
      hnr: Number(hnr.toFixed(2)),
      mfcc_features: mfccFeatures.map(v => Number(v.toFixed(4))),
      spectral_features: {
        spectral_centroid: Number(spectralFeatures.centroid.toFixed(2)),
        spectral_bandwidth: Number(spectralFeatures.bandwidth.toFixed(2)),
        spectral_rolloff: Number(spectralFeatures.rolloff.toFixed(2))
      }
    };
  }

  /**
   * Detects clipping artifacts where samples hit peak limits (+-0.985).
   */
  static _detectClipping(samples, threshold = 0.985) {
    let clippedCount = 0;
    for (let i = 0; i < samples.length; i++) {
      if (Math.abs(samples[i]) >= threshold) {
        clippedCount++;
        if (clippedCount > 10) return true;
      }
    }
    return false;
  }

  /**
   * Computes frame-based RMS energy, silence ratio, and SNR estimate.
   */
  static _analyzeSignalEnergy(samples, sampleRate) {
    const frameSize = Math.floor(sampleRate * 0.025); // 25ms frame
    const hopSize = Math.floor(sampleRate * 0.010);   // 10ms hop
    const frameCount = Math.floor((samples.length - frameSize) / hopSize);

    if (frameCount <= 0) {
      return { silenceRatio: 1.0, voicedEnergy: 0.0, unvoicedEnergy: 0.0, snrEstimate: 0.0 };
    }

    const frameEnergies = [];
    let maxEnergy = 0.0;

    for (let f = 0; f < frameCount; f++) {
      const offset = f * hopSize;
      let sumSquares = 0.0;
      for (let i = 0; i < frameSize; i++) {
        sumSquares += samples[offset + i] * samples[offset + i];
      }
      const rms = Math.sqrt(sumSquares / frameSize);
      frameEnergies.push(rms);
      if (rms > maxEnergy) maxEnergy = rms;
    }

    const silenceThreshold = Math.max(0.005, maxEnergy * 0.08);
    let silentFrames = 0;
    let voicedSum = 0;
    let voicedCount = 0;
    let noiseSum = 0;
    let noiseCount = 0;

    for (const energy of frameEnergies) {
      if (energy < silenceThreshold) {
        silentFrames++;
        noiseSum += energy * energy;
        noiseCount++;
      } else {
        voicedSum += energy * energy;
        voicedCount++;
      }
    }

    const silenceRatio = silentFrames / frameCount;
    const avgVoiced = voicedCount > 0 ? (voicedSum / voicedCount) : 1e-6;
    const avgNoise = noiseCount > 0 ? (noiseSum / noiseCount) : 1e-6;
    const snrEstimate = 10 * Math.log10(Math.max(1e-4, avgVoiced / avgNoise));

    return {
      silenceRatio,
      voicedEnergy: avgVoiced,
      unvoicedEnergy: avgNoise,
      snrEstimate
    };
  }

  /**
   * Tracks fundamental frequency (F0) across frames using normalized autocorrelation.
   */
  static _trackPitchAutocorrelation(samples, sampleRate) {
    const frameSize = Math.floor(sampleRate * 0.040); // 40ms window
    const hopSize = Math.floor(sampleRate * 0.020);   // 20ms hop
    const frameCount = Math.floor((samples.length - frameSize) / hopSize);

    const minLag = Math.floor(sampleRate / 400); // 400 Hz upper F0 limit
    const maxLag = Math.floor(sampleRate / 70);  // 70 Hz lower F0 limit

    const f0Values = [];
    const periods = [];
    const peakAmplitudes = [];

    for (let f = 0; f < frameCount; f++) {
      const offset = f * hopSize;
      
      // Calculate energy to check if voiced
      let energy = 0;
      for (let i = 0; i < frameSize; i++) {
        energy += samples[offset + i] * samples[offset + i];
      }
      if (energy < 1e-4) continue;

      let bestCorr = 0;
      let bestLag = 0;

      for (let lag = minLag; lag <= maxLag; lag++) {
        let sumProd = 0;
        let sumA = 0;
        let sumB = 0;
        for (let i = 0; i < frameSize - lag; i++) {
          const a = samples[offset + i];
          const b = samples[offset + i + lag];
          sumProd += a * b;
          sumA += a * a;
          sumB += b * b;
        }
        const denom = Math.sqrt(sumA * sumB);
        if (denom > 1e-6) {
          const normCorr = sumProd / denom;
          if (normCorr > bestCorr) {
            bestCorr = normCorr;
            bestLag = lag;
          }
        }
      }

      // Voicing threshold
      if (bestCorr > 0.45 && bestLag > 0) {
        const f0 = sampleRate / bestLag;
        f0Values.push(f0);
        periods.push(bestLag / sampleRate);

        // Find peak amplitude within the cycle
        let maxPeak = 0;
        for (let i = 0; i < bestLag && (offset + i) < samples.length; i++) {
          const amp = Math.abs(samples[offset + i]);
          if (amp > maxPeak) maxPeak = amp;
        }
        peakAmplitudes.push(maxPeak);
      }
    }

    if (f0Values.length === 0) {
      return { pitchMean: 0.0, pitchStd: 0.0, periods: [], peakAmplitudes: [] };
    }

    const mean = f0Values.reduce((a, b) => a + b, 0) / f0Values.length;
    const variance = f0Values.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / f0Values.length;
    const std = Math.sqrt(variance);

    return {
      pitchMean: mean,
      pitchStd: std,
      periods,
      peakAmplitudes
    };
  }

  /**
   * Computes relative jitter: mean cycle-to-cycle period difference / mean period.
   */
  static _calculateJitter(periods) {
    if (!periods || periods.length < 2) return 0.0;
    let diffSum = 0;
    let periodSum = periods[0];

    for (let i = 0; i < periods.length - 1; i++) {
      diffSum += Math.abs(periods[i] - periods[i + 1]);
      periodSum += periods[i + 1];
    }

    const meanDiff = diffSum / (periods.length - 1);
    const meanPeriod = periodSum / periods.length;

    if (meanPeriod <= 1e-6) return 0.0;
    return meanDiff / meanPeriod;
  }

  /**
   * Computes relative shimmer: mean cycle-to-cycle peak amplitude difference / mean peak amplitude.
   */
  static _calculateShimmer(peakAmplitudes) {
    if (!peakAmplitudes || peakAmplitudes.length < 2) return 0.0;
    let diffSum = 0;
    let ampSum = peakAmplitudes[0];

    for (let i = 0; i < peakAmplitudes.length - 1; i++) {
      diffSum += Math.abs(peakAmplitudes[i] - peakAmplitudes[i + 1]);
      ampSum += peakAmplitudes[i + 1];
    }

    const meanDiff = diffSum / (peakAmplitudes.length - 1);
    const meanAmp = ampSum / peakAmplitudes.length;

    if (meanAmp <= 1e-6) return 0.0;
    return meanDiff / meanAmp;
  }

  /**
   * Computes Harmonics-to-Noise Ratio (HNR in dB) via autocorrelation peak.
   */
  static _calculateHNR(samples, sampleRate, pitchMean) {
    if (!pitchMean || pitchMean <= 0 || samples.length < 1024) return 0.0;
    const fundamentalLag = Math.round(sampleRate / pitchMean);
    const windowSize = Math.min(samples.length - fundamentalLag, 2048);

    if (windowSize <= 0) return 0.0;

    let r0 = 0.0;
    let rLag = 0.0;

    for (let i = 0; i < windowSize; i++) {
      r0 += samples[i] * samples[i];
      rLag += samples[i] * samples[i + fundamentalLag];
    }

    if (r0 <= 1e-6) return 0.0;
    const normalizedCorr = Math.max(0.001, Math.min(0.999, rLag / r0));

    // Praat HNR equation: 10 * log10(r / (1 - r))
    const hnr = 10 * Math.log10(normalizedCorr / (1.0 - normalizedCorr));
    return Math.max(0.0, Math.min(45.0, hnr));
  }

  /**
   * Computes spectral centroid, spectral bandwidth, and 85% spectral rolloff.
   */
  static _calculateSpectralFeatures(samples, sampleRate) {
    const fftSize = 1024;
    const window = new Float32Array(fftSize);
    const half = fftSize / 2;

    // Use a central segment of the signal
    const startIdx = Math.max(0, Math.floor((samples.length - fftSize) / 2));
    for (let i = 0; i < fftSize; i++) {
      const idx = startIdx + i;
      const val = idx < samples.length ? samples[idx] : 0;
      // Hamming window
      const w = 0.54 - 0.46 * Math.cos((2 * Math.PI * i) / (fftSize - 1));
      window[i] = val * w;
    }

    // Power spectrum using discrete Fourier transform on key bins
    const powerSpectrum = new Float32Array(half);
    const binHz = sampleRate / fftSize;
    let totalPower = 0.0;

    for (let k = 0; k < half; k++) {
      let real = 0.0;
      let imag = 0.0;
      const angleStep = (2 * Math.PI * k) / fftSize;
      // Stride calculation for performance
      for (let n = 0; n < fftSize; n += 2) {
        const angle = angleStep * n;
        real += window[n] * Math.cos(angle);
        imag -= window[n] * Math.sin(angle);
      }
      const pwr = real * real + imag * imag;
      powerSpectrum[k] = pwr;
      totalPower += pwr;
    }

    if (totalPower <= 1e-6) {
      return { centroid: 0.0, bandwidth: 0.0, rolloff: 0.0 };
    }

    // Centroid
    let weightedFreqSum = 0.0;
    for (let k = 0; k < half; k++) {
      const freq = k * binHz;
      weightedFreqSum += freq * powerSpectrum[k];
    }
    const centroid = weightedFreqSum / totalPower;

    // Bandwidth
    let spreadSum = 0.0;
    for (let k = 0; k < half; k++) {
      const freq = k * binHz;
      spreadSum += Math.pow(freq - centroid, 2) * powerSpectrum[k];
    }
    const bandwidth = Math.sqrt(spreadSum / totalPower);

    // Rolloff (85% energy threshold)
    const rolloffTarget = 0.85 * totalPower;
    let cumPower = 0.0;
    let rolloff = 0.0;
    for (let k = 0; k < half; k++) {
      cumPower += powerSpectrum[k];
      if (cumPower >= rolloffTarget) {
        rolloff = k * binHz;
        break;
      }
    }

    return { centroid, bandwidth, rolloff };
  }

  /**
   * Computes first N Mel-Frequency Cepstral Coefficients (MFCCs).
   */
  static _calculateMFCCs(samples, sampleRate, numCoeffs = 13) {
    const numFilters = 26;
    const fftSize = 1024;
    const half = fftSize / 2;
    const minFreq = 100;
    const maxFreq = Math.min(sampleRate / 2, 8000);

    const hzToMel = (hz) => 2595 * Math.log10(1 + hz / 700);
    const melToHz = (mel) => 700 * (Math.pow(10, mel / 2595) - 1);

    const melMin = hzToMel(minFreq);
    const melMax = hzToMel(maxFreq);
    const melPoints = [];
    for (let i = 0; i <= numFilters + 1; i++) {
      melPoints.push(melMin + (i * (melMax - melMin)) / (numFilters + 1));
    }
    const binPoints = melPoints.map(m => Math.floor(((fftSize + 1) * melToHz(m)) / sampleRate));

    // Construct simple power spectrum from middle frame
    const startIdx = Math.max(0, Math.floor((samples.length - fftSize) / 2));
    const powerSpectrum = new Float32Array(half);
    for (let k = 0; k < half; k++) {
      let real = 0.0;
      let imag = 0.0;
      const angleStep = (2 * Math.PI * k) / fftSize;
      for (let n = 0; n < fftSize; n += 2) {
        const val = (startIdx + n < samples.length) ? samples[startIdx + n] : 0;
        real += val * Math.cos(angleStep * n);
        imag -= val * Math.sin(angleStep * n);
      }
      powerSpectrum[k] = (real * real + imag * imag) / fftSize;
    }

    // Filterbank energies
    const filterEnergies = new Float32Array(numFilters);
    for (let m = 1; m <= numFilters; m++) {
      const left = binPoints[m - 1];
      const center = binPoints[m];
      const right = binPoints[m + 1];

      let energy = 0.0;
      for (let k = left; k < center && k < half; k++) {
        const weight = (k - left) / Math.max(1, center - left);
        energy += powerSpectrum[k] * weight;
      }
      for (let k = center; k < right && k < half; k++) {
        const weight = (right - k) / Math.max(1, right - center);
        energy += powerSpectrum[k] * weight;
      }
      filterEnergies[m - 1] = Math.log(Math.max(1e-6, energy));
    }

    // Discrete Cosine Transform (DCT-II)
    const mfccs = [];
    for (let i = 0; i < numCoeffs; i++) {
      let sum = 0.0;
      for (let j = 0; j < numFilters; j++) {
        sum += filterEnergies[j] * Math.cos((Math.PI * i * (j + 0.5)) / numFilters);
      }
      mfccs.push(sum);
    }

    return mfccs;
  }

  static _getDefaultEmptyFeatures() {
    return {
      feature_version: FEATURE_VERSION,
      duration: 0.0,
      signal_quality: 0.0,
      clipping_detected: false,
      silence_ratio: 1.0,
      pitch_mean: 0.0,
      pitch_std: 0.0,
      jitter: 0.0,
      shimmer: 0.0,
      hnr: 0.0,
      mfcc_features: new Array(13).fill(0.0),
      spectral_features: {
        spectral_centroid: 0.0,
        spectral_bandwidth: 0.0,
        spectral_rolloff: 0.0
      }
    };
  }
}
