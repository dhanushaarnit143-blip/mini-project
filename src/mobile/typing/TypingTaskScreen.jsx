import React, { useState, useEffect, useRef } from 'react';
import { 
  Keyboard, 
  ShieldCheck, 
  CheckCircle2, 
  AlertTriangle, 
  RotateCcw, 
  UploadCloud, 
  Clock, 
  Zap, 
  Activity, 
  Layers, 
  Info,
  Check,
  XCircle
} from 'lucide-react';
import { TypingCollector, TARGET_PHRASE } from './typingCollector.js';
import { TypingFeatureExtractor } from './typingFeatureExtractor.js';
import { TypingQualityScorer } from './typingQualityScorer.js';
import { TypingSessionModel } from './typingSessionModel.js';

/**
 * MPF Mobile Extension — Controlled Typing Task Screen
 * 
 * Conducts a standardized, active typing kinematics test using a pangram phrase.
 * 
 * STRICT COMPLIANCE:
 * - NO diagnostic claims ("Research screening result — not a clinical diagnosis").
 * - Baseline-centric analysis ("Measures deviation from personal baseline").
 * - Privacy-by-design: Character text is NEVER stored or transmitted.
 */
export function TypingTaskScreen({ participantId, supabaseClient, onComplete, onCancel }) {
  const [sessionPhase, setSessionPhase] = useState('ready'); // 'ready' | 'typing' | 'completed'
  const [typedText, setTypedText] = useState('');
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState(null); // { success, message, idempotent }
  const [extractedFeatures, setExtractedFeatures] = useState(null);
  const [qualityResult, setQualityResult] = useState(null);
  const [sessionModel, setSessionModel] = useState(null);

  const collectorRef = useRef(new TypingCollector());
  const inputRef = useRef(null);

  // Auto-focus input when entering typing phase
  useEffect(() => {
    if (sessionPhase === 'typing' && inputRef.current) {
      inputRef.current.focus();
    }
  }, [sessionPhase]);

  // Handle task initiation
  const handleStartTask = () => {
    try {
      collectorRef.current.startSession(participantId || '00000000-0000-0000-0000-000000000001');
      setTypedText('');
      setSyncStatus(null);
      setExtractedFeatures(null);
      setQualityResult(null);
      setSessionModel(null);
      setSessionPhase('typing');
    } catch (err) {
      console.error("Failed to start session:", err);
    }
  };

  // Keyboard Event Handlers (Timing capture ONLY)
  const handleKeyDown = (e) => {
    if (sessionPhase !== 'typing') return;
    collectorRef.current.recordKeyDown(e);
  };

  const handleKeyUp = (e) => {
    if (sessionPhase !== 'typing') return;
    collectorRef.current.recordKeyUp(e);
  };

  // Controlled input change: purely for character progression verification
  const handleInputChange = (e) => {
    if (sessionPhase !== 'typing') return;
    const val = e.target.value;
    
    // Only accept characters up to target phrase length
    if (val.length <= TARGET_PHRASE.length) {
      setTypedText(val);

      // Check for completion
      if (val === TARGET_PHRASE) {
        finishTask(true);
      }
    }
  };

  const finishTask = (completed = true) => {
    try {
      const rawSession = collectorRef.current.endSession(completed);
      const features = TypingFeatureExtractor.extractFeatures(rawSession);
      const quality = TypingQualityScorer.calculateQualityScore({
        completed: rawSession.completed,
        timingEvents: rawSession.timingEvents,
        typingSpeed: features.typing_speed,
        keystrokeCount: rawSession.keystrokeCount,
        correctionCount: features.correction_count
      });

      const model = TypingSessionModel.fromFeatures({
        participantId: rawSession.participantId,
        sessionId: rawSession.sessionId,
        features,
        qualityResult: quality
      });

      setExtractedFeatures(features);
      setQualityResult(quality);
      setSessionModel(model);
      setSessionPhase('completed');
    } catch (err) {
      console.error("Error finalizing typing task:", err);
    }
  };

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
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between p-6 max-w-2xl mx-auto font-sans">
      {/* Top Header */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-400">
              <Keyboard className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white">Keyboard Dynamics Task</h1>
              <p className="text-xs text-slate-400">Motor-Cognitive Rhythm Biomarker Module</p>
            </div>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
            Phase 4
          </span>
        </div>

        {/* Prominent Research Disclaimer */}
        <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-start gap-2.5">
          <Info className="w-4 h-4 mt-0.5 shrink-0" />
          <div>
            <p className="font-semibold">Research screening result — not a clinical diagnosis.</p>
            <p className="text-amber-200/80 mt-0.5">
              Kinematic observations quantify deviation from your personal 14-day baseline. No medical determination is made.
            </p>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="my-auto py-6">
        {sessionPhase === 'ready' && (
          <div className="space-y-6 text-center">
            <div className="w-16 h-16 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mx-auto shadow-inner">
              <Keyboard className="w-8 h-8" />
            </div>

            <div className="space-y-2 max-w-md mx-auto">
              <h2 className="text-lg font-semibold text-slate-100">Standardized Controlled Phrase</h2>
              <p className="text-sm text-slate-400 leading-relaxed">
                You will be asked to type a short phrase at your natural pace. Type continuously without hurrying.
              </p>
            </div>

            {/* Target Phrase Preview */}
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 font-mono text-sm max-w-md mx-auto tracking-wide">
              "{TARGET_PHRASE}"
            </div>

            {/* Privacy Badge */}
            <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center justify-center gap-2 max-w-md mx-auto">
              <ShieldCheck className="w-4 h-4" />
              <span>Zero Text Captured: Keystroke text is never stored or uploaded.</span>
            </div>

            <button
              onClick={handleStartTask}
              className="w-full max-w-md mx-auto py-3.5 px-6 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium shadow-lg shadow-indigo-600/25 transition-all flex items-center justify-center gap-2"
            >
              <Zap className="w-4 h-4" />
              <span>Begin Controlled Typing Task</span>
            </button>
          </div>
        )}

        {sessionPhase === 'typing' && (
          <div className="space-y-6">
            {/* Phrase Display with Character Matching Feedback */}
            <div className="p-6 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-xl backdrop-blur">
              <div className="text-xs uppercase tracking-wider text-slate-400 font-semibold mb-3 flex items-center justify-between">
                <span>Target Phrase</span>
                <span>{typedText.length} / {TARGET_PHRASE.length} chars</span>
              </div>

              <div className="text-lg sm:text-xl font-mono leading-relaxed tracking-wider break-words select-none">
                {TARGET_PHRASE.split('').map((char, index) => {
                  let charClass = "text-slate-500";
                  if (index < typedText.length) {
                    charClass = typedText[index] === char 
                      ? "text-emerald-400 bg-emerald-500/10 rounded px-0.5" 
                      : "text-rose-400 bg-rose-500/10 rounded px-0.5";
                  } else if (index === typedText.length) {
                    charClass = "text-indigo-400 border-b-2 border-indigo-400 animate-pulse";
                  }

                  return (
                    <span key={index} className={charClass}>
                      {char}
                    </span>
                  );
                })}
              </div>
            </div>

            {/* In-App Typing Input (Discards character storage) */}
            <div className="space-y-2">
              <label className="text-xs text-slate-400 font-medium flex items-center justify-between">
                <span>Type in the field below:</span>
                <span className="text-emerald-400/90 text-[11px] flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3" /> Timing Kinematics Active
                </span>
              </label>

              <input
                ref={inputRef}
                type="text"
                value={typedText}
                onKeyDown={handleKeyDown}
                onKeyUp={handleKeyUp}
                onChange={handleInputChange}
                autoComplete="off"
                autoCorrect="off"
                autoCapitalize="off"
                spellCheck="false"
                placeholder="Type here..."
                className="w-full py-3.5 px-4 rounded-xl bg-slate-900 border border-indigo-500/50 text-white font-mono text-base focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all placeholder:text-slate-600"
              />
            </div>

            <div className="flex justify-between items-center text-xs text-slate-500">
              <span>Press Backspace to correct mistakes naturally.</span>
              <button 
                onClick={() => finishTask(false)}
                className="text-slate-400 hover:text-slate-300 underline"
              >
                End Early
              </button>
            </div>
          </div>
        )}

        {sessionPhase === 'completed' && extractedFeatures && qualityResult && (
          <div className="space-y-6">
            <div className="text-center space-y-2">
              <div className={`w-14 h-14 rounded-full mx-auto flex items-center justify-center border shadow-lg ${
                qualityResult.is_baseline_eligible 
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' 
                  : 'bg-amber-500/10 border-amber-500/30 text-amber-400'
              }`}>
                {qualityResult.is_baseline_eligible ? (
                  <CheckCircle2 className="w-7 h-7" />
                ) : (
                  <AlertTriangle className="w-7 h-7" />
                )}
              </div>

              <h2 className="text-xl font-bold text-white">Task Completed</h2>
              <p className="text-xs text-slate-400">Keystroke timing kinematics extracted successfully</p>
            </div>

            {/* Quality Score Gauge Card */}
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-300 uppercase tracking-wide">
                  Session Quality Score
                </span>
                <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                  qualityResult.is_baseline_eligible 
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' 
                    : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                }`}>
                  {qualityResult.is_baseline_eligible ? 'Eligible for Personal Baseline' : 'Sub-Threshold (<0.50)'}
                </span>
              </div>

              <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden">
                <div 
                  className={`h-full rounded-full transition-all duration-500 ${
                    qualityResult.is_baseline_eligible ? 'bg-emerald-500' : 'bg-amber-500'
                  }`}
                  style={{ width: `${Math.round(qualityResult.quality_score * 100)}%` }}
                />
              </div>

              <div className="flex justify-between text-xs text-slate-400">
                <span>Score: <strong className="text-white">{qualityResult.quality_score}</strong> / 1.00</span>
                <span>Minimum Gate: 0.50</span>
              </div>

              {qualityResult.rejection_reasons.length > 0 && !qualityResult.is_baseline_eligible && (
                <div className="text-[11px] text-amber-300/90 bg-amber-500/10 p-2 rounded border border-amber-500/20">
                  Notice: {qualityResult.rejection_reasons.join(", ")}
                </div>
              )}
            </div>

            {/* Extracted Kinematics Metrics Grid */}
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800/80">
                <div className="text-slate-400 flex items-center gap-1.5 mb-1">
                  <Zap className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Typing Speed</span>
                </div>
                <div className="text-base font-semibold text-white">
                  {extractedFeatures.typing_speed} <span className="text-xs font-normal text-slate-400">chars/s</span>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800/80">
                <div className="text-slate-400 flex items-center gap-1.5 mb-1">
                  <Clock className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Mean IKI</span>
                </div>
                <div className="text-base font-semibold text-white">
                  {extractedFeatures.mean_inter_key_interval} <span className="text-xs font-normal text-slate-400">ms</span>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800/80">
                <div className="text-slate-400 flex items-center gap-1.5 mb-1">
                  <Activity className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Rhythm Variability</span>
                </div>
                <div className="text-base font-semibold text-white">
                  {extractedFeatures.rhythm_variability} <span className="text-xs font-normal text-slate-400">(CV)</span>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800/80">
                <div className="text-slate-400 flex items-center gap-1.5 mb-1">
                  <Layers className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Pause Rate</span>
                </div>
                <div className="text-base font-semibold text-white">
                  {extractedFeatures.pause_rate} <span className="text-xs font-normal text-slate-400">/min</span>
                </div>
              </div>
            </div>

            {/* Sync Feedback */}
            {syncStatus && (
              <div className={`p-3 rounded-xl text-xs flex items-center gap-2 border ${
                syncStatus.success 
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' 
                  : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
              }`}>
                {syncStatus.success ? <Check className="w-4 h-4 shrink-0" /> : <XCircle className="w-4 h-4 shrink-0" />}
                <span>
                  {syncStatus.message || (syncStatus.success ? "Session synchronized with Supabase." : syncStatus.error)}
                </span>
              </div>
            )}

            {/* Action Buttons */}
            <div className="space-y-2 pt-2">
              <button
                onClick={handleSyncToSupabase}
                disabled={isSyncing || (syncStatus && syncStatus.success)}
                className={`w-full py-3 px-4 rounded-xl font-medium text-sm flex items-center justify-center gap-2 transition-all ${
                  syncStatus?.success
                    ? 'bg-slate-800 text-emerald-400 border border-emerald-500/30'
                    : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/20 disabled:opacity-60'
                }`}
              >
                <UploadCloud className="w-4 h-4" />
                <span>
                  {isSyncing ? "Uploading Kinematics..." : syncStatus?.success ? "Synchronized" : "Save & Sync to Supabase"}
                </span>
              </button>

              <button
                onClick={handleStartTask}
                className="w-full py-2.5 px-4 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 font-medium text-xs flex items-center justify-center gap-2 border border-slate-800 transition-all"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Retake Task</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Footer Privacy Guarantee */}
      <div className="pt-4 border-t border-slate-900 text-center">
        <div className="flex items-center justify-center gap-1.5 text-[11px] text-slate-500">
          <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
          <span>Zero Text Retention • Keystroke Timing Only • Client UUID Idempotency</span>
        </div>
      </div>
    </div>
  );
}

export default TypingTaskScreen;
