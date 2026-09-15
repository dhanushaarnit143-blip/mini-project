import React from 'react';
import { AlertTriangle, CheckCircle } from 'lucide-react';

interface MissingModalityCalloutProps {
  missingModalities: string[];
}

export const MissingModalityCallout: React.FC<MissingModalityCalloutProps> = ({
  missingModalities,
}) => {
  if (!missingModalities || missingModalities.length === 0) {
    return (
      <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-center gap-3 text-emerald-900 text-xs sm:text-sm">
        <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0" />
        <div>
          <span className="font-semibold">Complete Multimodal Profile:</span> All 5 modalities (olfactory, RBD, voice, motor, and retina) were available for fusion. Missingness-related uncertainty is minimal.
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="missing-modality-callout"
      className="bg-amber-50/80 border border-amber-200/80 rounded-xl p-4.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-amber-900 shadow-sm"
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div>
          <div className="font-semibold text-xs sm:text-sm flex items-center gap-2">
            <span>Missing Modality Impact:</span>
            <div className="flex flex-wrap gap-1.5">
              {missingModalities.map((mod) => (
                <span
                  key={mod}
                  className="px-2 py-0.5 bg-amber-200/70 text-amber-900 rounded font-mono text-[11px] uppercase tracking-wider font-bold"
                >
                  {mod}
                </span>
              ))}
            </div>
          </div>
          <p className="text-xs text-amber-800 mt-1">
            The fusion model adjusted weights based on available data. Missing modalities increase estimate uncertainty.
          </p>
        </div>
      </div>

      <div className="text-[11px] text-amber-800/80 sm:text-right font-medium shrink-0 bg-amber-100/50 px-3 py-1.5 rounded-lg border border-amber-200/50">
        Learned missing tokens applied
      </div>
    </div>
  );
};
