import React, { useEffect, useState } from 'react';
import { Activity, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';
import { checkApiHealth } from '../../lib/api';

export const Header: React.FC = () => {
  const [health, setHealth] = useState<'ok' | 'degraded' | 'offline' | 'checking'>('checking');

  useEffect(() => {
    checkApiHealth()
      .then((data) => setHealth(data.status === 'ok' ? 'ok' : 'degraded'))
      .catch(() => setHealth('offline'));
  }, []);

  return (
    <header className="bg-white border-b border-slate-200 shadow-sm sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-teal-600 text-white p-2 rounded-lg shadow-sm">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-slate-900 tracking-tight">MPF-PD Platform</h1>
              <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                Phase 8 Prototype
              </span>
            </div>
            <p className="text-xs text-slate-500">Multimodal Prodromal Risk Screening (Olfactory • RBD • Voice • Motor • Retina)</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border bg-slate-50 border-slate-200">
            {health === 'checking' && (
              <>
                <RefreshCw className="w-3 h-3 text-slate-400 animate-spin" />
                <span className="text-slate-500">Connecting...</span>
              </>
            )}
            {health === 'ok' && (
              <>
                <CheckCircle2 className="w-3 h-3 text-teal-600" />
                <span className="text-slate-700">Backend Ready</span>
              </>
            )}
            {health === 'degraded' && (
              <>
                <AlertCircle className="w-3 h-3 text-amber-500" />
                <span className="text-amber-700">Degraded</span>
              </>
            )}
            {health === 'offline' && (
              <>
                <AlertCircle className="w-3 h-3 text-rose-500" />
                <span className="text-rose-700">Offline</span>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
