import React, { useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
} from 'recharts';
import { HelpCircle, Layers, TrendingUp, TrendingDown } from 'lucide-react';
import { ExplainabilityResult } from '../../types/pipeline';

interface ExplainabilityPanelProps {
  explainability: ExplainabilityResult;
}

const MODALITY_COLORS: Record<string, string> = {
  olfactory: '#0284c7', // Sky
  rbd: '#6366f1',       // Indigo
  voice: '#10b981',     // Emerald
  motor: '#f59e0b',     // Amber
  retina: '#f43f5e',    // Rose
  demo: '#64748b',      // Slate
  unknown: '#94a3b8',
};

export const ExplainabilityPanel: React.FC<ExplainabilityPanelProps> = ({ explainability }) => {
  const [tab, setTab] = useState<'features' | 'modalities'>('features');

  // Prepare top positive & negative contributors for bar chart
  const topFeatures = explainability.important_features.slice(0, 10).map((f) => ({
    name: f.feature_name.replace(/_/g, ' '),
    rawName: f.feature_name,
    shap: f.shap_value,
    group: f.modality_group,
    direction: f.direction,
    featureValue: f.feature_value,
  }));

  // Prepare modality pie / bar data
  const modalityData = explainability.important_modalities.map((m) => ({
    name: m.modality.charAt(0).toUpperCase() + m.modality.slice(1),
    modalityKey: m.modality,
    value: Math.max(m.percent_contribution, 0.1),
    importance: m.importance,
    missing: m.missing,
  }));

  // Top modality narrative derivation
  const sortedModalities = [...explainability.important_modalities].sort(
    (a, b) => b.importance - a.importance
  );
  const primaryModality = sortedModalities.length > 0 ? sortedModalities[0].modality : 'features';
  const missingMods = explainability.missing_modalities;

  return (
    <div
      data-testid="explainability-panel"
      className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-6"
    >
      {/* Header & Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2">
            <Layers className="w-5 h-5 text-teal-600" />
            <h3 className="text-base font-bold text-slate-900 tracking-tight">
              SHAP Explainability & Attribution
            </h3>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Local Shapley additive explanations attributing risk pattern influence
          </p>
        </div>

        {/* Tab switch */}
        <div className="flex bg-slate-100 p-1 rounded-lg self-start sm:self-auto text-xs font-medium">
          <button
            type="button"
            onClick={() => setTab('features')}
            className={`px-3 py-1.5 rounded-md transition-all ${
              tab === 'features'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Top Feature Drivers
          </button>
          <button
            type="button"
            onClick={() => setTab('modalities')}
            className={`px-3 py-1.5 rounded-md transition-all ${
              tab === 'modalities'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Modality Importance
          </button>
        </div>
      </div>

      {/* Model Narrative Callout */}
      <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-700 leading-relaxed space-y-1">
        <p className="font-semibold text-slate-900 flex items-center gap-1.5">
          <HelpCircle className="w-3.5 h-3.5 text-teal-600" />
          <span>Decision Context Narrative:</span>
        </p>
        <p>
          The neural fusion network weighted{' '}
          <strong className="text-slate-900 capitalize">{primaryModality}</strong> as the most influential available modality for this participant.
          {missingMods.length > 0 ? (
            <>
              {' '}Because <strong className="text-slate-900">{missingMods.join(', ')}</strong> was missing, the attention gating unit reallocated weights across available modalities, which increases estimate uncertainty.
            </>
          ) : (
            ' All 5 modalities were present, allowing balanced multimodal cross-attention.'
          )}
        </p>
      </div>

      {/* Main Chart Area */}
      {tab === 'features' ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                <span className="text-slate-700 font-medium">Increases Risk Signal (SHAP &gt; 0)</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-teal-500" />
                <span className="text-slate-700 font-medium">Decreases Risk Signal (SHAP &lt; 0)</span>
              </span>
            </div>
            <span className="hidden sm:inline text-slate-400">Base Expected Value: {explainability.shap_base_value.toFixed(3)}</span>
          </div>

          <div className="h-80 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={topFeatures}
                layout="vertical"
                margin={{ top: 5, right: 30, left: 140, bottom: 5 }}
              >
                <XAxis type="number" tick={{ fontSize: 11, fill: '#64748b' }} domain={['dataMin - 0.02', 'dataMax + 0.02']} />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fontSize: 11, fill: '#334155' }}
                  width={130}
                />
                <Tooltip
                  formatter={(value: any, _: any, item: any) => [
                    `SHAP: ${Number(value).toFixed(4)} (Value: ${item.payload.featureValue})`,
                    `Group: ${item.payload.group}`,
                  ]}
                  contentStyle={{
                    backgroundColor: '#ffffff',
                    borderRadius: '8px',
                    borderColor: '#e2e8f0',
                    fontSize: '12px',
                    boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                  }}
                />
                <Bar dataKey="shap" radius={[4, 4, 4, 4]}>
                  {topFeatures.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.shap >= 0 ? '#f59e0b' : '#0d9488'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      ) : (
        /* Modality Importance View */
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
          <div className="h-64 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={modalityData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {modalityData.map((entry) => (
                    <Cell
                      key={entry.modalityKey}
                      fill={entry.missing ? '#cbd5e1' : MODALITY_COLORS[entry.modalityKey] || '#64748b'}
                    />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(val: any, name: any, item: any) => [
                    `${Number(val).toFixed(1)}% contribution`,
                    item.payload.missing ? `${name} (Skipped)` : name,
                  ]}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Legend and details */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wider">
              Relative Modality Contributions
            </h4>
            <div className="space-y-2">
              {modalityData.map((m) => (
                <div
                  key={m.modalityKey}
                  className="flex items-center justify-between text-xs p-2 rounded-lg bg-slate-50 border border-slate-200"
                >
                  <div className="flex items-center gap-2">
                    <span
                      className="w-3 h-3 rounded-full shrink-0"
                      style={{
                        backgroundColor: m.missing
                          ? '#cbd5e1'
                          : MODALITY_COLORS[m.modalityKey] || '#64748b',
                      }}
                    />
                    <span className="font-medium text-slate-800">
                      {m.name} {m.missing && '(Missing)'}
                    </span>
                  </div>
                  <span className="font-mono text-slate-600 font-semibold">
                    {m.value.toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Top Positive & Negative lists */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
        <div className="bg-amber-50/50 border border-amber-200/70 rounded-xl p-4 space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold text-amber-900">
            <TrendingUp className="w-4 h-4 text-amber-600" />
            <span>Top Contributors Increasing Risk Signal</span>
          </div>
          <ul className="space-y-1 text-xs text-amber-800">
            {explainability.positive_contributors.slice(0, 4).map((f) => (
              <li key={f.feature_name} className="flex justify-between font-mono text-[11px]">
                <span className="truncate max-w-[200px]">{f.feature_name}</span>
                <span className="font-semibold text-amber-900">+{f.shap_value.toFixed(4)}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="bg-teal-50/50 border border-teal-200/70 rounded-xl p-4 space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold text-teal-900">
            <TrendingDown className="w-4 h-4 text-teal-600" />
            <span>Top Contributors Decreasing Risk Signal</span>
          </div>
          <ul className="space-y-1 text-xs text-teal-800">
            {explainability.negative_contributors.slice(0, 4).map((f) => (
              <li key={f.feature_name} className="flex justify-between font-mono text-[11px]">
                <span className="truncate max-w-[200px]">{f.feature_name}</span>
                <span className="font-semibold text-teal-900">{f.shap_value.toFixed(4)}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
};
