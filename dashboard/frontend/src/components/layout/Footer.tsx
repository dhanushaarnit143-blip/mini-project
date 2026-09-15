import React from 'react';
import { ShieldCheck, Info } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-white border-t border-slate-200 mt-16 py-8 text-xs text-slate-500">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-4">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-teal-600" />
            <span className="font-medium text-slate-700">MPF-PD Research Prototype • Multimodal Prodromal Fusion</span>
          </div>
          <div className="flex items-center gap-4 text-slate-400">
            <span>Client-side local processing</span>
            <span>•</span>
            <span>Zero cloud persistence</span>
            <span>•</span>
            <span>Pseudonymous PIDs</span>
          </div>
        </div>
        <div className="p-3 bg-slate-50 rounded-md border border-slate-200 flex items-start gap-2.5 text-slate-600">
          <Info className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            <strong>Investigational Notice:</strong> This software is a scientific research prototype developed to evaluate multimodal feature fusion and neural gating for prodromal risk pattern estimation. It does not provide medical advice or clinical diagnosis. Model outputs reflect research risk estimates derived in prototype simulation mode.
          </p>
        </div>
      </div>
    </footer>
  );
};
