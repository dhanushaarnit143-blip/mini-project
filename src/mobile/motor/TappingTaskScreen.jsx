import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Hand,
  Play,
  CheckCircle2,
  AlertTriangle,
  UploadCloud,
  ShieldCheck,
  Timer,
  BarChart2,
  RefreshCw,
  Info,
  Zap,
} from 'lucide-react';
import { extractTappingFeatures } from './tappingFeatureExtractor.js';
import { MotorQualityScorer } from './motorQualityScorer.js';
import { MotorSessionModel, MOTOR_TASK_TYPES } from './motorSessionModel.js';

/**
 * MPF Mobile Extension — Finger Tapping Task Screen (Phase 6)
 *
 * Guides the participant through a standardized alternating finger-tapping task
 * (10–20 seconds). Records ONLY touchscreen tap timestamps — no gesture geometry,
 * no text, no pressure data.
 *
 * Features extracted: tap_count, tapping_rate, inter_tap_interval_mean/variability,
 *                     decline_slope.
 *
 * COMPLIANCE:
 * - "Research screening result — not a clinical diagnosis."
 * - "Progressive deviation from personal baseline" — NOT disease progression.
 * - No background data collection.
 */

const TASK_DURATION_SEC = 15; // default 15 seconds (configurable 10-20)
const TARGET_COLORS = { active: '#7c3aed', inactive: '#ede9fe', tap: '#a78bfa' };

const PHASE = {
  READY:      'ready',
  TAPPING:    'tapping',
  PROCESSING: 'processing',
  RESULTS:    'results',
};

export function TappingTaskScreen({ participantId, supabaseClient, onComplete, onCancel, taskDurationSec = TASK_DURATION_SEC }) {
  const [phase, setPhase]                 = useState(PHASE.READY);
  const [elapsed, setElapsed]             = useState(0);
  const [tapCount, setTapCount]           = useState(0);
  const [activeTarget, setActiveTarget]   = useState(0); // 0 = left, 1 = right
  const [flashTarget, setFlashTarget]     = useState(null);
  const [features, setFeatures]           = useState(null);
  const [qualityResult, setQualityResult] = useState(null);
  const [sessionModel, setSessionModel]   = useState(null);
  const [isSyncing, setIsSyncing]         = useState(false);
  const [syncStatus, setSyncStatus]       = useState(null);

  const tapTimestampsRef = useRef([]); // ONLY timestamps — no other tap data
  const timerRef         = useRef(null);
  const startMsRef       = useRef(null);
  const taskDurationMs   = taskDurationSec * 1000;

  useEffect(() => {
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, []);

  const handleStart = useCallback(() => {
    tapTimestampsRef.current = [];
    setTapCount(0);
    setActiveTarget(0);
    setFlashTarget(null);
    setPhase(PHASE.TAPPING);
    startMsRef.current = performance.now();

    timerRef.current = setInterval(() => {
      const sec = (performance.now() - startMsRef.current) / 1000;
      setElapsed(Math.min(sec, taskDurationSec));
      if (sec >= taskDurationSec) {
        clearInterval(timerRef.current);
        finishTask();
      }
    }, 200);
  }, [taskDurationSec]);

  const handleTap = useCallback((targetIdx) => {
    if (phase !== PHASE.TAPPING) return;

    // Record ONLY the timestamp — no position, pressure, or gesture data
    tapTimestampsRef.current.push(performance.now());

    setTapCount(c => c + 1);
    setActiveTarget(targetIdx === 0 ? 1 : 0); // alternate target
    setFlashTarget(targetIdx);
    setTimeout(() => setFlashTarget(null), 120);
  }, [phase]);

  const finishTask = useCallback(() => {
    clearInterval(timerRef.current);
    const durationMs = performance.now() - startMsRef.current;

    setPhase(PHASE.PROCESSING);

    // Shallow copy for extractor — original ref cleared immediately after
    const timestamps = [...tapTimestampsRef.current];
    tapTimestampsRef.current = []; // discard raw timestamps

    const extracted = extractTappingFeatures(timestamps, durationMs);

    const qResult = MotorQualityScorer.scoreTapping({
      durationSeconds:           extracted.duration_seconds,
      tapCount:                  extracted.tap_count,
      tappingRate:               extracted.tapping_rate,
      interTapIntervalVariability: extracted.inter_tap_interval_variability,
    });

    const model = MotorSessionModel.fromTapping({
      participantId,
      features:      extracted,
      qualityResult: qResult,
    });

    setFeatures(extracted);
    setQualityResult(qResult);
    setSessionModel(model);
    setPhase(PHASE.RESULTS);
  }, [participantId]);

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
    tapTimestampsRef.current = [];
    setPhase(PHASE.READY);
    setElapsed(0);
    setTapCount(0);
    setFeatures(null);
    setQualityResult(null);
    setSessionModel(null);
    setSyncStatus(null);
  }, []);

  const progressPct = (elapsed / taskDurationSec) * 100;

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <Hand size={28} color="#7c3aed" />
        <div>
          <h2 style={styles.title}>Finger Tapping Task</h2>
          <p style={styles.subtitle}>Alternating Tap Speed & Rhythm · {taskDurationSec}s</p>
        </div>
      </div>

      {/* Privacy badge */}
      <div style={styles.privacyBadge}>
        <ShieldCheck size={14} color="#10b981" />
        <span>Only tap timestamps recorded — no gesture, text, or pressure data</span>
      </div>

      {/* Disclaimer */}
      <div style={styles.disclaimer}>
        <Info size={13} color="#6b7280" />
        <span style={{ flex: 1, lineHeight: 1.4 }}>
          Research screening result — not a clinical diagnosis. Measures deviation from personal baseline.
        </span>
      </div>

      {/* READY phase */}
      {phase === PHASE.READY && (
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Instructions</h3>
          <ol style={styles.instructionList}>
            <li>Two targets will appear below.</li>
            <li>Alternately tap <strong>Left → Right → Left → Right</strong>…</li>
            <li>Tap as fast as you can for <strong>{taskDurationSec} seconds</strong>.</li>
            <li>Keep a steady rhythm throughout.</li>
          </ol>
          <div style={styles.buttonRow}>
            <button style={styles.btnSecondary} onClick={onCancel}>Cancel</button>
            <button style={styles.btnPrimary} onClick={handleStart}>
              <Play size={16} /> Start Tapping
            </button>
          </div>
        </div>
      )}

      {/* TAPPING phase */}
      {phase === PHASE.TAPPING && (
        <div style={styles.card}>
          <div style={styles.timerRow}>
            <Timer size={16} color="#7c3aed" />
            <span style={styles.timerText}>{elapsed.toFixed(1)}s / {taskDurationSec}s</span>
            <span style={styles.tapCount}>Taps: {tapCount}</span>
          </div>
          <div style={styles.progressTrack}>
            <div style={{ ...styles.progressFill, width: `${progressPct}%` }} />
          </div>

          {/* Tapping targets */}
          <div style={styles.targetsRow}>
            {[0, 1].map(idx => {
              const isActive = activeTarget === idx;
              const isFlash  = flashTarget === idx;
              return (
                <button
                  key={idx}
                  style={{
                    ...styles.target,
                    background: isFlash
                      ? TARGET_COLORS.tap
                      : isActive
                        ? TARGET_COLORS.active
                        : TARGET_COLORS.inactive,
                    color: isActive || isFlash ? '#fff' : '#7c3aed',
                    transform: isFlash ? 'scale(0.93)' : 'scale(1)',
                    boxShadow: isActive
                      ? '0 0 0 4px rgba(124,58,237,0.25)'
                      : '0 2px 8px rgba(0,0,0,0.08)',
                  }}
                  onPointerDown={() => handleTap(idx)}
                  aria-label={idx === 0 ? 'Left tap target' : 'Right tap target'}
                >
                  <Zap size={28} />
                  <span style={styles.targetLabel}>{idx === 0 ? 'LEFT' : 'RIGHT'}</span>
                </button>
              );
            })}
          </div>

          <p style={styles.hint}>
            {activeTarget === 0 ? '← Tap LEFT' : 'Tap RIGHT →'}
          </p>
          <button style={styles.btnStop} onClick={() => finishTask()}>
            Stop Early
          </button>
        </div>
      )}

      {/* PROCESSING phase */}
      {phase === PHASE.PROCESSING && (
        <div style={styles.card}>
          <div style={styles.processingBox}>
            <BarChart2 size={32} color="#7c3aed" />
            <p>Analyzing tap rhythm… (raw timestamps discarded)</p>
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
              <tr><td style={styles.featureKey}>Total Taps</td>
                  <td style={styles.featureVal}>{features.tap_count}</td></tr>
              <tr><td style={styles.featureKey}>Tapping Rate</td>
                  <td style={styles.featureVal}>{features.tapping_rate ?? '—'} taps/s</td></tr>
              <tr><td style={styles.featureKey}>ITI Mean</td>
                  <td style={styles.featureVal}>{features.inter_tap_interval_mean ?? '—'} ms</td></tr>
              <tr><td style={styles.featureKey}>ITI Variability (CV)</td>
                  <td style={styles.featureVal}>{features.inter_tap_interval_variability ?? '—'}</td></tr>
              <tr><td style={styles.featureKey}>Decline Slope</td>
                  <td style={styles.featureVal}>{features.decline_slope ?? '—'} ms/tap</td></tr>
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
    display: 'block', margin: '0.75rem auto 0',
    background: '#fef2f2', color: '#991b1b', border: '1.5px solid #fca5a5',
    borderRadius: 10, padding: '0.5rem 1.2rem', fontWeight: 600,
    cursor: 'pointer', fontSize: '0.85rem',
  },
  timerRow: { display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.4rem' },
  timerText: { color: '#7c3aed', fontWeight: 700, fontSize: '1rem' },
  tapCount: { marginLeft: 'auto', fontWeight: 700, color: '#3730a3' },
  progressTrack: { width: '100%', height: 8, background: '#ede9fe', borderRadius: 4, overflow: 'hidden', marginBottom: '1.5rem' },
  progressFill: { height: '100%', background: 'linear-gradient(90deg, #7c3aed, #a78bfa)', borderRadius: 4, transition: 'width 0.2s ease' },
  targetsRow: { display: 'flex', gap: '1.5rem', justifyContent: 'center', marginBottom: '1rem' },
  target: {
    flex: 1, maxWidth: 140, height: 140, borderRadius: 24,
    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
    border: 'none', cursor: 'pointer', transition: 'all 0.12s ease', gap: '0.5rem',
    userSelect: 'none', touchAction: 'manipulation',
  },
  targetLabel: { fontWeight: 700, fontSize: '0.8rem', letterSpacing: '0.05em' },
  hint: { textAlign: 'center', color: '#7c3aed', fontWeight: 600, fontSize: '1rem', margin: '0.25rem 0' },
  processingBox: {
    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem',
    padding: '2rem', color: '#7c3aed',
  },
  resultHeader: { display: 'flex', alignItems: 'flex-start', gap: '0.75rem', marginBottom: '1rem' },
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
