import React, { useState, useEffect, useRef } from 'react';
import {
  Mic,
  Square,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  UploadCloud,
  ShieldCheck,
  Activity,
  Layers,
  Volume2,
  VolumeX,
  Info,
  Check,
  Clock,
  Sparkles
} from 'lucide-react';
import { VoiceRecorder, VOICE_TASKS } from './voiceRecorder.js';
import { VoiceFeatureExtractor } from './voiceFeatureExtractor.js';
import { VoiceQualityScorer } from './voiceQualityScorer.js';
import { VoiceSessionModel } from './voiceSessionModel.js';

/**
 * MPF Mobile Extension — Guided Voice Task Screen (Phase 5)
 * 
 * Conducts standardized, active acoustic biomarker collection across 3 guided tasks:
 * 1. Sustained vowel phonation (/a/)
 * 2. Standardized reading sentence
 * 3. Short spontaneous free speech
 * 
 * STRICT COMPLIANCE & PRIVACY:
 * - NO diagnostic claims ("Research screening result — not a clinical diagnosis").
 * - Baseline-centric analysis ("Measures deviation from personal baseline").
 * - Privacy-by-design: Raw audio is processed locally and discarded immediately.
 * - Raw audio upload is disabled by default.
 */
export function VoiceTaskScreen({ participantId, supabaseClient, onComplete, onCancel }) {
  const [selectedTaskKey, setSelectedTaskKey] = useState('SUSTAINED_VOWEL');
  const [sessionPhase, setSessionPhase] = useState('ready'); // 'ready' | 'recording' | 'processing' | 'completed'
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [liveAudioLevel, setLiveAudioLevel] = useState(0);
  const [extractedFeatures, setExtractedFeatures] = useState(null);
  const [qualityResult, setQualityResult] = useState(null);
  const [sessionModel, setSessionModel] = useState(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);

  const recorderRef = useRef(null);
  const timerRef = useRef(null);
  const animFrameRef = useRef(null);
  const audioElemRef = useRef(null);

  const currentTask = VOICE_TASKS[selectedTaskKey];

  // Initialize recorder on mount
  useEffect(() => {
    recorderRef.current = new VoiceRecorder({
      sampleRate: 44100,
      hasAudioStorageConsent: false // Strict privacy default
    });

    recorderRef.current.initialize().catch(err => {
      console.warn("VoiceRecorder init notice:", err);
    });

    return () => {
      if (recorderRef.current) {
        recorderRef.current.dispose();
      }
      if (timerRef.current) clearInterval(timerRef.current);
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    };
  }, []);

  // Update live audio meter while recording
  const updateMeter = () => {
    if (recorderRef.current && sessionPhase === 'recording') {
      const level = recorderRef.current.getLiveAudioLevel();
      setLiveAudioLevel(level);
      animFrameRef.current = requestAnimationFrame(updateMeter);
    }
  };

  // Start recording
  const handleStartRecording = async () => {
    try {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
        setAudioUrl(null);
      }
      setExtractedFeatures(null);
      setQualityResult(null);
      setSessionModel(null);
      setSyncStatus(null);
      setElapsedSeconds(0);

      const pId = participantId || '00000000-0000-0000-0000-000000000001';
      await recorderRef.current.startRecording(pId, currentTask.id);

      setSessionPhase('recording');

      // Start elapsed timer
      const startMs = Date.now();
      timerRef.current = setInterval(() => {
        const secs = Math.floor((Date.now() - startMs) / 1000);
        setElapsedSeconds(secs);

        // Auto-stop at max duration
        if (secs >= currentTask.maxDurationSeconds) {
          handleStopRecording();
        }
      }, 200);

      // Start live visualizer
      animFrameRef.current = requestAnimationFrame(updateMeter);
    } catch (err) {
      console.error("Failed to start voice recording:", err);
      alert(`Recording error: ${err.message}`);
    }
  };

  // Stop recording & extract features locally
  const handleStopRecording = async () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    setSessionPhase('processing');

    try {
      const result = await recorderRef.current.stopRecording();
      const { pcmBuffer, durationSeconds, sampleRate, sessionId, taskType } = result;

      // Extract acoustic and quality biomarkers locally
      const features = VoiceFeatureExtractor.extractFeatures(pcmBuffer, sampleRate);
      setExtractedFeatures(features);

      // Multi-factor quality scoring
      const quality = VoiceQualityScorer.calculateQualityScore({
        duration: durationSeconds,
        signal_quality: features.signal_quality,
        clipping_detected: features.clipping_detected,
        silence_ratio: features.silence_ratio,
        hnr: features.hnr
      });
      setQualityResult(quality);

      // Build validated VoiceSessionModel
      const pId = participantId || '00000000-0000-0000-0000-000000000001';
      const model = VoiceSessionModel.fromFeatures({
        participantId: pId,
        sessionId,
        taskType,
        features,
        qualityResult: quality
      });
      setSessionModel(model);

      // PRIVACY PURGE: Delete raw PCM audio buffer from memory
      recorderRef.current.discardRawAudio();

      setSessionPhase('completed');
    } catch (err) {
      console.error("Feature extraction error:", err);
      setSessionPhase('ready');
      alert(`Feature extraction failed: ${err.message}`);
    }
  };

  // Reset task
  const handleReset = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    if (recorderRef.current) recorderRef.current.discardRawAudio();
    setSessionPhase('ready');
    setElapsedSeconds(0);
    setLiveAudioLevel(0);
    setExtractedFeatures(null);
    setQualityResult(null);
    setSessionModel(null);
    setSyncStatus(null);
  };

  // Upload features to Supabase
  const handleSyncToSupabase = async () => {
    if (!sessionModel) return;
    setIsSyncing(true);
    setSyncStatus(null);

    try {
      const res = await sessionModel.syncToSupabase(supabaseClient);
      setSyncStatus(res);
      if (res.success && onComplete) {
        onComplete(sessionModel);
      }
    } catch (err) {
      setSyncStatus({ success: false, error: err.message });
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto p-4 sm:p-6 bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl text-slate-100 font-sans">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-5 border-b border-slate-800 gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 bg-indigo-500/10 text-indigo-400 rounded-lg">
              <Mic className="w-5 h-5" />
            </span>
            <h2 className="text-xl font-bold tracking-tight text-white">
              Acoustic Voice Biomarker Collection
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Standardized vocal stability and speech rhythm kinematics
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-medium rounded-full flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5" />
            On-Device Processing
          </span>
          <span className="px-3 py-1 bg-slate-800 text-slate-400 text-xs font-mono rounded-full">
            v1.0.0
          </span>
        </div>
      </div>

      {/* Strict Privacy & Clinical Protocol Alert */}
      <div className="mt-4 p-3 bg-indigo-950/40 border border-indigo-500/30 rounded-xl flex items-start gap-3">
        <Info className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
        <div className="text-xs text-indigo-200/90 leading-relaxed space-y-1">
          <p>
            <strong className="text-white">Privacy Guarantee:</strong> Raw audio is processed 100% locally on your device and discarded immediately. No audio clips or conversations are stored or uploaded.
          </p>
          <p className="text-indigo-300/80">
            <strong className="text-indigo-200">Clinical Protocol:</strong> Research screening result — not a clinical diagnosis. Evaluates progressive deviation from personal baseline.
          </p>
        </div>
      </div>

      {/* Task Selector Tabs */}
      {sessionPhase === 'ready' && (
        <div className="mt-6">
          <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">
            Select Daily Guided Speech Task
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {Object.entries(VOICE_TASKS).map(([key, task]) => {
              const isSelected = selectedTaskKey === key;
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => setSelectedTaskKey(key)}
                  className={`p-3.5 rounded-xl border text-left transition-all duration-200 flex flex-col justify-between ${
                    isSelected
                      ? 'bg-indigo-600/15 border-indigo-500 text-white shadow-lg shadow-indigo-500/10'
                      : 'bg-slate-800/40 border-slate-700/60 text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-bold text-slate-300">{task.title}</span>
                      {isSelected && <Check className="w-4 h-4 text-indigo-400" />}
                    </div>
                    <p className="text-xs text-slate-400 line-clamp-2">{task.instruction}</p>
                  </div>
                  <div className="mt-3 text-[11px] text-slate-500 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    ~{task.targetDurationSeconds}s duration
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Active Task Instruction Card */}
      <div className="mt-6 p-5 bg-slate-800/50 border border-slate-700/70 rounded-xl">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">
            {currentTask.title}
          </span>
          <span className="text-xs text-slate-400">
            Target: ~{currentTask.targetDurationSeconds}s ({currentTask.minDurationSeconds}s - {currentTask.maxDurationSeconds}s)
          </span>
        </div>
        <p className="text-base sm:text-lg font-medium text-slate-100 bg-slate-900/60 p-4 rounded-lg border border-slate-700/50">
          "{currentTask.instruction}"
        </p>
        <p className="text-xs text-slate-400 mt-2 flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          <span>Biomarker Objective: {currentTask.purpose}</span>
        </p>
      </div>

      {/* Recording Visualizer & Controls */}
      <div className="mt-6 p-6 bg-slate-950/60 border border-slate-800 rounded-xl flex flex-col items-center justify-center min-h-[220px]">
        {sessionPhase === 'ready' && (
          <div className="text-center space-y-4">
            <div className="w-20 h-20 rounded-full bg-indigo-600/20 border-2 border-indigo-500/40 flex items-center justify-center mx-auto text-indigo-400">
              <Mic className="w-9 h-9" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-200">
                Ready to record. Find a quiet room and speak naturally.
              </p>
              <p className="text-xs text-slate-500 mt-1">
                Tap start and follow the prompt instruction above.
              </p>
            </div>
            <button
              type="button"
              onClick={handleStartRecording}
              className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white font-medium text-sm rounded-xl transition-all duration-150 shadow-lg shadow-indigo-600/30 flex items-center gap-2 mx-auto"
            >
              <Mic className="w-4 h-4" />
              Start Recording
            </button>
          </div>
        )}

        {sessionPhase === 'recording' && (
          <div className="w-full text-center space-y-5">
            <div className="flex items-center justify-center gap-3">
              <span className="w-3 h-3 rounded-full bg-rose-500 animate-ping" />
              <span className="text-sm font-semibold text-rose-400 uppercase tracking-widest">
                Recording Active
              </span>
              <span className="text-lg font-mono font-bold text-white bg-slate-900 px-3 py-1 rounded-lg border border-slate-800">
                {elapsedSeconds}s / {currentTask.targetDurationSeconds}s
              </span>
            </div>

            {/* Live Audio Level Meter */}
            <div className="w-full max-w-md mx-auto space-y-1.5">
              <div className="h-3 w-full bg-slate-800 rounded-full overflow-hidden border border-slate-700/60 p-0.5">
                <div
                  className={`h-full rounded-full transition-all duration-75 ${
                    liveAudioLevel > 0.8
                      ? 'bg-rose-500'
                      : liveAudioLevel > 0.4
                      ? 'bg-indigo-500'
                      : 'bg-emerald-500'
                  }`}
                  style={{ width: `${Math.min(100, Math.max(5, liveAudioLevel * 100))}%` }}
                />
              </div>
              <div className="flex justify-between text-[11px] text-slate-500">
                <span>Mic Input Level</span>
                <span>{liveAudioLevel > 0.8 ? 'Peak Warning' : 'Optimal'}</span>
              </div>
            </div>

            <p className="text-xs text-slate-400 italic">
              Speak clearly: "{currentTask.instruction}"
            </p>

            <button
              type="button"
              onClick={handleStopRecording}
              className="px-6 py-2.5 bg-rose-600 hover:bg-rose-500 active:scale-95 text-white font-medium text-sm rounded-xl transition-all duration-150 shadow-lg shadow-rose-600/30 flex items-center gap-2 mx-auto"
            >
              <Square className="w-4 h-4 fill-white" />
              Finish Recording
            </button>
          </div>
        )}

        {sessionPhase === 'processing' && (
          <div className="text-center space-y-3 py-6">
            <Activity className="w-8 h-8 text-indigo-400 animate-spin mx-auto" />
            <p className="text-sm font-semibold text-slate-200">
              Extracting acoustic biomarkers on-device...
            </p>
            <p className="text-xs text-slate-500">
              Calculating fundamental pitch, cycle perturbation, and spectral features.
            </p>
          </div>
        )}

        {sessionPhase === 'completed' && extractedFeatures && (
          <div className="w-full space-y-6">
            {/* Quality Score Gating Card */}
            <div className={`p-4 rounded-xl border ${
              qualityResult?.is_baseline_eligible
                ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-200'
                : 'bg-amber-950/30 border-amber-500/40 text-amber-200'
            }`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {qualityResult?.is_baseline_eligible ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-amber-400" />
                  )}
                  <span className="text-sm font-bold text-white">
                    {qualityResult?.is_baseline_eligible
                      ? 'Valid Acoustic Recording'
                      : 'Quality Below Baseline Threshold'}
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-lg font-mono font-bold text-white">
                    {(qualityResult?.quality_score * 100).toFixed(0)}%
                  </span>
                  <span className="text-xs text-slate-400 block">Quality Score</span>
                </div>
              </div>

              {/* Quality Criteria Breakdown */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3 pt-3 border-t border-slate-700/50 text-xs">
                <div>
                  <span className="text-slate-400 block">Duration (&gt;3s)</span>
                  <span className="font-semibold text-white">
                    {extractedFeatures.duration}s (+{qualityResult?.breakdown.sufficient_duration.toFixed(2)})
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block">Signal Quality</span>
                  <span className="font-semibold text-white">
                    {(extractedFeatures.signal_quality * 100).toFixed(0)}% (+{qualityResult?.breakdown.good_snr.toFixed(2)})
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block">No Clipping</span>
                  <span className="font-semibold text-white">
                    {extractedFeatures.clipping_detected ? 'Clipping (-0.2)' : 'Clean (+0.2)'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block">Silence (&lt;30%)</span>
                  <span className="font-semibold text-white">
                    {(extractedFeatures.silence_ratio * 100).toFixed(0)}% (+{qualityResult?.breakdown.low_silence.toFixed(2)})
                  </span>
                </div>
              </div>

              {!qualityResult?.is_baseline_eligible && (
                <p className="text-xs text-amber-300 mt-2 bg-amber-950/60 p-2 rounded">
                  Note: This recording scored &lt; 0.50 and will not update your 14-day personal baseline.
                </p>
              )}
            </div>

            {/* Acoustic Features Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg">
                <span className="text-[11px] text-slate-500 uppercase tracking-wider block">Pitch Mean (F0)</span>
                <span className="text-base font-mono font-bold text-white">
                  {extractedFeatures.pitch_mean} <span className="text-xs text-slate-400">Hz</span>
                </span>
              </div>
              <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg">
                <span className="text-[11px] text-slate-500 uppercase tracking-wider block">Pitch Std Dev</span>
                <span className="text-base font-mono font-bold text-white">
                  {extractedFeatures.pitch_std} <span className="text-xs text-slate-400">Hz</span>
                </span>
              </div>
              <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg">
                <span className="text-[11px] text-slate-500 uppercase tracking-wider block">Harmonics-to-Noise</span>
                <span className="text-base font-mono font-bold text-white">
                  {extractedFeatures.hnr} <span className="text-xs text-slate-400">dB</span>
                </span>
              </div>
              <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg">
                <span className="text-[11px] text-slate-500 uppercase tracking-wider block">Jitter (Period Var)</span>
                <span className="text-base font-mono font-bold text-white">
                  {(extractedFeatures.jitter * 100).toFixed(3)}%
                </span>
              </div>
              <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg">
                <span className="text-[11px] text-slate-500 uppercase tracking-wider block">Shimmer (Amp Var)</span>
                <span className="text-base font-mono font-bold text-white">
                  {(extractedFeatures.shimmer * 100).toFixed(3)}%
                </span>
              </div>
              <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg">
                <span className="text-[11px] text-slate-500 uppercase tracking-wider block">Spectral Centroid</span>
                <span className="text-base font-mono font-bold text-white">
                  {extractedFeatures.spectral_features.spectral_centroid} <span className="text-xs text-slate-400">Hz</span>
                </span>
              </div>
            </div>

            {/* Action Buttons: Reset & Sync */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-slate-800">
              <button
                type="button"
                onClick={handleReset}
                className="w-full sm:w-auto px-4 py-2 border border-slate-700 hover:bg-slate-800 text-slate-300 text-xs font-semibold rounded-xl flex items-center justify-center gap-1.5 transition-all"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Record Again
              </button>

              <div className="w-full sm:w-auto flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleSyncToSupabase}
                  disabled={isSyncing || sessionModel?.synced}
                  className={`w-full sm:w-auto px-5 py-2.5 font-semibold text-xs rounded-xl flex items-center justify-center gap-2 transition-all ${
                    sessionModel?.synced
                      ? 'bg-emerald-600/30 text-emerald-300 border border-emerald-500/40 cursor-default'
                      : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/25 active:scale-95'
                  }`}
                >
                  <UploadCloud className="w-4 h-4" />
                  {isSyncing ? 'Uploading Features...' : sessionModel?.synced ? 'Features Uploaded' : 'Sync Features to Cloud'}
                </button>
              </div>
            </div>

            {/* Sync Feedback Message */}
            {syncStatus && (
              <div className={`p-3 rounded-lg text-xs flex items-center gap-2 ${
                syncStatus.success
                  ? 'bg-emerald-950/40 border border-emerald-500/30 text-emerald-300'
                  : 'bg-rose-950/40 border border-rose-500/30 text-rose-300'
              }`}>
                {syncStatus.success ? (
                  <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                ) : (
                  <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
                )}
                <span>{syncStatus.message || syncStatus.error || "Sync status updated."}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
