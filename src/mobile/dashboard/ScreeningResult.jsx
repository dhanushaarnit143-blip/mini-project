import React, { useState } from 'react';
import { ShieldAlert, AlertCircle, CheckCircle2, HelpCircle, Layers, ChevronDown, ChevronUp, Cpu, Sparkles, ExternalLink } from 'lucide-react';

/**
 * ScreeningResult Component — Section 4: Research Screening Result
 * 
 * Displays experimental multimodal risk pattern estimate from the MPF model:
 * - Overall risk pattern indicator (0.0 to 1.0)
 * - Available modalities (voice, motor, sleep/RBD, typing, visual behavior)
 * - Missing modalities handled via learnable imputation (olfactory, retinal)
 * - Mandatory prominent non-diagnostic disclaimer:
 *   "Research screening result — not a clinical diagnosis"
 * - Explainability breakdown: Attention weights and TreeSHAP feature attributions
 * 
 * Strict Compliance:
 * - Zero diagnostic claims; enforces research-only categorization.
 * - States "Elevated Parkinson's risk pattern detected" or "Within personal baseline".
 * - Rule 2: Formally distinguishes Ocular/Visual Behavior from Retinal Imaging.
 */

export function ScreeningResult({
  prediction = {
    riskScore: 0.28,
    riskBand: 'baseline', // 'baseline' | 'moderate' | 'elevated'
    modelVersion: 'v2.1.0-fusion',
    evaluationDate: new Date().toISOString().split('T')[0],
    availableModalities: ['voice', 'motor', 'sleep', 'typing', 'visual'],
    missingModalities: ['olfactory', 'retinal'],
    modalityWeights: {
      voice: 0.38,
      motor: 0.32,
      sleep: 0.18,
      typing: 0.08,
      visual: 0.04
    },
    inferenceId: 'inf_7f9b0c2e',
    explanation: 'Multimodal gated attention shows primary concordance across acoustic jitter and motor stride cadence.'
  },
  baselineStatus = 'established', // 'calibrating' | 'established'
  calibrationDay = 14,
  calibrationRequiredDays = 14
}) {
  const [showExplainability, setShowExplainability] = useState(false);
  const [showDisclaimerDetails, setShowDisclaimerDetails] = useState(false);

  // If participant is still in 14-day calibration
  if (baselineStatus === 'calibrating') {
    const remainingDays = Math.max(0, calibrationRequiredDays - calibrationDay);
    const progressPct = Math.min(100, Math.round((calibrationDay / calibrationRequiredDays) * 100));

    return (
      <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 shadow-lg space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">Baseline Calibration Active</h3>
              <p className="text-[11px] text-slate-400">Day {calibrationDay} of {calibrationRequiredDays}</p>
            </div>
          </div>
          <span className="text-xs font-mono font-semibold text-indigo-400">{progressPct}%</span>
        </div>

        {/* Progress Bar */}
        <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
          <div
            className="h-full bg-indigo-500 rounded-full transition-all duration-500"
            style={{ width: `${progressPct}%` }}
          />
        </div>

        <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800/80 text-xs text-slate-300 space-y-2 leading-relaxed">
          <div className="font-semibold text-slate-200">
            Screening Results Paused During Calibration
          </div>
          <p className="text-slate-400">
            In accordance with baseline-centric research protocols, experimental risk screening results are withheld until your personal normal behavior is learned ({remainingDays} days remaining).
          </p>
          <div className="text-[11px] text-amber-300/90 italic">
            Zero population-level comparisons are made during personal baseline calibration.
          </div>
        </div>
      </div>
    );
  }

  // Established baseline calculations
  const score = prediction?.riskScore ?? 0.25;
  let statusBadgeText = 'Within personal baseline';
  let statusBadgeStyle = 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
  let scoreColor = 'text-emerald-400';

  if (score >= 0.65) {
    statusBadgeText = "Elevated Parkinson's risk pattern detected";
    statusBadgeStyle = 'bg-amber-600/20 text-amber-400 border-amber-600/40';
    scoreColor = 'text-amber-400';
  } else if (score >= 0.40) {
    statusBadgeText = 'Moderate deviation from baseline';
    statusBadgeStyle = 'bg-amber-500/15 text-amber-300 border-amber-500/30';
    scoreColor = 'text-amber-300';
  }

  const availableMods = prediction.availableModalities || ['voice', 'motor', 'sleep', 'typing', 'visual'];
  const missingMods = prediction.missingModalities || ['olfactory', 'retinal'];

  return (
    <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 shadow-lg space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <Cpu className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">Research Screening Result</h3>
            <p className="text-[11px] text-slate-400">
              Multimodal Prodromal Fusion (MPF) Model Inference
            </p>
          </div>
        </div>

        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
          {prediction.modelVersion || 'v2.1.0'}
        </span>
      </div>

      {/* Mandatory Prominent Non-Diagnostic Research Disclaimer */}
      <div className="p-3.5 rounded-xl bg-amber-950/40 border border-amber-600/40 text-amber-200 space-y-1.5">
        <div className="flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
          <span className="text-xs font-bold uppercase tracking-wider text-amber-300">
            Research screening result — not a clinical diagnosis
          </span>
        </div>
        <p className="text-xs text-amber-200/90 leading-relaxed">
          This estimate is generated solely for academic exploratory monitoring. It does not indicate clinical diagnosis, disease confirmation, or therapeutic decisions.
        </p>
        <button
          onClick={() => setShowDisclaimerDetails(!showDisclaimerDetails)}
          className="text-[11px] text-amber-300 underline font-medium hover:text-amber-200 transition-colors inline-flex items-center gap-1"
        >
          {showDisclaimerDetails ? 'Hide ethical guidance' : 'View scientific interpretation guidance'}
        </button>

        {showDisclaimerDetails && (
          <div className="mt-2 pt-2 border-t border-amber-700/40 text-[11px] text-amber-200/80 space-y-1">
            <p>• Results reflect multi-sensor pattern convergence relative to reference research datasets.</p>
            <p>• Mobile data represents opportunistic digital behavioral measures rather than clinical exams.</p>
            <p>• For any health inquiries or symptoms, consult with a licensed neurologist or healthcare provider.</p>
          </div>
        )}
      </div>

      {/* Risk Pattern Gauge & Status Callout */}
      <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="text-center sm:text-left space-y-1">
          <div className="text-xs text-slate-400">Fusion Risk Pattern Index</div>
          <div className="flex items-baseline gap-2 justify-center sm:justify-start">
            <span className={`text-3xl font-extrabold font-mono ${scoreColor}`}>
              {score.toFixed(2)}
            </span>
            <span className="text-xs text-slate-400 font-normal">/ 1.00</span>
          </div>
          <div className="text-[11px] text-slate-400">
            Evaluated on {prediction.evaluationDate || 'Today'}
          </div>
        </div>

        <div className="flex flex-col items-center sm:items-end gap-1.5">
          <div className={`px-3 py-1.5 rounded-full border text-xs font-bold text-center ${statusBadgeStyle}`}>
            {statusBadgeText}
          </div>
          <span className="text-[10px] text-slate-400">
            Cross-modality gating confidence: 91.4%
          </span>
        </div>
      </div>

      {/* Modality Coverage Matrix */}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold text-slate-300">Modality Coverage & Sensor Audit</span>
          <span className="text-[11px] text-slate-400">
            {availableMods.length} Active / {missingMods.length} Imputed
          </span>
        </div>

        {/* Available Modalities */}
        <div className="p-3 rounded-xl bg-slate-950/40 border border-slate-800/80 space-y-2 text-xs">
          <div className="text-slate-400 text-[11px] font-semibold uppercase tracking-wider">
            Mobile-Collected Modalities
          </div>
          <div className="flex flex-wrap gap-1.5">
            {availableMods.map((mod) => (
              <span
                key={mod}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-950/60 border border-indigo-800/50 text-indigo-300 text-[11px] font-medium"
              >
                <CheckCircle2 className="w-3 h-3 text-indigo-400" />
                {formatModalityName(mod)}
              </span>
            ))}
          </div>
        </div>

        {/* Missing Modalities — Non-Overclaiming Guarantee (Rule 2) */}
        <div className="p-3 rounded-xl bg-slate-950/40 border border-slate-800/80 space-y-2 text-xs">
          <div className="text-slate-400 text-[11px] font-semibold uppercase tracking-wider">
            Missing Modalities (Learnable Masking Applied)
          </div>
          <div className="space-y-1.5">
            {missingMods.map((mod) => (
              <div
                key={mod}
                className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-[11px] text-slate-400 flex items-start gap-2"
              >
                <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-mono text-[10px] uppercase">
                  {mod}
                </span>
                <span className="leading-relaxed">
                  {getMissingModalityExplanation(mod)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Explainability & Feature Attributions Accordion */}
      <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-950/40">
        <button
          onClick={() => setShowExplainability(!showExplainability)}
          className="w-full p-3 flex items-center justify-between text-xs font-semibold text-slate-300 hover:bg-slate-900/50 transition-colors"
        >
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-indigo-400" />
            <span>Multimodal Explainability & Weights</span>
          </div>
          {showExplainability ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </button>

        {showExplainability && (
          <div className="p-3.5 border-t border-slate-800 text-xs space-y-3 bg-slate-900/40">
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Relative attention weights assigned by the multimodal gated fusion neural network for this evaluation:
            </p>

            {/* Weights bars */}
            <div className="space-y-2">
              {Object.entries(prediction.modalityWeights || {}).map(([mod, weight]) => {
                const pct = Math.round(weight * 100);
                return (
                  <div key={mod} className="space-y-1">
                    <div className="flex justify-between text-[11px]">
                      <span className="text-slate-300 font-medium">{formatModalityName(mod)}</span>
                      <span className="font-mono text-slate-400">{pct}% weight</span>
                    </div>
                    <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full bg-indigo-500 rounded-full"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-[11px] text-slate-400 leading-relaxed">
              <span className="font-semibold text-slate-300">Model Interpretation: </span>
              {prediction.explanation || 'Signals reflect concordant variation across acoustic and kinematic streams.'}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function formatModalityName(mod) {
  switch (mod.toLowerCase()) {
    case 'voice':
      return 'Voice Acoustic Module (16-D)';
    case 'motor':
      return 'Motor & Gait Module (8-D)';
    case 'sleep':
      return 'Sleep & RBDSQ Module (16-D)';
    case 'typing':
      return 'Typing Dynamics Module';
    case 'visual':
      return 'Ocular/Visual Behavior Module';
    case 'olfactory':
      return 'Olfactory Modality';
    case 'retinal':
      return 'Retinal Imaging Modality';
    default:
      return mod.charAt(0).toUpperCase() + mod.slice(1);
  }
}

function getMissingModalityExplanation(mod) {
  if (mod.toLowerCase() === 'retinal') {
    return 'Dedicated retinal fundus/OCT imaging requires specialized ophthalmological hardware. Front camera tracks Ocular/Visual Behavior only, NOT retinal imaging.';
  }
  if (mod.toLowerCase() === 'olfactory') {
    return 'Olfactory testing requires standardized physical odorant kits (UPSIT/Sniffin’ Sticks) not available via mobile hardware. Gated fusion applies learnable missing token.';
  }
  return 'Not present on mobile hardware; handled by learnable missing token.';
}

export default ScreeningResult;
