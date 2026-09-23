import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Waves,
  Play,
  Square,
  CheckCircle2,
  AlertTriangle,
  UploadCloud,
  ShieldCheck,
  Timer,
  BarChart2,
  RefreshCw,
  Info,
} from 'lucide-react';
import { SensorCollector } from './sensorCollector.js';
import { extractTremorFeatures } from './tremorFeatureExtractor.js';
import { MotorQualityScorer } from './motorQualityScorer.js';
import { MotorSessionModel, MOTOR_TASK_TYPES } from './motorSessionModel.js';

/**
 * MPF Mobile Extension — Tremor Hold Task Screen (Phase 6)
 *
 * Optional 10-second tremor hold: participant holds phone still.
 * Collects IMU data, applies FFT to extract frequency-domain tremor features.
 *
 * Features extracted:
 *   dominant_frequency, peak_power, tremor_amplitude, band_power_ratios
 *
 * COMPLIANCE:
 * - "Research screening result — not a clinical diagnosis."
 * - "Deviation from personal baseline" language ONLY.
 * - NO background sensor collection.
 * - Raw sensor streams discarded after FFT extraction.
 * - NOT equivalent to clinical tremor assessment equipment.
 */

const TASK_DURATION_SEC = 10;
const SENSOR_SAMPLE_RATE_HZ = 50;

const PHASE = {
  READY:      'ready',
  HOLDING:    'holding',
  PROCESSING: 'processing',
  RESULTS:    'results',
};

export function TremorTaskScreen({ participantId, supabaseClient, onComplete, onCancel }) {
  const [phase, setPhase]                 = useState(PHASE.READY);
  const [elapsed, setElapsed]             = useState(0);
  const [liveAmplitude, setLiveAmplitude] = useState(0);
  const [features, setFeatures]           = useState(null);
  const [qualityResult, setQualityResult] = useState(null);
  const [sessionModel, setSessionModel]   = useState(null);
  const [isSyncing, setIsSyncing]         = useState(false);
  const [syncStatus, setSyncStatus]       = useState(null);
  const [sensorAvailable, setSensorAvailable] = useState(true);
  const [permissionError, setPermissionError] = useState(null);

  const collectorRef = useRef(null);
  const timerRef     = useRef(null);
  const startMsRef   = useRef(null);

  useEffect(() => {
    collectorRef.current = new SensorCollector();
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (collectorRef.current) collectorRef.current.dispose();
    };
  }, []);

  const handleStart = useCallback(async () => {
    const collector = collectorRef.current;

    if (!collector.isAvailable()) {
      setSensorAvailable(false);
      setPermissionError('Accelerometer not available on this device or browser.');
      return;
    }

    const perm = await collector.requestPermission();
    if (!perm.granted) {
      setPermissionError(perm.reason || 'Sensor permission denied.');
      return;
    }

    setPhase(PHASE.HOLDING);
    setElapsed(0);
    setLiveAmplitude(0);
    startMsRef.current = performance.now();

    // Live amplitude for visual feedback (magnitude of acceleration)
    collector.startTask(MOTOR_TASK_TYPES.TREMOR_HOLD, (sample) => {
      const mag = Math.sqrt(sample.ax ** 2 + sample.ay ** 2 + sample.az ** 2);
      setLiveAmplitude(parseFloat(mag.toFixed(3)));
    });

    timerRef.current = setInterval(() => {
      const sec = (performance.now() - startMsRef.current) / 1000;
      setElapsed(Math.min(sec, TASK_DURATION_SEC));
      if (sec >= TASK_DURATION_SEC) {
        clearInterval(timerRef.current);
        finishTask();
      }
    }, 200);
  }, []);

  const finishTask = useCallback(() => {
    clearInterval(timerRef.current);
    const collector = collectorRef.current;
    const { samples, durationMs, sampleCount } = collector.stopTask();

    setPhase(PHASE.PROCESSING);

    // FFT-based tremor extraction — raw samples discarded after
    const extracted = extractTremorFeatures(samples, durationMs, SENSOR_SAMPLE_RATE_HZ);

    const qResult = MotorQualityScorer.scoreTremor({
      durationSeconds:  extracted.duration_seconds,
      tremorAmplitude:  extracted.tremor_amplitude,
      sampleCount:      sampleCount,
      extractionStatus: extracted._extraction_status,
    });

    const model = MotorSessionModel.fromTremor({
      participantId,
      features:      extracted,
      qualityResult: qResult,
    });

    setFeatures(extracted);
    setQualityResult(qResult);
    setSessionModel(model);
    setPhase(PHASE.RESULTS);
  }, [participantId]);

  const handleStop = useCallback(() => {
    clearInterval(timerRef.current);
    finishTask();
  }, [finishTask]);

  const handleSync = useCallback(async () => {
    if (!sessionModel || !supabaseClient) return;
    setIsSyncing(true);
    try {
      const result = await sessionModel.syncToSupabase(supabaseClient);
      setSyncStatus(result);
    } catch (err) {
      setSyncStatus({ success: false, error: err.message });
    } finally {
      setIsSyncing(false);
    }
  }, [sessionModel, supabaseClient]);

  const handleReset = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (collectorRef.current?.isCollecting) collectorRef.current.stopTask();
    setPhase(PHASE.READY);
    setElapsed(0);
    setLiveAmplitude(0);
    setFeatures(null);
    setQualityResult(null);
    setSessionModel(null);
    setSyncStatus(null);
    setPermissionError(null);
  }, []);

  const progressPct = (elapsed / TASK_DURATION_SEC) * 100;

  // Visual tremor meter color based on amplitude
  const amplitudeColor = liveAmplitude < 0.5 ? '#10b981'
    : liveAmplitude < 1.5 ? '#f59e0b'
    : '#ef4444';

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <Waves size={28} color="#7c3aed" />
        <div>
          <h2 style={styles.title}>Tremor Hold Task</h2>
          <p style={styles.subtitle}>Hand Stability Assessment · {TASK_DURATION_SEC}s (Optional)</p>
        </div>
      </div>

      {/* Privacy badge */}
      <div style={styles.privacyBadge}>
        <ShieldCheck size={14} color="#10b981" />
        <span>Sensor active ONLY during this {TASK_DURATION_SEC}s window · Raw IMU data discarded after FFT</span>
      </div>

      {/* Disclaimer */}
      <div style={styles.disclaimer}>
        <Info size={13} color="#6b7280" />
        <span style={{ flex: 1, lineHeight: 1.4 }}>
          Research screening result — not a clinical diagnosis. Results reflect deviation from your personal
          baseline, not a pathological threshold. Smartphone sensors are NOT clinical tremor assessment instruments.
        </span>
      </div>

      {/* READY phase */}
      {phase === PHASE.READY && (
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Instructions</h3>
          <ol style={styles.instructionList}>
            <li>Hold your phone flat in the palm of your hand.</li>
            <li>Keep your arm still and relaxed for <strong>10 seconds</strong>.</li>
            <li>Try not to move — natural hand tremor is expected and measured.</li>
            <li>The task stops automatically after 10 seconds.</li>
          </ol>
          {permissionError && (
            <div style={styles.errorBox}>
              <AlertTriangle size={16} color="#ef4444" />
              <span>{permissionError}</span>
            </div>
          )}
          <div style={styles.buttonRow}>
            <button style={styles.btnSecondary} onClick={onCancel}>Skip Task</button>
            <button style={styles.btnPrimary} onClick={handleStart}>
              <Play size={16} /> Start Hold
            </button>
          </div>
        </div>
      )}

      {/* HOLDING phase */}
      {phase === PHASE.HOLDING && (
        <div style={styles.card}>
          <div style={styles.timerRow}>
            <Timer size={16} color="#7c3aed" />
            <span style={styles.timerText}>{elapsed.toFixed(1)}s / {TASK_DURATION_SEC}s</span>
          </div>
          <div style={styles.progressTrack}>
            <div style={{ ...styles.progressFill, width: `${progressPct}%` }} />
          </div>

          <p style={styles.instruction}>
            🤚 Hold still…
          </p>

          {/* Live amplitude meter */}
          <div style={styles.meterContainer}>
            <span style={styles.meterLabel}>Live acceleration magnitude (m/s²)</span>
            <div style={styles.meterTrack}>
              <div style={{
                ...styles.meterFill,
                width: `${Math.min(liveAmplitude / 5, 1) * 100}%`,
                background: amplitudeColor,
              }} />
            </div>
            <span style={{ ...styles.meterValue, color: amplitudeColor }}>
              {liveAmplitude} m/s²
            </span>
          </div>

          <button style={styles.btnStop} onClick={handleStop}>
            <Square size={14} /> Stop Early
          </button>
        </div>
      )}

      {/* PROCESSING phase */}
      {phase === PHASE.PROCESSING && (
        <div style={styles.card}>
          <div style={styles.processingBox}>
            <BarChart2 size={32} color="#7c3aed" />
            <p>Running FFT analysis… (raw IMU data discarded)</p>
          </div>
        </div>
      )}

      {/* RESULTS phase */}
      {phase === PHASE.RESULTS && features && qualityResult && (
        <div style={styles.card}>
          <div style={styles.resultHeader}>
            {qualityResult.is_baseline_eligible
              ? <CheckCircle2 size={24} color="#10b981" />
              : <AlertTriangle size={24} color="#f59e0b" />}
            <div>
              <h3 style={styles.cardTitle}>
                Quality: {(qualityResult.quality_score * 100).toFixed(0)}%
              </h3>
              <p style={{ margin: 0, fontSize: '0.8rem', color: '#6b7280' }}>{qualityResult.summary}</p>
            </div>
          </div>

          <table style={styles.featureTable}>
            <tbody>
              <tr><td style={styles.featureKey}>Dominant Frequency</td>
                  <td style={styles.featureVal}>{features.dominant_frequency ?? '—'} Hz</td></tr>
              <tr><td style={styles.featureKey}>Peak Power</td>
                  <td style={styles.featureVal}>{features.peak_power ?? '—'}</td></tr>
              <tr><td style={styles.featureKey}>Tremor Amplitude (RMS)</td>
                  <td style={styles.featureVal}>{features.tremor_amplitude ?? '—'} m/s²</td></tr>
              <tr><td style={styles.featureKey}>Duration</td>
                  <td style={styles.featureVal}>{features.duration_seconds} s</td></tr>
              <tr><td style={styles.featureKey}>Samples Collected</td>
                  <td style={styles.featureVal}>{features.sample_count}</td></tr>
            </tbody>
          </table>

          {/* Band power ratios */}
          {features.band_power_ratios && (
            <div style={styles.bandBox}>
              <h4 style={styles.bandTitle}>Spectral Band Power Ratios</h4>
              {Object.entries(features.band_power_ratios).map(([band, ratio]) => (
                <div key={band} style={styles.bandRow}>
                  <span style={styles.bandName}>{band.replace(/_/g, ' ')}</span>
                  <div style={styles.bandBarTrack}>
                    <div style={{ ...styles.bandBarFill, width: `${(ratio * 100).toFixed(1)}%` }} />
                  </div>
                  <span style={styles.bandPct}>{(ratio * 100).toFixed(1)}%</span>
                </div>
              ))}
            </div>
          )}

          {qualityResult.rejection_reasons.length > 0 && (
            <div style={styles.warningBox}>
              <AlertTriangle size={14} color="#f59e0b" />
              <ul style={styles.warningList}>
                {qualityResult.rejection_reasons.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            </div>
          )}

          {syncStatus?.success && (
            <div style={styles.successBox}>
              <CheckCircle2 size={14} color="#10b981" />
              <span>{syncStatus.idempotent ? 'Already uploaded.' : 'Uploaded successfully.'}</span>
            </div>
          )}
          {syncStatus && !syncStatus.success && (
            <div style={styles.errorBox}>
              <AlertTriangle size={14} color="#ef4444" />
              <span>Sync error: {syncStatus.error}</span>
            </div>
          )}

          <div style={styles.buttonRow}>
            <button style={styles.btnSecondary} onClick={handleReset}>
              <RefreshCw size={14} /> Retry
            </button>
            {!syncStatus?.success && (
              <button style={styles.btnSecondary} onClick={handleSync} disabled={isSyncing}>
                <UploadCloud size={14} /> {isSyncing ? 'Uploading…' : 'Save Results'}
              </button>
            )}
            <button
              style={styles.btnPrimary}
              onClick={() => onComplete?.({ features, qualityResult, session: sessionModel })}
            >
              <CheckCircle2 size={14} /> Done
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Styles
// ─────────────────────────────────────────────────────────────────────────────

const styles = {
  container: {
    maxWidth: 540, margin: '0 auto', padding: '1.5rem',
    fontFamily: "'Inter', 'Segoe UI', sans-serif", color: '#1f2937',
    background: 'linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%)', minHeight: '100vh',
  },
  header: { display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' },
  title: { margin: 0, fontSize: '1.25rem', fontWeight: 700, color: '#3730a3' },
  subtitle: { margin: 0, fontSize: '0.8rem', color: '#6b7280' },
  privacyBadge: {
    display: 'flex', alignItems: 'center', gap: '0.4rem',
    background: '#d1fae5', borderRadius: 8, padding: '0.4rem 0.75rem',
    fontSize: '0.75rem', color: '#065f46', marginBottom: '0.6rem',
  },
  disclaimer: {
    display: 'flex', alignItems: 'flex-start', gap: '0.4rem',
    background: '#f3f4f6', borderRadius: 8, padding: '0.5rem 0.75rem',
    fontSize: '0.75rem', color: '#4b5563', marginBottom: '1rem',
  },
  card: {
    background: '#fff', borderRadius: 16, padding: '1.25rem',
    boxShadow: '0 4px 24px rgba(124,58,237,0.08)', marginBottom: '1rem',
  },
  cardTitle: { margin: '0 0 0.5rem', fontSize: '1rem', fontWeight: 700 },
  instructionList: { paddingLeft: '1.2rem', margin: '0 0 1rem', lineHeight: 1.9, fontSize: '0.9rem' },
  buttonRow: { display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', marginTop: '1rem', flexWrap: 'wrap' },
  btnPrimary: {
    display: 'flex', alignItems: 'center', gap: '0.4rem',
    background: '#7c3aed', color: '#fff', border: 'none',
    borderRadius: 10, padding: '0.55rem 1.1rem', fontWeight: 600,
    cursor: 'pointer', fontSize: '0.85rem',
  },
  btnSecondary: {
    display: 'flex', alignItems: 'center', gap: '0.4rem',
    background: '#ede9fe', color: '#4c1d95', border: 'none',
    borderRadius: 10, padding: '0.55rem 1rem', fontWeight: 600,
    cursor: 'pointer', fontSize: '0.85rem',
  },
  btnStop: {
    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.4rem',
    background: '#fef2f2', color: '#991b1b', border: '1.5px solid #fca5a5',
    borderRadius: 10, padding: '0.5rem 1.2rem', fontWeight: 600,
    cursor: 'pointer', fontSize: '0.85rem', margin: '1rem auto 0',
  },
  timerRow: { display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.4rem' },
  timerText: { color: '#7c3aed', fontWeight: 700, fontSize: '1rem' },
  progressTrack: { width: '100%', height: 8, background: '#ede9fe', borderRadius: 4, overflow: 'hidden', marginBottom: '1rem' },
  progressFill: { height: '100%', background: 'linear-gradient(90deg, #7c3aed, #a78bfa)', borderRadius: 4, transition: 'width 0.2s ease' },
  instruction: { textAlign: 'center', fontSize: '1.1rem', color: '#374151', margin: '0.5rem 0' },
  meterContainer: { background: '#f5f3ff', borderRadius: 10, padding: '0.75rem', marginTop: '0.75rem' },
  meterLabel: { fontSize: '0.72rem', color: '#7c3aed', fontWeight: 600, display: 'block', marginBottom: '0.4rem' },
  meterTrack: { width: '100%', height: 10, background: '#ede9fe', borderRadius: 5, overflow: 'hidden', marginBottom: '0.4rem' },
  meterFill: { height: '100%', borderRadius: 5, transition: 'width 0.15s ease, background 0.3s ease' },
  meterValue: { fontSize: '0.8rem', fontWeight: 700 },
  processingBox: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem', padding: '2rem', color: '#7c3aed' },
  resultHeader: { display: 'flex', alignItems: 'flex-start', gap: '0.75rem', marginBottom: '1rem' },
  featureTable: { width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', marginBottom: '0.75rem' },
  featureKey: { padding: '0.35rem 0.5rem', color: '#6b7280', width: '60%' },
  featureVal: { padding: '0.35rem 0.5rem', fontWeight: 600, color: '#111827' },
  bandBox: { background: '#f5f3ff', borderRadius: 10, padding: '0.75rem', marginBottom: '0.75rem' },
  bandTitle: { margin: '0 0 0.5rem', fontSize: '0.8rem', fontWeight: 700, color: '#4c1d95' },
  bandRow: { display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.3rem' },
  bandName: { fontSize: '0.72rem', color: '#6b7280', width: '40%', textTransform: 'capitalize' },
  bandBarTrack: { flex: 1, height: 6, background: '#ede9fe', borderRadius: 3, overflow: 'hidden' },
  bandBarFill: { height: '100%', background: 'linear-gradient(90deg, #7c3aed, #a78bfa)', borderRadius: 3 },
  bandPct: { fontSize: '0.72rem', fontWeight: 700, color: '#7c3aed', width: '3.5rem', textAlign: 'right' },
  warningBox: {
    display: 'flex', alignItems: 'flex-start', gap: '0.4rem',
    background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 8,
    padding: '0.5rem 0.75rem', marginBottom: '0.5rem',
  },
  warningList: { margin: 0, paddingLeft: '1rem', fontSize: '0.78rem', color: '#92400e' },
  successBox: {
    display: 'flex', alignItems: 'center', gap: '0.4rem',
    background: '#ecfdf5', borderRadius: 8, padding: '0.5rem 0.75rem',
    fontSize: '0.8rem', color: '#065f46', marginBottom: '0.5rem',
  },
  errorBox: {
    display: 'flex', alignItems: 'center', gap: '0.4rem',
    background: '#fef2f2', borderRadius: 8, padding: '0.5rem 0.75rem',
    fontSize: '0.8rem', color: '#991b1b', marginBottom: '0.5rem',
  },
};
