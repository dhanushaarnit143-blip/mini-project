import React from 'react';
import { AlertTriangle, ShieldAlert } from 'lucide-react';

export const DisclaimerBanner: React.FC = () => {
  return (
    <div
      data-testid="disclaimer-banner"
      className="bg-amber-50 border-b border-amber-200 px-4 py-2.5 text-amber-900"
    >
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-3 text-xs sm:text-sm">
        <div className="flex items-center gap-2 font-semibold tracking-wide">
          <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
          <span className="uppercase tracking-wider">Research Prototype — Not for Clinical Diagnosis</span>
        </div>
        <div className="hidden md:flex items-center gap-2 text-amber-800">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
          <span>Requires clinician review if used in future clinical studies. Investigational screening estimate only.</span>
        </div>
      </div>
    </div>
  );
};
