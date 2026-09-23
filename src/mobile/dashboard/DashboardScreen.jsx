import React, { useState } from 'react';
import {
  Activity,
  CheckCircle2,
  Clock,
  AlertTriangle,
  RefreshCw,
  Sparkles,
  ChevronRight,
  ShieldCheck,
  Calendar,
  Layers,
  BarChart2,
  Lock,
  ArrowUpRight
} from 'lucide-react';

import { TrendChart } from './TrendChart';
import { DeviationAlert } from './DeviationAlert';
import { ScreeningResult } from './ScreeningResult';
import { DataQualityPanel } from './DataQualityPanel';
import { PrivacyControls } from './PrivacyControls';

/**
 * DashboardScreen Component — Personal Research Dashboard (Phase 14)
 * 
 * Master responsive mobile container integrating all 6 required dashboard sections:
 * - Section 1: Today's Summary (Collection status, quality scores, baseline status badge)
 * - Section 2: Personal Trends (14/30/90-day multi-modality trend curves with baseline envelope)
 * - Section 3: Deviation Alerts (Non-diagnostic deviation cards with severity & duration)
 * - Section 4: Research Screening Result (Experimental MPF fusion risk pattern & non-diagnostic disclaimer)
 * - Section 5: Data Quality (Adherence tracking, missing patterns, signal quality)
 * - Section 6: Privacy & Data Controls (Consent toggles, data export, deletion, transparency)
 * 
 * Strict Compliance:
 * - Zero diagnostic claims ("Within personal baseline", "Elevated Parkinson's risk pattern detected")
 * - Front camera designated as Ocular/Visual Behavior Module (not retinal imaging)
 * - Non-alarming amber/orange for deviations, calm emerald for baseline, neutral slate for missing data.
 */

export function DashboardScreen({
  participantId = 'part_test_001',
  pseudonymousId = 'ps_4a8c9b_2026',
  baselineStatus = 'established', // 'calibrating' | 'established'
  calibrationDay = 14,
  onStartTask,
  onUpdateConsent,
  onExportData,
  onDeleteData
}) {
  const [selectedModality, setSelectedModality] = useState('voice');
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Section 1: Today's Tasks & Quality Summary
  const [todayTasks, setTodayTasks] = useState([
    { id: 'voice', name: 'Voice Phonation (5s)', completed: true, quality: 92, status: 'Within personal baseline', icon: 'mic' },
    { id: 'motor', name: 'Motor & Gait Walk (20s)', completed: true, quality: 88, status: 'Within personal baseline', icon: 'activity' },
    { id: 'typing', name: 'Typing Dynamics', completed: true, quality: 94, status: 'Within personal baseline', icon: 'keyboard' },
    { id: 'visual', name: 'Ocular/Visual Fixation', completed: false, quality: null, status: 'Pending', icon: 'eye' },
    { id: 'sleep', name: 'Sleep & RBDSQ Check-in', completed: true, quality: 100, status: 'Within personal baseline', icon: 'moon' }
  ]);

  const completedCount = todayTasks.filter(t => t.completed).length;
  const hasDeviationToday = todayTasks.some(t => t.status && t.status.toLowerCase().includes('deviation'));

  // Section 2: Personal Trends Configuration
  const trendMetrics = {
    voice: {
      metricName: 'Voice Pitch Jitter (local %)',
      modality: 'voice',
      baselineMean: 1.38,
      baselineStd: 0.24,
      currentValue: 1.48,
      unit: '%',
      description: 'Cycle-to-cycle acoustic perturbation from 5s sustained /a/ phonation'
    },
    motor: {
      metricName: 'Walking Cadence (steps/min)',
      modality: 'motor',
      baselineMean: 108.4,
      baselineStd: 5.6,
      currentValue: 104.2,
      unit: 'spm',
      description: 'Locomotor frequency from 20-second continuous linear walk'
    },
    typing: {
      metricName: 'Keystroke Hold Time (ms)',
      modality: 'typing',
      baselineMean: 96.2,
      baselineStd: 8.4,
      currentValue: 102.8,
      unit: 'ms',
      description: 'Average key press dwell latency across active daily typing'
    },
    visual: {
      metricName: 'Gaze Fixation Dispersion (BCEA)',
      modality: 'visual',
      baselineMean: 0.82,
      baselineStd: 0.16,
      currentValue: 0.86,
      unit: 'deg²',
      description: 'Bivariate contour ellipse area during 3s gaze fixation test'
    },
    sleep: {
      metricName: 'Sleep Duration (hours)',
      modality: 'sleep',
      baselineMean: 7.2,
      baselineStd: 0.9,
      currentValue: 7.0,
      unit: 'hrs',
      description: 'Self-reported nocturnal duration from morning micro-survey'
    }
  };

  // Section 3: Recent Deviations
  const [deviations, setDeviations] = useState([
    {
      id: 'dev_01',
      date: 'Yesterday',
      modality: 'Voice',
      featureName: 'Voice Pitch Jitter',
      zScore: 2.14,
      severity: 'moderate',
      durationType: 'single_day',
      consecutiveDays: 1,
      description: 'Acoustic pitch perturbation of 1.92% (baseline mean 1.38% ± 0.24%).',
      acknowledged: false
    },
    {
      id: 'dev_02',
      date: '3 Days Ago',
      modality: 'Motor & Gait',
      featureName: 'Stride Regularity CV',
      zScore: 2.35,
      severity: 'moderate',
      durationType: 'sustained',
      consecutiveDays: 3,
      description: 'Locomotor stride interval coefficient of variation showed sustained deviation across 3 recording days.',
      acknowledged: false
    }
  ]);

  const handleAcknowledgeDeviation = (id) => {
    setDeviations(prev => prev.filter(d => d.id !== id));
  };

  // Refresh handler
  const handleRefresh = async () => {
    setIsRefreshing(true);
    await new Promise(r => setTimeout(r, 600));
    setIsRefreshing(false);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans pb-16">
      {/* Mobile constrained container */}
      <div className="max-w-md mx-auto p-4 sm:p-5 space-y-6">
        
        {/* App Bar / Header */}
        <header className="flex items-center justify-between pt-2 pb-1">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 animate-pulse" />
              <span className="text-xs uppercase tracking-wider font-bold text-indigo-400">
                MPF Mobile Research
              </span>
            </div>
            <h1 className="text-xl font-extrabold text-white mt-0.5 tracking-tight">
              Personal Research Dashboard
            </h1>
          </div>

          <button
            onClick={handleRefresh}
            className={`p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition-all ${
              isRefreshing ? 'rotate-180 transition-transform duration-500' : ''
            }`}
            title="Refresh Research Metrics"
            aria-label="Refresh Research Metrics"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </header>

        {/* Participant & Baseline Status Badge */}
        <div className="flex items-center justify-between p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-slate-400">ID:</span>
            <span className="font-mono text-slate-200 font-semibold">{pseudonymousId}</span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span className="text-emerald-300 font-medium">
              {baselineStatus === 'calibrating' ? `Calibrating (Day ${calibrationDay}/14)` : '14-Day Baseline Established'}
            </span>
          </div>
        </div>

        {/* ==================================================
            SECTION 1: TODAY'S SUMMARY
            ================================================== */}
        <section aria-labelledby="section-today-summary" className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 id="section-today-summary" className="text-sm font-bold text-white uppercase tracking-wider">
              Section 1: Today's Summary
            </h2>
            <span className="text-xs text-slate-400">
              {completedCount} of {todayTasks.length} Completed
            </span>
          </div>

          {/* Quick Baseline Status Indicator */}
          <div className={`p-3.5 rounded-xl border flex items-center justify-between ${
            hasDeviationToday
              ? 'bg-amber-950/25 border-amber-600/30 text-amber-200'
              : 'bg-emerald-950/20 border-emerald-500/30 text-emerald-200'
          }`}>
            <div className="flex items-center gap-2.5">
              <span className={`w-3 h-3 rounded-full ${hasDeviationToday ? 'bg-amber-400' : 'bg-emerald-400'}`} />
              <div>
                <div className="text-xs font-bold">
                  {hasDeviationToday ? 'Deviation noted' : 'Within personal baseline'}
                </div>
                <div className="text-[11px] opacity-80 mt-0.5">
                  {hasDeviationToday
                    ? 'Recent observation differs from baseline envelope. Review trends.'
                    : 'All submitted daily metrics match your learned personal normal.'}
                </div>
              </div>
            </div>
          </div>

          {/* Tasks Checklist Grid */}
          <div className="space-y-2">
            {todayTasks.map((task) => (
              <div
                key={task.id}
                className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between gap-3"
              >
                <div className="flex items-center gap-3">
                  <div className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs ${
                    task.completed ? 'bg-emerald-500/15 text-emerald-400' : 'bg-slate-800 text-slate-400'
                  }`}>
                    {task.completed ? <CheckCircle2 className="w-4 h-4" /> : <Clock className="w-4 h-4" />}
                  </div>

                  <div>
                    <div className="text-xs font-semibold text-slate-200">{task.name}</div>
                    <div className="text-[11px] text-slate-400">
                      {task.completed ? (
                        <span className="text-emerald-400 font-medium">Completed (Quality {task.quality}%)</span>
                      ) : (
                        <span className="text-amber-400">Pending Daily Session</span>
                      )}
                    </div>
                  </div>
                </div>

                {!task.completed && onStartTask && (
                  <button
                    onClick={() => onStartTask(task.id)}
                    className="px-2.5 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium flex items-center gap-1 transition-colors"
                  >
                    <span>Start</span>
                    <ChevronRight className="w-3 h-3" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </section>

        {/* ==================================================
            SECTION 2: PERSONAL TRENDS
            ================================================== */}
        <section aria-labelledby="section-trends" className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 id="section-trends" className="text-sm font-bold text-white uppercase tracking-wider">
              Section 2: Personal Trends
            </h2>
            <span className="text-xs text-slate-400">Baseline Band (mean ± 1 std)</span>
          </div>

          {/* Modality Selector Tabs */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
            {Object.keys(trendMetrics).map((mod) => (
              <button
                key={mod}
                onClick={() => setSelectedModality(mod)}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
                  selectedModality === mod
                    ? 'bg-indigo-600 text-white shadow-md'
                    : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                {mod === 'visual' ? 'Visual' : mod.charAt(0).toUpperCase() + mod.slice(1)}
              </button>
            ))}
          </div>

          {/* Trend Chart Component */}
          <TrendChart {...trendMetrics[selectedModality]} />
        </section>

        {/* ==================================================
            SECTION 3: DEVIATION ALERTS
            ================================================== */}
        <section aria-labelledby="section-deviations" className="space-y-3">
          <h2 id="section-deviations" className="text-sm font-bold text-white uppercase tracking-wider">
            Section 3: Deviation Alerts
          </h2>
          <DeviationAlert
            deviations={deviations}
            onAcknowledge={handleAcknowledgeDeviation}
          />
        </section>

        {/* ==================================================
            SECTION 4: RESEARCH SCREENING RESULT
            ================================================== */}
        <section aria-labelledby="section-screening" className="space-y-3">
          <h2 id="section-screening" className="text-sm font-bold text-white uppercase tracking-wider">
            Section 4: Research Screening Result
          </h2>
          <ScreeningResult
            baselineStatus={baselineStatus}
            calibrationDay={calibrationDay}
          />
        </section>

        {/* ==================================================
            SECTION 5: DATA QUALITY
            ================================================== */}
        <section aria-labelledby="section-quality" className="space-y-3">
          <h2 id="section-quality" className="text-sm font-bold text-white uppercase tracking-wider">
            Section 5: Data Quality
          </h2>
          <DataQualityPanel />
        </section>

        {/* ==================================================
            SECTION 6: PRIVACY & DATA CONTROLS
            ================================================== */}
        <section aria-labelledby="section-privacy" className="space-y-3">
          <h2 id="section-privacy" className="text-sm font-bold text-white uppercase tracking-wider">
            Section 6: Privacy & Data Controls
          </h2>
          <PrivacyControls
            pseudonymousId={pseudonymousId}
            onUpdateConsent={onUpdateConsent}
            onExportData={onExportData}
            onDeleteData={onDeleteData}
          />
        </section>

        {/* Footer & Research Attribution */}
        <footer className="pt-6 border-t border-slate-800 text-center text-xs text-slate-400 space-y-2">
          <div className="font-semibold text-slate-300">
            MPF Mobile Extension — Experimental Multimodal Prodromal Fusion
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed max-w-xs mx-auto">
            Research screening result — not a clinical diagnosis. Developed for observational digital biomarker calibration.
          </p>
          <div className="text-[10px] font-mono text-slate-400 flex items-center justify-center gap-3 pt-1">
            <span>App: v1.0.0</span>
            <span>•</span>
            <span>Baseline Engine: v1.0.0</span>
            <span>•</span>
            <span>Model: v2.1.0-fusion</span>
          </div>
        </footer>

      </div>
    </div>
  );
}

export default DashboardScreen;
