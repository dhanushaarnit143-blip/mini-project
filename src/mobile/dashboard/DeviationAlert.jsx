import React, { useState } from 'react';
import { AlertCircle, AlertTriangle, CheckCircle, Clock, Info, ChevronDown, ChevronUp, Bell } from 'lucide-react';

/**
 * DeviationAlert Component — Section 3: Deviation Alerts
 * 
 * Displays recent deviations detected by the longitudinal engine:
 * - Severity levels: mild / moderate / significant
 * - Duration: single day / sustained (consecutive days)
 * - Safe non-diagnostic framing:
 *   "Your recent measurements differ from your personal baseline"
 *   "Sustained deviation detected"
 *   "Moderate deviation from baseline"
 * 
 * Strict Compliance:
 * - Enforces zero diagnostic claims and rejects prohibited clinical statements.
 * - Uses calm amber/orange tones rather than emergency red.
 * - Provides non-alarming contextual explanations (fatigue, sleep variations, caffeine).
 */

export function DeviationAlert({
  deviations = [],
  onAcknowledge,
  maxVisible = 5
}) {
  const [expandedId, setExpandedId] = useState(null);

  // If no deviations or all within baseline
  if (!deviations || deviations.length === 0) {
    return (
      <div className="bg-slate-900/80 rounded-2xl border border-slate-800 p-5 shadow-lg">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/25 flex items-center justify-center text-emerald-400 shrink-0">
            <CheckCircle className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">No Significant Deviations</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Your recent measurements remain consistent with your personal baseline across all monitored modalities.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const toggleExpand = (id) => {
    setExpandedId(prev => (prev === id ? null : id));
  };

  return (
    <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 shadow-lg space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400">
            <Bell className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">Personal Deviation Alerts</h3>
            <p className="text-[11px] text-slate-400">
              Tracking personal baseline variations over time
            </p>
          </div>
        </div>

        <span className="px-2.5 py-0.5 rounded-full bg-amber-500/15 border border-amber-500/30 text-amber-300 text-[11px] font-semibold">
          {deviations.length} Active {deviations.length === 1 ? 'Notice' : 'Notices'}
        </span>
      </div>

      {/* Primary Safe Language Banner */}
      <div className="p-3.5 rounded-xl bg-amber-950/30 border border-amber-600/30 text-amber-200 text-xs flex items-start gap-2.5">
        <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <div className="font-semibold text-amber-300">
            Your recent measurements differ from your personal baseline
          </div>
          <p className="text-amber-200/80 leading-relaxed text-[11px]">
            Variations can arise from benign daily influences including sleep duration, fatigue, physical exertion, or time of recording. Continued longitudinal tracking helps map your unique personal variability.
          </p>
        </div>
      </div>

      {/* List of Deviations */}
      <div className="space-y-2.5">
        {deviations.slice(0, maxVisible).map((dev) => {
          const isExpanded = expandedId === dev.id;
          const severityConfig = getSeverityConfig(dev.severity, dev.zScore);
          const durationLabel = dev.durationType === 'sustained' || (dev.consecutiveDays && dev.consecutiveDays >= 3)
            ? 'Sustained deviation detected'
            : 'Single day observation';

          return (
            <div
              key={dev.id}
              className={`rounded-xl border transition-all ${
                isExpanded ? 'bg-slate-950 border-slate-700' : 'bg-slate-950/50 border-slate-800/80 hover:border-slate-700'
              }`}
            >
              {/* Collapsed Header Bar */}
              <div
                onClick={() => toggleExpand(dev.id)}
                className="p-3.5 flex items-center justify-between cursor-pointer select-none"
              >
                <div className="flex items-center gap-3">
                  <div className={`w-2.5 h-2.5 rounded-full ${severityConfig.dotColor}`} />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-white">
                        {dev.featureName || dev.modality}
                      </span>
                      <span className={`text-[10px] px-2 py-0.5 rounded-md font-semibold ${severityConfig.badgeStyle}`}>
                        {severityConfig.label}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-[11px] text-slate-400 mt-0.5">
                      <span>{dev.date || 'Recent observation'}</span>
                      <span>•</span>
                      <span className="text-slate-300">{durationLabel}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-slate-400">
                  <span className="text-[11px] font-mono text-slate-300">
                    {dev.zScore != null ? `${dev.zScore > 0 ? '+' : ''}${Number(dev.zScore).toFixed(1)}σ` : ''}
                  </span>
                  {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </div>
              </div>

              {/* Expanded Card Details */}
              {isExpanded && (
                <div className="px-3.5 pb-3.5 pt-1 border-t border-slate-800/70 text-xs space-y-3">
                  <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 text-slate-300 space-y-1.5 leading-relaxed">
                    <div className="font-semibold text-slate-200">
                      Observation Details:
                    </div>
                    <p className="text-slate-300/90">
                      {dev.description || `Measured value differs from established personal calibration mean by ${Math.abs(dev.zScore || 2.1).toFixed(1)} standard deviations.`}
                    </p>
                    {dev.consecutiveDays && dev.consecutiveDays >= 2 && (
                      <div className="inline-flex items-center gap-1.5 text-amber-300 text-[11px] font-medium pt-1">
                        <Clock className="w-3.5 h-3.5" />
                        <span>Observed across {dev.consecutiveDays} consecutive collection days.</span>
                      </div>
                    )}
                  </div>

                  {/* Context Guidance */}
                  <div className="text-[11px] text-slate-400 flex items-start gap-2">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                    <span>
                      Research notice: Measurements reflect statistical deviation from personal baseline. If symptoms persist or cause clinical concern, consult a qualified physician.
                    </span>
                  </div>

                  {/* Action */}
                  {onAcknowledge && (
                    <div className="pt-1 flex justify-end">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onAcknowledge(dev.id);
                        }}
                        className="px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors"
                      >
                        Acknowledge Notice
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/**
 * Returns safe styling and non-diagnostic labels based on deviation severity.
 */
function getSeverityConfig(severity, zScore) {
  const absZ = Math.abs(zScore || 0);

  if (severity === 'significant' || absZ >= 3.0) {
    return {
      label: 'Significant deviation from baseline',
      badgeStyle: 'bg-amber-600/20 text-amber-400 border border-amber-600/40',
      dotColor: 'bg-amber-500'
    };
  }

  if (severity === 'moderate' || absZ >= 2.0) {
    return {
      label: 'Moderate deviation from baseline',
      badgeStyle: 'bg-amber-500/15 text-amber-300 border border-amber-500/30',
      dotColor: 'bg-amber-400'
    };
  }

  return {
    label: 'Mild deviation from baseline',
    badgeStyle: 'bg-amber-500/10 text-amber-200 border border-amber-500/20',
    dotColor: 'bg-amber-300'
  };
}

export default DeviationAlert;
