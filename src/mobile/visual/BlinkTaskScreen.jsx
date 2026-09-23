import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Eye,
  Play,
  Square,
  CheckCircle2,
  AlertTriangle,
  UploadCloud,
  ShieldCheck,
  Timer,
  RefreshCw,
  Info,
  Camera,
  Activity,
} from 'lucide-react';
import { FaceLandmarkDetector } from './faceLandmarkDetector.js';
import { extractBlinkFeatures } from './visualFeatureExtractor.js';
import { VisualQualityScorer } from './visualQualityScorer.js';
import { VisualSessionModel, VISUAL_TASK_TYPES } from './visualSessionModel.js';

/**
 * MPF Mobile Extension — Blink Dynamics Task Screen (Phase 7)
 *
 * Task 2: Spontaneous blink measurement.
 * Instruction: "Look at the screen naturally for 30 seconds."
 *
 * CRITICAL PRIVACY & CLINICAL COMPLIANCE:
 * - "Ocular/Visual Behavior Module" — NOT retinal imaging.
 * - Video stream is processed in-memory locally.
 * - ZERO video recordings or facial images stored or uploaded.
 * - Camera active ONLY during the active task window.
 * - "Research screening result — not a clinical diagnosis."
 * - "Deviation from personal baseline."
 */

const TASK_DURATION_SEC = 30;

const PHASE = {
  READY:      'ready',
  RECORDING:  'recording',
  PROCESSING: 'processing',
  RESULTS:    'results',
};

export function BlinkTaskScreen({ participantId, supabaseClient, onComplete, onCancel }) {
  const [phase, setPhase]                 = useState(PHASE.READY);
  const [elapsed, setElapsed]             = useState(0);
  const [liveBlinkCount, setLiveBlinkCount] = useState(0);
  const [features, setFeatures]           = useState(null);
  const [qualityResult, setQualityResult] = useState(null);
  const [sessionModel, setSessionModel]   = useState(null);
  const [isSyncing, setIsSyncing]         = useState(false);
  const [syncStatus, setSyncStatus]       = useState(null);
  const [cameraActive, setCameraActive]   = useState(false);
  const [permissionError, setPermissionError] = useState(null);

  const detectorRef    = useRef(null);
  const earSamplesRef  = useRef([]);
  const timerRef       = useRef(null);
  const startMsRef     = useRef(null);

  // Quality accumulators
  const faceDetectedCountRef = useRef(0);
  const goodLightingCountRef = useRef(0);
  const totalFramesRef       = useRef(0);
  const confidencesRef       = useRef([]);
  const headDisplacementsRef = useRef([]);

  // Live blink counter tracking
  const wasBlinkingRef       = useRef(false);
  const blinkCountRef        = useRef(0);

  useEffect(() => {
    detectorRef.current = new FaceLandmarkDetector();
    return () => {
      _cleanupResources();
    };
  }, []);

  const _cleanupResources = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (detectorRef.current) detectorRef.current.dispose();
  };

  const handleStart = useCallback(async () => {
    setPermissionError(null);
    earSamplesRef.current = [];
    faceDetectedCountRef.current = 0;
    goodLightingCountRef.current = 0;
    totalFramesRef.current = 0;
    confidencesRef.current = [];
    headDisplacementsRef.current = [];
    wasBlinkingRef.current = false;
    blinkCountRef.current = 0;
    setLiveBlinkCount(0);

    const detector = detectorRef.current;
    const perm = await detector.requestPermissionAndStart((landmark) => {
      totalFramesRef.current++;
      if (landmark.faceDetected) faceDetectedCountRef.current++;
      if (landmark.lighting?.isAcceptable) goodLightingCountRef.current++;
      if (landmark.confidence) confidencesRef.current.push(landmark.confidence);
      if (landmark.headPose?.displacement) headDisplacementsRef.current.push(landmark.headPose.displacement);

      const ear = landmark.eyes?.meanEar ?? 0.30;
      const isBlink = landmark.eyes?.isBlink ?? (ear < 0.21);

      // Local real-time blink counter
      if (isBlink && !wasBlinkingRef.current) {
        blinkCountRef.current++;
        setLiveBlinkCount(blinkCountRef.current);
      }
      wasBlinkingRef.current = isBlink;

      // Store numeric EAR sample only (no image data)
      earSamplesRef.current.push({
        t: performance.now(),
        ear,
        confidence: landmark.confidence,
      });
    });

    if (!perm.granted) {
      setPermissionError(perm.error || 'Camera permission required.');
      return;
    }

    setCameraActive(true);
    setPhase(PHASE.RECORDING);
    setElapsed(0);
    startMsRef.current = Date.now();

    timerRef.current = setInterval(() => {
      const sec = (Date.now() - startMsRef.current) / 1000;
      setElapsed(Math.min(sec, TASK_DURATION_SEC));
      if (sec >= TASK_DURATION_SEC) {
        clearInterval(timerRef.current);
        finishTask();
      }
    }, 250);
  }, []);

  const finishTask = useCallback(() => {
    setPhase(PHASE.PROCESSING);

    // Stop camera immediately
    if (detectorRef.current) {
      detectorRef.current.stop();
    }
    setCameraActive(false);

    const actualDurationMs = Date.now() - startMsRef.current;
    const actualDurationSec = actualDurationMs / 1000;
    const totalFrames = Math.max(1, totalFramesRef.current);

    const faceRatio = faceDetectedCountRef.current / totalFrames;
    const lightRatio = goodLightingCountRef.current / totalFrames;
    const avgConf = confidencesRef.current.length > 0
      ? confidencesRef.current.reduce((a, b) => a + b, 0) / confidencesRef.current.length
      : 0.9;
    const avgHeadDisp = headDisplacementsRef.current.length > 0
      ? headDisplacementsRef.current.reduce((a, b) => a + b, 0) / headDisplacementsRef.current.length
      : 0.02;

    const quality = VisualQualityScorer.scoreSession({
      taskType: 'blink',
      actualDurationSec,
      targetDurationSec: TASK_DURATION_SEC,
      faceDetectedRatio: faceRatio,
      goodLightingRatio: lightRatio,
      meanConfidence: avgConf,
      headDisplacement: avgHeadDisp,
    });

    const feat = extractBlinkFeatures(earSamplesRef.current, actualDurationMs);

    let model = null;
    if (participantId) {
      try {
        model = VisualSessionModel.fromBlink({
          participantId,
          features: feat,
          qualityResult: quality,
        });
      } catch (err) {
        console.error('VisualSessionModel construction failed:', err);
      }
    }

    setFeatures(feat);
    setQualityResult(quality);
    setSessionModel(model);
    setPhase(PHASE.RESULTS);
  }, [participantId]);

  const handleStopEarly = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    finishTask();
  };

  const handleSync = async () => {
    if (!sessionModel || !supabaseClient) return;
    setIsSyncing(true);
    setSyncStatus(null);
    const res = await sessionModel.syncToSupabase(supabaseClient);
    setIsSyncing(false);
    if (res.success) {
      setSyncStatus({ ok: true, message: 'Blink metrics successfully synced.' });
      if (onComplete) onComplete(sessionModel);
    } else {
      setSyncStatus({ ok: false, message: res.error?.message || 'Sync failed.' });
    }
  };

  const progressPercent = Math.min(100, Math.round((elapsed / TASK_DURATION_SEC) * 100));

  return (
    <div className="flex flex-col min-h-screen bg-slate-900 text-slate-100 p-4 max-w-xl mx-auto font-sans">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
        <div className="flex items-center gap-2">
          <Eye className="w-6 h-6 text-sky-400" />
          <div>
            <h1 className="text-lg font-semibold text-white tracking-wide">
              Blink Measurement Task
            </h1>
            <p className="text-xs text-slate-400">
              Ocular/Visual Behavior Module • 30-Second Rest
            </p>
          </div>
        </div>
        {cameraActive && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 bg-rose-500/20 border border-rose-500/50 rounded-full animate-pulse">
            <Camera className="w-3.5 h-3.5 text-rose-400" />
            <span className="text-[11px] font-medium text-rose-300">Camera Active</span>
          </div>
        )}
      </div>

      {/* Mandatory Non-Diagnostic / Non-Retinal Banner */}
      <div className="bg-amber-950/40 border border-amber-500/30 rounded-lg p-2.5 mb-4 flex items-start gap-2">
        <Info className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
        <div className="text-[11px] text-amber-200/90 leading-tight">
          <span className="font-semibold text-amber-300">Notice:</span> Research screening result — not a clinical diagnosis.
          Spontaneous blink rate is an ocular behavioral biomarker, <strong>NOT retinal imaging</strong>. Video frames are processed in-memory and discarded immediately.
        </div>
      </div>

      {/* Main Interactive Stage */}
      {phase === PHASE.READY && (
        <div className="flex-1 flex flex-col justify-center items-center text-center px-4 py-8">
          <div className="w-20 h-20 rounded-full bg-sky-500/10 border-2 border-sky-500/30 flex items-center justify-center mb-6">
            <Eye className="w-10 h-10 text-sky-400" />
          </div>
          <h2 className="text-xl font-bold text-white mb-2">Look at the Screen Naturally</h2>
          <p className="text-sm text-slate-300 mb-6 max-w-sm">
            Hold your device comfortably and look at the screen naturally for 30 seconds. Blink as you normally would without forcing or resisting.
          </p>

          <div className="bg-slate-800/60 rounded-lg p-3 text-xs text-slate-400 mb-6 max-w-sm text-left space-y-1.5 border border-slate-700/50">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span>Camera runs only during the 30-second window</span>
            </div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span>Zero facial recordings or pictures saved</span>
            </div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span>Derives blink rate and interval variability</span>
            </div>
          </div>

          {permissionError && (
            <div className="bg-rose-950/50 border border-rose-500/40 rounded-lg p-3 text-xs text-rose-300 mb-4 max-w-sm">
              {permissionError}
            </div>
          )}

          <div className="flex gap-3 w-full max-w-sm">
            {onCancel && (
              <button
                onClick={onCancel}
                className="flex-1 py-3 px-4 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-sm transition"
              >
                Cancel
              </button>
            )}
            <button
              onClick={handleStart}
              className="flex-1 py-3 px-4 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-medium text-sm flex items-center justify-center gap-2 shadow-lg shadow-sky-900/30 transition"
            >
              <Play className="w-4 h-4 fill-current" />
              Start 30s Task
            </button>
          </div>
        </div>
      )}

      {phase === PHASE.RECORDING && (
        <div className="flex-1 flex flex-col">
          {/* Progress / Status Header */}
          <div className="mb-3">
            <div className="flex justify-between items-center text-xs text-slate-400 mb-1.5">
              <span>Blink naturally • Focus on center dot</span>
              <span className="font-mono text-sky-400 font-semibold">{elapsed.toFixed(1)}s / {TASK_DURATION_SEC}s</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
              <div
                className="bg-sky-500 h-1.5 transition-all duration-200"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>

          {/* Calming Central Fixation Stage */}
          <div className="flex-1 relative bg-slate-950 border border-slate-800 rounded-xl overflow-hidden min-h-[340px] flex flex-col items-center justify-center">
            {/* Concentric rings for natural gaze anchoring */}
            <div className="w-32 h-32 rounded-full border border-sky-500/20 flex items-center justify-center animate-pulse">
              <div className="w-20 h-20 rounded-full border border-sky-500/40 flex items-center justify-center">
                <div className="w-4 h-4 rounded-full bg-sky-400 shadow-[0_0_16px_rgba(56,189,248,0.7)]" />
              </div>
            </div>

            {/* Live Local Blink Counter Indicator */}
            <div className="mt-8 bg-slate-900/80 border border-slate-800 rounded-full px-4 py-1.5 flex items-center gap-2">
              <Activity className="w-4 h-4 text-sky-400" />
              <span className="text-xs text-slate-300">
                Blinks detected: <strong className="text-sky-300 font-mono text-sm">{liveBlinkCount}</strong>
              </span>
            </div>

            <div className="absolute bottom-4 text-center pointer-events-none">
              <span className="text-[11px] text-slate-500 bg-slate-900/80 px-3 py-1 rounded-full border border-slate-800">
                Processed locally • Discarded instantly
              </span>
            </div>
          </div>

          {/* Abort Button */}
          <div className="mt-4 flex justify-center">
            <button
              onClick={handleStopEarly}
              className="py-2.5 px-6 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium flex items-center gap-2 transition"
            >
              <Square className="w-3.5 h-3.5 fill-current text-rose-400" />
              Stop Early
            </button>
          </div>
        </div>
      )}

      {phase === PHASE.PROCESSING && (
        <div className="flex-1 flex flex-col justify-center items-center text-center">
          <RefreshCw className="w-8 h-8 text-sky-400 animate-spin mb-3" />
          <h3 className="text-base font-semibold text-white">Analyzing Blink Dynamics</h3>
          <p className="text-xs text-slate-400 max-w-xs mt-1">
            Calculating blink rate, interval variability, and duration.
          </p>
        </div>
      )}

      {phase === PHASE.RESULTS && features && qualityResult && (
        <div className="flex-1 flex flex-col justify-between py-2 space-y-4">
          <div className="space-y-4">
            {/* Quality Assessment Banner */}
            <div className={`p-4 rounded-xl border ${
              qualityResult.is_baseline_eligible
                ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-200'
                : 'bg-amber-950/30 border-amber-500/40 text-amber-200'
            }`}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  {qualityResult.is_baseline_eligible ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-amber-400" />
                  )}
                  <span className="font-semibold text-sm">
                    {qualityResult.is_baseline_eligible ? 'Eligible for Baseline' : 'Suboptimal Quality'}
                  </span>
                </div>
                <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-slate-800/80">
                  Score: {(qualityResult.quality_score * 100).toFixed(0)}%
                </span>
              </div>
              <p className="text-xs text-slate-300">
                {qualityResult.is_baseline_eligible
                  ? 'Blink metrics meet protocol inclusion criteria.'
                  : 'Session quality falls below baseline inclusion criteria (< 50%).'}
              </p>
              {qualityResult.rejection_reasons.length > 0 && (
                <ul className="mt-2 text-[11px] text-amber-300/90 list-disc list-inside space-y-0.5">
                  {qualityResult.rejection_reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              )}
            </div>

            {/* Primary Extracted Blink Biomarkers */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-slate-800/70 border border-slate-700/60 rounded-xl p-3.5">
                <span className="text-xs text-slate-400">Blink Rate</span>
                <div className="text-xl font-bold text-sky-400 mt-1">
                  {features.blink_rate !== null ? features.blink_rate.toFixed(1) : 'N/A'}
                </div>
                <span className="text-[10px] text-slate-500">Blinks / minute</span>
              </div>

              <div className="bg-slate-800/70 border border-slate-700/60 rounded-xl p-3.5">
                <span className="text-xs text-slate-400">Interval Variability</span>
                <div className="text-xl font-bold text-sky-400 mt-1">
                  {features.blink_interval_variability !== null
                    ? (features.blink_interval_variability * 100).toFixed(1) + '%'
                    : 'N/A'}
                </div>
                <span className="text-[10px] text-slate-500">Inter-blink CV</span>
              </div>

              <div className="bg-slate-800/70 border border-slate-700/60 rounded-xl p-3.5">
                <span className="text-xs text-slate-400">Mean Blink Duration</span>
                <div className="text-xl font-bold text-slate-200 mt-1">
                  {features.blink_duration_mean !== null ? features.blink_duration_mean.toFixed(0) + ' ms' : 'N/A'}
                </div>
                <span className="text-[10px] text-slate-500">Closure duration</span>
              </div>

              <div className="bg-slate-800/70 border border-slate-700/60 rounded-xl p-3.5">
                <span className="text-xs text-slate-400">Total Count</span>
                <div className="text-xl font-bold text-slate-200 mt-1">
                  {features.blink_count}
                </div>
                <span className="text-[10px] text-slate-500">Blinks in 30 seconds</span>
              </div>
            </div>

            {/* Sync Feedback */}
            {syncStatus && (
              <div className={`p-3 rounded-lg text-xs flex items-center gap-2 ${
                syncStatus.ok
                  ? 'bg-emerald-950/40 border border-emerald-500/40 text-emerald-200'
                  : 'bg-rose-950/40 border border-rose-500/40 text-rose-200'
              }`}>
                {syncStatus.ok ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <AlertTriangle className="w-4 h-4 text-rose-400" />}
                <span>{syncStatus.message}</span>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="space-y-2 pt-2">
            {supabaseClient && !sessionModel?.synced && (
              <button
                onClick={handleSync}
                disabled={isSyncing}
                className="w-full py-3 px-4 rounded-xl bg-sky-600 hover:bg-sky-500 text-white font-medium text-sm flex items-center justify-center gap-2 shadow-lg shadow-sky-900/30 disabled:opacity-50 transition"
              >
                {isSyncing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <UploadCloud className="w-4 h-4" />}
                {isSyncing ? 'Syncing to Supabase...' : 'Sync Session to Supabase'}
              </button>
            )}

            <button
              onClick={() => {
                setPhase(PHASE.READY);
                setFeatures(null);
                setQualityResult(null);
                setSessionModel(null);
                setSyncStatus(null);
              }}
              className="w-full py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
            >
              Repeat Task
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
