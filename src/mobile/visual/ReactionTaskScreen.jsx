import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Zap,
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
  Target,
} from 'lucide-react';
import { FaceLandmarkDetector } from './faceLandmarkDetector.js';
import { extractReactionFeatures } from './visualFeatureExtractor.js';
import { VisualQualityScorer } from './visualQualityScorer.js';
import { VisualSessionModel, VISUAL_TASK_TYPES } from './visualSessionModel.js';

/**
 * MPF Mobile Extension — Visual Reaction Time Task Screen (Phase 7)
 *
 * Task 3: Guided visual reaction time.
 * Instruction: "Tap the screen when you see the target appear."
 *
 * CRITICAL PRIVACY & CLINICAL COMPLIANCE:
 * - "Ocular/Visual Behavior Module" — NOT retinal imaging.
 * - Video stream is processed in-memory locally.
 * - ZERO video recordings or facial images stored or uploaded.
 * - Camera active ONLY during the active task window.
 * - "Research screening result — not a clinical diagnosis."
 * - "Deviation from personal baseline."
 */

const TASK_DURATION_SEC = 25;
const TARGET_PRESENTATIONS_GOAL = 8;
const MIN_INTERVAL_DELAY_MS = 1500;
const MAX_INTERVAL_DELAY_MS = 3500;
const STIMULUS_TIMEOUT_MS   = 2000;

const PHASE = {
  READY:      'ready',
  WAITING:    'waiting',     // Inter-stimulus interval (no target visible)
  STIMULUS:   'stimulus',    // Target visible on screen awaiting tap
  PROCESSING: 'processing',
  RESULTS:    'results',
};

export function ReactionTaskScreen({ participantId, supabaseClient, onComplete, onCancel }) {
  const [phase, setPhase]                 = useState(PHASE.READY);
  const [elapsed, setElapsed]             = useState(0);
  const [targetPos, setTargetPos]         = useState({ x: 50, y: 50 });
  const [targetCount, setTargetCount]     = useState(0);
  const [lastReactionMs, setLastReactionMs] = useState(null);
  const [features, setFeatures]           = useState(null);
  const [qualityResult, setQualityResult] = useState(null);
  const [sessionModel, setSessionModel]   = useState(null);
  const [isSyncing, setIsSyncing]         = useState(false);
  const [syncStatus, setSyncStatus]       = useState(null);
  const [cameraActive, setCameraActive]   = useState(false);
  const [permissionError, setPermissionError] = useState(null);

  const detectorRef       = useRef(null);
  const eventsRef         = useRef([]);
  const timerRef          = useRef(null);
  const timeoutRef        = useRef(null);
  const stimulusTimerRef  = useRef(null);
  const startMsRef        = useRef(null);
  const stimulusStartMsRef= useRef(null);
  const completedTargetsRef = useRef(0);

  // Quality tracking accumulators
  const faceDetectedCountRef = useRef(0);
  const goodLightingCountRef = useRef(0);
  const totalFramesRef       = useRef(0);
  const confidencesRef       = useRef([]);
  const headDisplacementsRef = useRef([]);

  useEffect(() => {
    detectorRef.current = new FaceLandmarkDetector();
    return () => {
      _cleanupResources();
    };
  }, []);

  const _cleanupResources = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    if (stimulusTimerRef.current) clearTimeout(stimulusTimerRef.current);
    if (detectorRef.current) detectorRef.current.dispose();
  };

  const scheduleNextStimulus = useCallback(() => {
    if (completedTargetsRef.current >= TARGET_PRESENTATIONS_GOAL) {
      finishTask();
      return;
    }

    setPhase(PHASE.WAITING);

    const delayMs = MIN_INTERVAL_DELAY_MS +
      Math.random() * (MAX_INTERVAL_DELAY_MS - MIN_INTERVAL_DELAY_MS);

    timeoutRef.current = setTimeout(() => {
      presentStimulus();
    }, delayMs);
  }, []);

  const presentStimulus = useCallback(() => {
    // Generate pseudo-random stimulus coordinates within safe bounds (20% - 80%)
    const posX = Math.round(20 + Math.random() * 60);
    const posY = Math.round(25 + Math.random() * 50);
    setTargetPos({ x: posX, y: posY });

    stimulusStartMsRef.current = performance.now();
    setPhase(PHASE.STIMULUS);

    // Timeout if participant does not tap within 2000 ms
    stimulusTimerRef.current = setTimeout(() => {
      eventsRef.current.push({
        stimulusTimeMs: stimulusStartMsRef.current,
        responseTimeMs: null,
        tapped: false,
        timeout: true,
      });
      completedTargetsRef.current++;
      setTargetCount(completedTargetsRef.current);
      scheduleNextStimulus();
    }, STIMULUS_TIMEOUT_MS);
  }, [scheduleNextStimulus]);

  const handleTap = useCallback((e) => {
    e?.stopPropagation();
    if (phase !== PHASE.STIMULUS) return;

    if (stimulusTimerRef.current) {
      clearTimeout(stimulusTimerRef.current);
    }

    const tapTime = performance.now();
    const rt = Math.round(tapTime - stimulusStartMsRef.current);
    setLastReactionMs(rt);

    eventsRef.current.push({
      stimulusTimeMs: stimulusStartMsRef.current,
      responseTimeMs: tapTime,
      tapped: true,
      timeout: false,
    });

    completedTargetsRef.current++;
    setTargetCount(completedTargetsRef.current);
    scheduleNextStimulus();
  }, [phase, scheduleNextStimulus]);

  const handleStart = useCallback(async () => {
    setPermissionError(null);
    eventsRef.current = [];
    faceDetectedCountRef.current = 0;
    goodLightingCountRef.current = 0;
    totalFramesRef.current = 0;
    confidencesRef.current = [];
    headDisplacementsRef.current = [];
    completedTargetsRef.current = 0;
    setTargetCount(0);
    setLastReactionMs(null);

    const detector = detectorRef.current;
    const perm = await detector.requestPermissionAndStart((landmark) => {
      totalFramesRef.current++;
      if (landmark.faceDetected) faceDetectedCountRef.current++;
      if (landmark.lighting?.isAcceptable) goodLightingCountRef.current++;
      if (landmark.confidence) confidencesRef.current.push(landmark.confidence);
      if (landmark.headPose?.displacement) headDisplacementsRef.current.push(landmark.headPose.displacement);
    });

    if (!perm.granted) {
      setPermissionError(perm.error || 'Camera permission required.');
      return;
    }

    setCameraActive(true);
    setPhase(PHASE.WAITING);
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

    scheduleNextStimulus();
  }, [scheduleNextStimulus]);

  const finishTask = useCallback(() => {
    setPhase(PHASE.PROCESSING);

    _cleanupResources();
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
      taskType: 'reaction',
      actualDurationSec,
      targetDurationSec: TASK_DURATION_SEC,
      faceDetectedRatio: faceRatio,
      goodLightingRatio: lightRatio,
      meanConfidence: avgConf,
      headDisplacement: avgHeadDisp,
    });

    const feat = extractReactionFeatures(eventsRef.current, actualDurationMs);

    let model = null;
    if (participantId) {
      try {
        model = VisualSessionModel.fromReaction({
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
    finishTask();
  };

  const handleSync = async () => {
    if (!sessionModel || !supabaseClient) return;
    setIsSyncing(true);
    setSyncStatus(null);
    const res = await sessionModel.syncToSupabase(supabaseClient);
    setIsSyncing(false);
    if (res.success) {
      setSyncStatus({ ok: true, message: 'Reaction time metrics successfully synced.' });
      if (onComplete) onComplete(sessionModel);
    } else {
      setSyncStatus({ ok: false, message: res.error?.message || 'Sync failed.' });
    }
  };

  const progressPercent = Math.min(100, Math.round((targetCount / TARGET_PRESENTATIONS_GOAL) * 100));

  return (
    <div className="flex flex-col min-h-screen bg-slate-900 text-slate-100 p-4 max-w-xl mx-auto font-sans select-none">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
        <div className="flex items-center gap-2">
          <Zap className="w-6 h-6 text-amber-400" />
          <div>
            <h1 className="text-lg font-semibold text-white tracking-wide">
              Visual Reaction Task
            </h1>
            <p className="text-xs text-slate-400">
              Ocular/Visual Behavior Module • Speed & Consistency
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
          Visual reaction time reflects behavioral sensorimotor latency, <strong>NOT retinal imaging</strong>. Video is processed in-memory only.
        </div>
      </div>

      {/* Main Interactive Stage */}
      {phase === PHASE.READY && (
        <div className="flex-1 flex flex-col justify-center items-center text-center px-4 py-8">
          <div className="w-20 h-20 rounded-full bg-amber-500/10 border-2 border-amber-500/30 flex items-center justify-center mb-6">
            <Zap className="w-10 h-10 text-amber-400" />
          </div>
          <h2 className="text-xl font-bold text-white mb-2">Tap When Target Appears</h2>
          <p className="text-sm text-slate-300 mb-6 max-w-sm">
            Hold your device with your dominant hand ready. Whenever a target flashes on the screen, tap it as quickly as possible.
          </p>

          <div className="bg-slate-800/60 rounded-lg p-3 text-xs text-slate-400 mb-6 max-w-sm text-left space-y-1.5 border border-slate-700/50">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span>Camera monitors head stability and lighting only</span>
            </div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span>Zero facial recordings or images captured</span>
            </div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span>Extracts mean latency and response variability</span>
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
              className="flex-1 py-3 px-4 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-medium text-sm flex items-center justify-center gap-2 shadow-lg shadow-amber-900/30 transition"
            >
              <Play className="w-4 h-4 fill-current" />
              Start Task
            </button>
          </div>
        </div>
      )}

      {(phase === PHASE.WAITING || phase === PHASE.STIMULUS) && (
        <div className="flex-1 flex flex-col">
          {/* Progress / Status Header */}
          <div className="mb-3">
            <div className="flex justify-between items-center text-xs text-slate-400 mb-1.5">
              <span>
                {phase === PHASE.STIMULUS ? 'TAP NOW!' : 'Get ready...'}
              </span>
              <span className="font-mono text-amber-400 font-semibold">
                Target {targetCount} / {TARGET_PRESENTATIONS_GOAL}
              </span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
              <div
                className="bg-amber-500 h-1.5 transition-all duration-200"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>

          {/* Interactive Tap Stage */}
          <div
            onClick={phase === PHASE.STIMULUS ? handleTap : undefined}
            className={`flex-1 relative bg-slate-950 border border-slate-800 rounded-xl overflow-hidden min-h-[340px] flex items-center justify-center cursor-pointer transition-colors duration-100 ${
              phase === PHASE.STIMULUS ? 'bg-amber-950/20 border-amber-500/40' : ''
            }`}
          >
            {phase === PHASE.WAITING && (
              <div className="text-center text-slate-500">
                <Target className="w-8 h-8 mx-auto opacity-30 animate-pulse" />
                <span className="text-xs mt-2 block">Watch for the target...</span>
              </div>
            )}

            {phase === PHASE.STIMULUS && (
              <button
                onClick={handleTap}
                style={{
                  left: `${targetPos.x}%`,
                  top: `${targetPos.y}%`,
                  transform: 'translate(-50%, -50%)',
                }}
                className="absolute w-20 h-20 rounded-full bg-amber-400 hover:bg-amber-300 shadow-[0_0_32px_rgba(251,191,36,0.9)] border-4 border-white flex items-center justify-center animate-ping"
              >
                <Zap className="w-8 h-8 text-slate-950 fill-current" />
              </button>
            )}

            {lastReactionMs !== null && phase === PHASE.WAITING && (
              <div className="absolute top-4 left-0 right-0 text-center">
                <span className="text-xs font-mono font-bold text-amber-300 bg-slate-900/90 px-3 py-1 rounded-full border border-amber-500/30">
                  Last tap: {lastReactionMs} ms
                </span>
              </div>
            )}
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
          <RefreshCw className="w-8 h-8 text-amber-400 animate-spin mb-3" />
          <h3 className="text-base font-semibold text-white">Evaluating Reaction Dynamics</h3>
          <p className="text-xs text-slate-400 max-w-xs mt-1">
            Analyzing response latency and consistency.
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
                  ? 'Reaction times meet protocol inclusion criteria.'
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

            {/* Primary Extracted Reaction Biomarkers */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-slate-800/70 border border-slate-700/60 rounded-xl p-3.5">
                <span className="text-xs text-slate-400">Mean Reaction Time</span>
                <div className="text-xl font-bold text-amber-400 mt-1">
                  {features.reaction_time_mean !== null ? features.reaction_time_mean.toFixed(0) + ' ms' : 'N/A'}
                </div>
                <span className="text-[10px] text-slate-500">Sensorimotor latency</span>
              </div>

              <div className="bg-slate-800/70 border border-slate-700/60 rounded-xl p-3.5">
                <span className="text-xs text-slate-400">Response Variability</span>
                <div className="text-xl font-bold text-amber-400 mt-1">
                  {features.reaction_time_variability !== null
                    ? (features.reaction_time_variability * 100).toFixed(1) + '%'
                    : 'N/A'}
                </div>
                <span className="text-[10px] text-slate-500">Latency CV</span>
              </div>

              <div className="bg-slate-800/70 border border-slate-700/60 rounded-xl p-3.5">
                <span className="text-xs text-slate-400">Missed Targets</span>
                <div className="text-xl font-bold text-slate-200 mt-1">
                  {features.missed_targets}
                </div>
                <span className="text-[10px] text-slate-500">Timed out (&gt;2.0s)</span>
              </div>

              <div className="bg-slate-800/70 border border-slate-700/60 rounded-xl p-3.5">
                <span className="text-xs text-slate-400">Completed Targets</span>
                <div className="text-xl font-bold text-slate-200 mt-1">
                  {features.valid_responses} / {features.total_targets}
                </div>
                <span className="text-[10px] text-slate-500">Valid response count</span>
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
                className="w-full py-3 px-4 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-medium text-sm flex items-center justify-center gap-2 shadow-lg shadow-amber-900/30 disabled:opacity-50 transition"
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
