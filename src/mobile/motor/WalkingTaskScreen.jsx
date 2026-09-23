import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Activity,
  Play,
  Square,
  CheckCircle2,
  AlertTriangle,
  UploadCloud,
  ShieldCheck,
  Timer,
  Footprints,
  BarChart2,
  RefreshCw,
  Info,
} from 'lucide-react';
import { SensorCollector } from './sensorCollector.js';
import { extractWalkingFeatures } from './walkingFeatureExtractor.js';
import { MotorQualityScorer } from './motorQualityScorer.js';
import { MotorSessionModel, MOTOR_TASK_TYPES } from './motorSessionModel.js';

/**
 * MPF Mobile Extension — Walking Task Screen (Phase 6)
 *
 * Guides the participant through a standardized 30-second walking test.
 * Collects accelerometer/gyroscope data ONLY during the active window.
 * Extracts features locally — raw sensor data is discarded immediately.
 *
 * COMPLIANCE:
 * - "Research screening result — not a clinical diagnosis."
 * - "Deviation from personal baseline" — NOT disease progression.
 * - No background sensor collection.
 * - Raw sensor streams are never persisted or uploaded.
 */

const TASK_DURATION_SEC = 30;

const PHASE = {
  READY:      'ready',
  WALKING:    'walking',
  PROCESSING: 'processing',
  RESULTS:    'results',
};

export function WalkingTaskScreen({ participantId, supabaseClient, onComplete, onCancel }) {
  const [phase, setPhase]                 = useState(PHASE.READY);
  const [elapsed, setElapsed]             = useState(0);
  const [liveAccel, setLiveAccel]         = useState({ x: 0, y: 0, z: 0 });
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

    setPhase(PHASE.WALKING);
    setElapsed(0);
    startMsRef.current = Date.now();

    collector.startTask(MOTOR_TASK_TYPES.WALKING, (sample) => {
      setLiveAccel({ x: sample.ax.toFixed(2), y: sample.ay.toFixed(2), z: sample.az.toFixed(2) });
    });

    timerRef.current = setInterval(() => {
      const sec = (Date.now() - startMsRef.current) / 1000;
      setElapsed(Math.min(sec, TASK_DURATION_SEC));
      if (sec >= TASK_DURATION_SEC) {
        clearInterval(timerRef.current);
        finishTask();
      }
    }, 500);
  }, []);

  const finishTask = useCallback(() => {
    clearInterval(timerRef.current);
    const collector = collectorRef.current;
    const { samples, durationMs } = collector.stopTask();

    setPhase(PHASE.PROCESSING);

    // Extract features — raw samples used and immediately discarded
    const extracted = extractWalkingFeatures(samples, durationMs);

    const qResult = MotorQualityScorer.scoreWalking({
      sensorAvailable: true,
      durationSeconds: extracted.duration_seconds,
      stepCount:       extracted.step_count,
      cadence:         extracted.cadence,
      movementRegularity: extracted.movement_regularity,
    });

    const model = MotorSessionModel.fromWalking({
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
    setPhase(PHASE.READY);
    setElapsed(0);
    setFeatures(null);
    setQualityResult(null);
    setSessionModel(null);
    setSyncStatus(null);
    setPermissionError(null);
  }, []);

  const progressPct = (elapsed / TASK_DURATION_SEC) * 100;

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <Footprints size={28} color="#7c3aed" />
        <div>
          <h2 style={styles.title}>Walking Task</h2>
          <p style={styles.subtitle}>Gait & Movement Analysis · 30 seconds</p>
        </div>
      </div>

      {/* Privacy badge */}
      <div style={styles.privacyBadge}>
        <ShieldCheck size={14} color="#10b981" />
        <span style={styles.privacyText}>
          Sensor active ONLY during this task · Raw data discarded after extraction
        </span>
      </div>

      {/* Disclaimer */}
      <div style={styles.disclaimer}>
        <Info size={13} color="#6b7280" />
        <span style={styles.disclaimerText}>
          Research screening result — not a clinical diagnosis. Measures deviation from personal baseline.
        </span>
      </div>

      {/* READY phase */}
      {phase === PHASE.READY && (
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Instructions</h3>
          <ol style={styles.instructionList}>
            <li>Hold your phone naturally (in hand or pocket).</li>
            <li>Walk at your normal pace when the task starts.</li>
            <li>Continue walking for <strong>30 seconds</strong>.</li>
            <li>The task will stop automatically, or tap Stop early.</li>
          </ol>
          {permissionError && (
            <div style={styles.errorBox}>
              <AlertTriangle size={16} color="#ef4444" />
              <span>{permissionError}</span>
            </div>
          )}
          <div style={styles.buttonRow}>
            <button style={styles.btnSecondary} onClick={onCancel}>Cancel</button>
            <button style={styles.btnPrimary} onClick={handleStart}>
              <Play size={16} /> Start Walking
            </button>
          </div>
        </div>
      )}

      {/* WALKING phase */}
      {phase === PHASE.WALKING && (
        <div style={styles.card}>
          <div style={styles.timerDisplay}>
            <Timer size={20} color="#7c3aed" />
            <span style={styles.timerText}>{elapsed.toFixed(0)}s / {TASK_DURATION_SEC}s</span>
          </div>
          <div style={styles.progressTrack}>
            <div style={{ ...styles.progressFill, width: `${progressPct}%` }} />
          </div>
          <p style={styles.instruction}>
            🚶 Walk at your normal pace…
          </p>
          <div style={styles.liveReadings}>
            <span style={styles.liveLabel}>Live accelerometer (m/s²)</span>
            <div style={styles.axisRow}>
              <span>X: <strong>{liveAccel.x}</strong></span>
              <span>Y: <strong>{liveAccel.y}</strong></span>
              <span>Z: <strong>{liveAccel.z}</strong></span>
            </div>
          </div>
          <button style={styles.btnStop} onClick={handleStop}>
            <Square size={16} /> Stop Early
          </button>
        </div>
      )}

      {/* PROCESSING phase */}
      {phase === PHASE.PROCESSING && (
        <div style={styles.card}>
          <div style={styles.processingBox}>
            <Activity size={32} color="#7c3aed" style={{ animation: 'spin 1s linear infinite' }} />
            <p>Extracting gait features… (raw data is discarded)</p>
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
              <p style={styles.qualitySummary}>{qualityResult.summary}</p>
            </div>
          </div>

          <table style={styles.featureTable}>
            <tbody>
              <tr><td style={styles.featureKey}>Cadence</td>
                  <td style={styles.featureVal}>{features.cadence ?? '—'} steps/min</td></tr>
              <tr><td style={styles.featureKey}>Stride Interval Mean</td>
                  <td style={styles.featureVal}>{features.stride_interval_mean ?? '—'} s</td></tr>
              <tr><td style={styles.featureKey}>Stride Variability (CV)</td>
                  <td style={styles.featureVal}>{features.stride_interval_variability ?? '—'}</td></tr>
              <tr><td style={styles.featureKey}>Movement Regularity</td>
                  <td style={styles.featureVal}>{features.movement_regularity ?? '—'}</td></tr>
              <tr><td style={styles.featureKey}>Symmetry Index</td>
                  <td style={styles.featureVal}>{features.symmetry_index ?? '—'}</td></tr>
              <tr><td style={styles.featureKey}>Steps Detected</td>
                  <td style={styles.featureVal}>{features.step_count}</td></tr>
              <tr><td style={styles.featureKey}>Duration</td>
                  <td style={styles.featureVal}>{features.duration_seconds} s</td></tr>
            </tbody>
          </table>

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
    maxWidth: 540,
    margin: '0 auto',
    padding: '1.5rem',
    fontFamily: "'Inter', 'Segoe UI', sans-serif",
    color: '#1f2937',
    background: 'linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%)',
    minHeight: '100vh',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    marginBottom: '1rem',
  },
  title: { margin: 0, fontSize: '1.25rem', fontWeight: 700, color: '#3730a3' },
  subtitle: { margin: 0, fontSize: '0.8rem', color: '#6b7280' },
  privacyBadge: {
    display: 'flex', alignItems: 'center', gap: '0.4rem',
    background: '#d1fae5', borderRadius: 8, padding: '0.4rem 0.75rem',
    fontSize: '0.75rem', color: '#065f46', marginBottom: '0.6rem',
  },
  privacyText: { flex: 1 },
  disclaimer: {
    display: 'flex', alignItems: 'flex-start', gap: '0.4rem',
    background: '#f3f4f6', borderRadius: 8, padding: '0.5rem 0.75rem',
    fontSize: '0.75rem', color: '#4b5563', marginBottom: '1rem',
  },
  disclaimerText: { flex: 1, lineHeight: 1.4 },
  card: {
    background: '#fff',
    borderRadius: 16,
    padding: '1.25rem',
    boxShadow: '0 4px 24px rgba(124,58,237,0.08)',
    marginBottom: '1rem',
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
    display: 'flex', alignItems: 'center', gap: '0.4rem',
    background: '#fef2f2', color: '#991b1b', border: '1.5px solid #fca5a5',
    borderRadius: 10, padding: '0.55rem 1rem', fontWeight: 600,
    cursor: 'pointer', fontSize: '0.85rem', margin: '1rem auto 0',
  },
  timerDisplay: {
    display: 'flex', alignItems: 'center', gap: '0.5rem',
    fontSize: '1.1rem', fontWeight: 700, marginBottom: '0.5rem',
  },
  timerText: { color: '#7c3aed' },
  progressTrack: {
    width: '100%', height: 8, background: '#ede9fe', borderRadius: 4, overflow: 'hidden', marginBottom: '1rem',
  },
  progressFill: {
    height: '100%', background: 'linear-gradient(90deg, #7c3aed, #a78bfa)',
    borderRadius: 4, transition: 'width 0.5s ease',
  },
  instruction: { textAlign: 'center', fontSize: '1rem', color: '#374151', margin: '0.5rem 0' },
  liveReadings: {
    background: '#f5f3ff', borderRadius: 8, padding: '0.6rem 0.8rem', marginTop: '0.75rem',
  },
  liveLabel: { fontSize: '0.7rem', color: '#7c3aed', fontWeight: 600, display: 'block', marginBottom: '0.3rem' },
  axisRow: { display: 'flex', gap: '1.5rem', fontSize: '0.85rem', color: '#374151' },
  processingBox: {
    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem',
    padding: '2rem', color: '#7c3aed',
  },
  resultHeader: { display: 'flex', alignItems: 'flex-start', gap: '0.75rem', marginBottom: '1rem' },
  qualitySummary: { margin: 0, fontSize: '0.8rem', color: '#6b7280' },
  featureTable: { width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', marginBottom: '0.75rem' },
  featureKey: { padding: '0.35rem 0.5rem', color: '#6b7280', width: '60%' },
  featureVal: { padding: '0.35rem 0.5rem', fontWeight: 600, color: '#111827' },
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
