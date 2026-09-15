import React from 'react';
import {
  Wind,
  Moon,
  Mic,
  Activity,
  Eye,
  CheckCircle2,
  AlertTriangle,
  MinusCircle,
  XCircle,
} from 'lucide-react';
import { IndividualModalityResult } from '../../types/pipeline';
import { formatRiskScore } from '../../lib/utils';

interface ModalityCardsProps {
  modalities: Record<string, IndividualModalityResult>;
}

const MODALITY_CONFIG: Record<
  string,
  { label: string; icon: React.FC<{ className?: string }>; color: string }
> = {
  olfactory: { label: 'Olfactory (UPSIT)', icon: Wind, color: 'text-sky-600 bg-sky-50' },
  rbd: { label: 'RBD (Questionnaire)', icon: Moon, color: 'text-indigo-600 bg-indigo-50' },
  voice: { label: 'Voice Acoustics', icon: Mic, color: 'text-emerald-600 bg-emerald-50' },
  motor: { label: 'Motor & Gait', icon: Activity, color: 'text-amber-600 bg-amber-50' },
  retina: { label: 'Retinal Microvasculature', icon: Eye, color: 'text-rose-600 bg-rose-50' },
};

export const ModalityCards: React.FC<ModalityCardsProps> = ({ modalities }) => {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-slate-900">Individual Biomarker Modality Breakdown</h4>
        <span className="text-xs text-slate-500">5-Modality Prodromal Battery</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {Object.entries(modalities).map(([key, data]) => {
          const cfg = MODALITY_CONFIG[key] || {
            label: key,
            icon: Activity,
            color: 'text-slate-600 bg-slate-50',
          };
          const Icon = cfg.icon;

          return (
            <div
              key={key}
              data-testid={`result-card-${key}`}
              className={`rounded-xl border p-4 flex flex-col justify-between transition-all ${
                data.status === 'success'
                  ? 'bg-white border-slate-200 shadow-sm'
                  : data.status === 'failed_qc'
                  ? 'bg-rose-50/50 border-rose-200 shadow-sm'
                  : 'bg-slate-50/60 border-slate-200/60'
              }`}
            >
              <div>
                {/* Header */}
                <div className="flex items-center justify-between gap-2 pb-2 mb-2 border-b border-slate-100">
                  <div className="flex items-center gap-2 truncate">
                    <div className={`p-1.5 rounded-lg ${cfg.color}`}>
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <span className="text-xs font-semibold text-slate-800 truncate">
                      {cfg.label}
                    </span>
                  </div>

                  {data.status === 'success' && (
                    <span className="flex items-center gap-1 text-[10px] font-medium text-teal-700 bg-teal-50 px-2 py-0.5 rounded-full border border-teal-200 shrink-0">
                      <CheckCircle2 className="w-3 h-3" />
                      <span>Ready</span>
                    </span>
                  )}
                  {data.status === 'missing' && (
                    <span className="flex items-center gap-1 text-[10px] font-medium text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full border border-slate-200 shrink-0">
                      <MinusCircle className="w-3 h-3" />
                      <span>Skipped</span>
                    </span>
                  )}
                  {data.status === 'failed_qc' && (
                    <span className="flex items-center gap-1 text-[10px] font-medium text-rose-700 bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200 shrink-0">
                      <XCircle className="w-3 h-3" />
                      <span>QC Failed</span>
                    </span>
                  )}
                </div>

                {/* Body Risk / Status */}
                <div className="py-2">
                  <div className="text-[11px] text-slate-500">Individual Risk Signal</div>
                  <div className="text-lg font-bold text-slate-900">
                    {data.status === 'success'
                      ? data.risk_score !== null
                        ? formatRiskScore(data.risk_score)
                        : 'Biomarker Extracted'
                      : '—'}
                  </div>
                </div>

                {/* Quality issues or warnings */}
                {data.quality && !data.quality.passed && data.quality.issues.length > 0 && (
                  <div className="text-[11px] text-rose-600 bg-rose-50 p-2 rounded border border-rose-200 mt-2">
                    <div className="font-medium flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" />
                      <span>QC Issue</span>
                    </div>
                    <p className="truncate text-[10px]">{data.quality.issues[0]}</p>
                  </div>
                )}
              </div>

              {/* Footer feature count */}
              <div className="pt-3 mt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
                <span>Features Used</span>
                <span className="font-mono text-slate-600">
                  {Object.keys(data.features || {}).length}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
