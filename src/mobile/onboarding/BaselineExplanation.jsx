import React from 'react';
import { Calendar, Clock, BarChart3, AlertCircle, CheckCircle2, ArrowRight, ArrowLeft } from 'lucide-react';

/**
 * Screen 5: 14-Day Baseline Explanation
 * Educates the participant on personal reference calibration and why zero risk scores
 * are produced during the initial 14-day learning phase.
 */
export function BaselineExplanation({ onNext, onBack }) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between p-6 max-w-md mx-auto font-sans">
      <div>
        {/* Navigation Bar */}
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={onBack}
            className="p-2 -ml-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-900 transition cursor-pointer"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Step 5: Baseline Calibration
          </div>
          <div className="w-5" />
        </div>

        <h2 className="text-2xl font-bold tracking-tight text-white">
          The 14-Day Calibration
        </h2>
        <p className="mt-2 text-xs text-slate-400 leading-relaxed">
          How MPF learns your unique normal before calculating longitudinal stability.
        </p>

        {/* Timeline Visualization Card */}
        <div className="mt-5 p-4 rounded-2xl bg-gradient-to-br from-indigo-950/40 to-slate-900/80 border border-indigo-500/30">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-indigo-400" />
              <span className="text-xs font-bold text-slate-200">Days 1 through 14</span>
            </div>
            <span className="px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 text-[10px] font-semibold border border-indigo-500/30">
              Calibration Phase
            </span>
          </div>

          <div className="mt-3 flex items-center justify-between gap-1">
            {[1, 3, 5, 7, 9, 11, 14].map((day, idx) => (
              <div key={idx} className="flex flex-col items-center gap-1.5 flex-1">
                <div className={`w-7 h-7 rounded-lg flex items-center justify-center text-[10px] font-bold ${
                  day <= 3
                    ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-500/50'
                    : 'bg-slate-800 text-slate-400 border border-slate-700'
                }`}>
                  D{day}
                </div>
                <div className="w-1.5 h-1.5 rounded-full bg-slate-700" />
              </div>
            ))}
          </div>

          <p className="mt-4 text-[11px] text-slate-300 leading-relaxed">
            During these 14 days, brief 3-minute micro-tasks record your individual typing speed, voice timber, and motor cadence across varied times of day.
          </p>
        </div>

        {/* Strict Non-Scoring Policy */}
        <div className="mt-4 p-4 rounded-2xl bg-amber-950/30 border border-amber-600/40 text-amber-200">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div className="text-xs space-y-1">
              <div className="font-bold text-amber-300">
                Zero Risk Scores During Baseline
              </div>
              <p className="text-amber-200/90 leading-relaxed text-[11px]">
                To eliminate false alarms, <strong className="underline">no risk scores or pattern indicators</strong> are computed until your 14-day baseline is statistically calibrated.
              </p>
              <p className="text-amber-300/80 text-[10px] pt-1">
                Subsequent analyses report: <em>"Deviation from personal baseline"</em> — never diagnostic labels.
              </p>
            </div>
          </div>
        </div>

        {/* What to Expect Daily */}
        <div className="mt-4 space-y-2">
          <div className="flex items-center gap-2.5 p-2.5 rounded-xl bg-slate-900/60 border border-slate-800/80 text-xs">
            <Clock className="w-4 h-4 text-emerald-400 shrink-0" />
            <span className="text-slate-300 text-[11px]">3 to 5 minutes once per day at your convenience.</span>
          </div>

          <div className="flex items-center gap-2.5 p-2.5 rounded-xl bg-slate-900/60 border border-slate-800/80 text-xs">
            <BarChart3 className="w-4 h-4 text-sky-400 shrink-0" />
            <span className="text-slate-300 text-[11px]">Personal stability trends unlock automatically on Day 15.</span>
          </div>
        </div>
      </div>

      {/* Start Calibration Button */}
      <div className="pt-4 pb-2">
        <button
          onClick={onNext}
          className="w-full py-3.5 px-5 rounded-xl bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 active:scale-[0.99] text-white font-semibold text-sm shadow-lg shadow-indigo-500/25 flex items-center justify-center gap-2 transition cursor-pointer"
        >
          <span>Start Baseline Period</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

export default BaselineExplanation;
