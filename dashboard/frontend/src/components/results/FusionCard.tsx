import React from 'react';
import { ShieldAlert, Cpu } from 'lucide-react';
import { FusionResult } from '../../types/pipeline';
import { formatRiskScore } from '../../lib/utils';

interface FusionCardProps {
  fusion: FusionResult;
  participantId: string;
}

export const FusionCard: React.FC<FusionCardProps> = ({ fusion, participantId }) => {
  const isElevated = fusion.risk_score >= 0.5;
  const scorePercent = fusion.risk_score * 100;

  // Calculate SVG arc for gauge
  const radius = 80;
  const strokeWidth = 14;
  const arcLength = Math.PI * radius;
  const strokeDashoffset = arcLength - (arcLength * Math.min(Math.max(scorePercent, 0), 100)) / 100;

  return (
    <div
      data-testid="fusion-card"
      className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm overflow-hidden relative"
    >
      <div className="flex flex-col lg:flex-row items-center justify-between gap-8">
        {/* Left: Risk Gauge & Score */}
        <div className="flex flex-col items-center text-center">
          <div className="relative w-48 h-28 flex items-end justify-center overflow-hidden">
            <svg viewBox="0 0 200 110" className="w-48 h-28">
              {/* Background Arc */}
              <path
                d="M 20 100 A 80 80 0 0 1 180 100"
                fill="none"
                stroke="#e2e8f0"
                strokeWidth={strokeWidth}
                strokeLinecap="round"
              />
              {/* Active Progress Arc */}
              <path
                d="M 20 100 A 80 80 0 0 1 180 100"
                fill="none"
                stroke={isElevated ? '#d97706' : '#0d9488'}
                strokeWidth={strokeWidth}
                strokeDasharray={arcLength}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                className="transition-all duration-1000 ease-out"
              />
            </svg>
            <div className="absolute bottom-1 flex flex-col items-center">
              <span className="text-3xl font-extrabold tracking-tight text-slate-900">
                {formatRiskScore(fusion.risk_score)}
              </span>
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">
                Research Risk Score
              </span>
            </div>
          </div>
          <div className="mt-2 text-xs font-medium text-slate-500">
            Participant: <span className="font-mono text-slate-700">{participantId}</span>
          </div>
        </div>

        {/* Center: Classification Pattern & Non-diagnostic notices */}
        <div className="flex-1 text-center lg:text-left space-y-2">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold tracking-wide uppercase bg-slate-100 text-slate-700 border border-slate-200">
            <Cpu className="w-3.5 h-3.5 text-teal-600" />
            <span>Gated Multimodal Neural Fusion</span>
          </div>

          <h3
            data-testid="risk-pattern-text"
            className={`text-xl sm:text-2xl font-bold tracking-tight ${
              isElevated ? 'text-amber-700' : 'text-teal-700'
            }`}
          >
            {fusion.risk_pattern}
          </h3>

          <p className="text-xs sm:text-sm text-slate-600 max-w-xl">
            This is a research risk estimate, not a clinical diagnosis. The estimate reflects cross-modality patterns weighted by dynamic neural gating.
          </p>

          <div className="pt-2 flex flex-wrap items-center justify-center lg:justify-start gap-4 text-xs text-slate-500">
            <span className="flex items-center gap-1">
              <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
              <span>Investigational Use Only</span>
            </span>
            <span>•</span>
            <span>Version: {fusion.model_version}</span>
            <span>•</span>
            <span>Mode: {fusion.experiment_type}</span>
          </div>
        </div>

        {/* Right: Neural Gating Attention Weights */}
        <div className="w-full lg:w-72 bg-slate-50/80 p-4 rounded-xl border border-slate-200/80 space-y-2.5">
          <div className="flex justify-between items-center text-xs font-semibold text-slate-700 pb-1 border-b border-slate-200">
            <span>Dynamic Gate Weights</span>
            <span className="text-[10px] text-slate-400 font-normal">Attention Alloc.</span>
          </div>

          {Object.entries(fusion.gate_weights).map(([mod, weight]) => {
            const isPresent = fusion.modality_presence[mod];
            return (
              <div key={mod} className="space-y-1">
                <div className="flex justify-between text-[11px]">
                  <span className={`capitalize ${isPresent ? 'text-slate-700 font-medium' : 'text-slate-400 italic'}`}>
                    {mod} {!isPresent && '(masked)'}
                  </span>
                  <span className="font-mono text-slate-600">{(weight * 100).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      isPresent ? 'bg-teal-600' : 'bg-slate-400'
                    }`}
                    style={{ width: `${Math.min(weight * 100, 100)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
