import React, { useState } from 'react';
import { ShieldCheck, AlertCircle, ArrowRight, BookOpen, Lock, Activity, Sparkles } from 'lucide-react';

/**
 * Screen 1: Welcome Screen
 * - Project Name: MPF Mobile Research
 * - Core research statement and prominent non-diagnostic disclaimer
 * - "Learn More" modal and "Get Started" navigation
 */
export function WelcomeScreen({ onNext }) {
  const [showLearnMore, setShowLearnMore] = useState(false);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between p-6 max-w-md mx-auto relative overflow-hidden font-sans">
      {/* Background ambient gradient */}
      <div className="absolute top-0 -left-20 w-72 h-72 bg-indigo-600/15 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-10 -right-20 w-80 h-80 bg-teal-500/15 rounded-full blur-3xl pointer-events-none" />

      {/* Header Badge */}
      <div className="pt-8">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-950/80 border border-indigo-700/50 text-indigo-300 text-xs font-semibold tracking-wide mb-6">
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          <span>Multimodal Prodromal Fusion Research</span>
        </div>

        <h1 className="text-3xl font-extrabold tracking-tight text-white leading-tight">
          MPF Mobile Research
        </h1>
        <p className="mt-3 text-slate-400 text-sm leading-relaxed">
          A longitudinal scientific study exploring how subtle daily digital biomarkers—such as typing cadence, vocal dynamics, and micro-movements—can establish your personal baseline.
        </p>
      </div>

      {/* Prominent Research Disclaimer Card */}
      <div className="my-6 p-4 rounded-2xl bg-amber-950/40 border border-amber-600/40 text-amber-200 shadow-lg shadow-amber-950/20">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="text-xs space-y-1.5">
            <p className="font-bold uppercase tracking-wider text-amber-300 text-[11px]">
              Mandatory Research Disclaimer
            </p>
            <p className="text-amber-200/90 leading-relaxed font-medium">
              This is a research prototype. It does <strong className="underline decoration-amber-400 font-bold">NOT</strong> diagnose Parkinson's disease or provide clinical diagnoses of any kind.
            </p>
            <p className="text-amber-300/80 text-[11px]">
              All calculations measure potential deviations from your own unique personal baseline.
            </p>
          </div>
        </div>
      </div>

      {/* Highlights */}
      <div className="space-y-3 my-2">
        <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-900/60 border border-slate-800/80 text-xs">
          <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
            <Activity className="w-4 h-4" />
          </div>
          <div>
            <div className="font-semibold text-slate-200">14-Day Baseline Calibration</div>
            <div className="text-slate-400">Zero scores generated until your personal normal is learned.</div>
          </div>
        </div>

        <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-900/60 border border-slate-800/80 text-xs">
          <div className="p-2 rounded-lg bg-teal-500/10 text-teal-400">
            <Lock className="w-4 h-4" />
          </div>
          <div>
            <div className="font-semibold text-slate-200">Privacy & Pseudonymity First</div>
            <div className="text-slate-400">No passwords or messages stored. Zero raw audio uploaded by default.</div>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="pt-6 pb-4 space-y-3">
        <button
          onClick={onNext}
          className="w-full py-3.5 px-5 rounded-xl bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 active:scale-[0.99] text-white font-semibold text-sm shadow-lg shadow-indigo-500/25 flex items-center justify-center gap-2 transition-all cursor-pointer"
        >
          <span>Get Started</span>
          <ArrowRight className="w-4 h-4" />
        </button>

        <button
          type="button"
          onClick={() => setShowLearnMore(true)}
          className="w-full py-3 px-4 rounded-xl bg-slate-900 hover:bg-slate-800/80 border border-slate-800 text-slate-300 font-medium text-xs flex items-center justify-center gap-2 transition cursor-pointer"
        >
          <BookOpen className="w-3.5 h-3.5 text-slate-400" />
          <span>Learn More About the Study</span>
        </button>
      </div>

      {/* Learn More Modal */}
      {showLearnMore && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-sm w-full p-6 text-slate-200 max-h-[85vh] overflow-y-auto space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-white text-base">About MPF Research</h3>
              <button
                onClick={() => setShowLearnMore(false)}
                className="text-slate-400 hover:text-white text-sm px-2 py-1 rounded"
              >
                ✕
              </button>
            </div>

            <div className="text-xs text-slate-300 space-y-3 leading-relaxed">
              <p>
                <strong>Scientific Objective:</strong> The Multimodal Prodromal Fusion (MPF) framework explores multimodal sensor data for early pattern recognition. This mobile extension records voluntary, micro-session activities to assess longitudinal trends.
              </p>
              <p>
                <strong>Personalized Baseline:</strong> Everyone types, speaks, and moves differently. Rather than imposing arbitrary population averages, MPF learns your unique 14-day baseline.
              </p>
              <p>
                <strong>Participant Rights:</strong> Participation is 100% voluntary. You can export all your data or irreversibly purge your records at any time.
              </p>
              <p className="p-2.5 rounded-lg bg-amber-950/40 border border-amber-800/50 text-amber-200 font-medium">
                Remember: This application provides experimental research screening metrics and never substitutes for certified neurological consultation.
              </p>
            </div>

            <button
              onClick={() => setShowLearnMore(false)}
              className="w-full py-2.5 rounded-xl bg-indigo-600 text-white font-semibold text-xs mt-2"
            >
              Understood
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default WelcomeScreen;
