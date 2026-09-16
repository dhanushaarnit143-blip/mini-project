import React, { useState } from 'react';
import { ScreenId, FusionResult, AssessmentData } from '../types';
import { AuditLogModal } from '../components/AuditLogModal';
import { ExportModal } from '../components/ExportModal';

interface ExplainabilityScreenProps {
  fusionResult: FusionResult;
  assessmentData: AssessmentData;
  onNavigate: (screen: ScreenId) => void;
}

export const ExplainabilityScreen: React.FC<ExplainabilityScreenProps> = ({
  fusionResult,
  assessmentData,
  onNavigate,
}) => {
  const [expandedFeatures, setExpandedFeatures] = useState<Record<string, boolean>>({
    olfactory: false,
    rbd: false,
    voice: false,
    age: false,
    motor: false,
  });
  const [showAuditModal, setShowAuditModal] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const toggleFeature = (key: string) => {
    setExpandedFeatures((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const handleExportClick = () => {
    setShowExportModal(true);
  };

  return (
    <div className="flex flex-col w-full gap-space-lg mx-auto pb-space-xl animate-in fade-in duration-200">
      {/* Subject Header Banner */}
      <div className="flex flex-col gap-space-xs bg-surface-container-lowest p-space-lg rounded-2xl shadow-xs border border-surface-container-high/40">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-space-xs">
            <span className="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
            <span className="font-label-sm text-label-sm text-primary uppercase tracking-wider font-semibold">
              Explainable AI • SHAP Attribution
            </span>
          </div>
          <span className="px-2 py-0.5 rounded-full bg-surface-container font-label-sm text-label-sm text-on-surface-variant font-medium">
            TreeSHAP v1.8
          </span>
        </div>

        <div className="flex flex-col mt-space-xs">
          <h1 className="font-headline-xl-mobile text-headline-xl-mobile text-on-surface font-semibold tracking-tight">
            What drove this multimodal risk estimate?
          </h1>
          <p className="font-body-md text-body-md text-on-surface-variant mt-1">
            Quantifying positive and negative risk contributors for Subject #{fusionResult.subjectId}
          </p>
        </div>

        {/* Quick Meta Pills */}
        <div className="flex flex-wrap items-center gap-space-xs mt-space-sm pt-space-sm bg-surface-container-low p-space-sm rounded-xl border border-surface-container-high/30">
          <div className="flex items-center gap-1 text-on-surface-variant">
            <span className="material-symbols-outlined text-[15px] text-primary">fingerprint</span>
            <span className="font-label-sm text-label-sm text-on-surface font-medium">
              Cohort ID: PD-Prodromal-Cohort-B
            </span>
          </div>
          <span className="text-outline-variant">•</span>
          <div className="flex items-center gap-1 text-on-surface-variant">
            <span className="material-symbols-outlined text-[15px] text-tertiary">tune</span>
            <span className="font-label-sm text-label-sm text-on-surface-variant">
              Model Confidence: 94.2%
            </span>
          </div>
        </div>
      </div>

      {/* Main Responsive Layout: 2-Column Grid on Desktop */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-space-lg items-start">
        {/* Left Column (Desktop): Additive Waterfall & Modality Feature Bars */}
        <div className="lg:col-span-7 flex flex-col gap-space-lg">
          {/* Interactive Waterfall Aggregate Card */}
      <div className="flex flex-col bg-surface-container-lowest p-space-lg rounded-2xl shadow-xs border border-surface-container-high/40 gap-space-md">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-space-xs">
            <div className="w-7 h-7 rounded-lg bg-primary-fixed flex items-center justify-center text-primary">
              <span className="material-symbols-outlined text-[18px]">waterfall_chart</span>
            </div>
            <div>
              <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider block">
                Risk Trajectory
              </span>
              <h2 className="font-headline-sm text-headline-sm text-on-surface font-semibold">
                Additive SHAP Waterfall
              </h2>
            </div>
          </div>
          <div className="flex flex-col items-end">
            <span className="font-label-sm text-label-sm text-on-surface-variant">Final Fusion</span>
            <span className="font-metric-display text-headline-xl-mobile font-bold text-primary">
              {fusionResult.integratedRiskScore.toFixed(2)}
            </span>
          </div>
        </div>

        {/* Micro-visual Flow Chart */}
        <div className="bg-surface-container-low p-space-md rounded-xl flex flex-col gap-space-sm border border-surface-container-high/30">
          <div className="flex justify-between items-center text-on-surface-variant font-label-sm text-label-sm">
            <span>Base Population Prior</span>
            <span className="font-semibold text-on-surface">E[f(x)] = 0.05</span>
          </div>

          {/* Progress Track Flow */}
          <div className="w-full bg-surface-container-high h-2.5 rounded-full relative overflow-hidden flex">
            <div className="bg-secondary h-full" style={{ width: '7.3%' }}></div>
            <div className="bg-primary h-full" style={{ width: '41.1%' }}></div>
            <div className="bg-primary-container h-full" style={{ width: '32.3%' }}></div>
            <div className="bg-tertiary h-full" style={{ width: '16.1%' }}></div>
            <div className="bg-secondary-fixed-dim h-full" style={{ width: '10.2%' }}></div>
          </div>

          {/* Steps sequence horizontal scroller */}
          <div className="flex items-center gap-2 overflow-x-auto py-1 text-on-surface-variant no-scrollbar">
            <div className="flex items-center gap-1.5 shrink-0 bg-surface-container px-2.5 py-1 rounded-lg">
              <span className="font-label-sm text-[11px] text-on-surface-variant font-medium">Prior:</span>
              <span className="font-label-sm text-[11px] text-on-surface font-semibold">0.05</span>
            </div>
            <span className="material-symbols-outlined text-[14px] text-outline">arrow_forward</span>

            <div className="flex items-center gap-1.5 shrink-0 bg-primary-fixed px-2.5 py-1 rounded-lg">
              <span className="font-label-sm text-[11px] text-on-primary-fixed font-medium">Olfactory:</span>
              <span className="font-label-sm text-[11px] text-primary font-bold">
                +{fusionResult.olfactoryShift.toFixed(2)}
              </span>
            </div>
            <span className="material-symbols-outlined text-[14px] text-outline">arrow_forward</span>

            <div className="flex items-center gap-1.5 shrink-0 bg-secondary-container px-2.5 py-1 rounded-lg">
              <span className="font-label-sm text-[11px] text-on-secondary-fixed font-medium">RBD:</span>
              <span className="font-label-sm text-[11px] text-primary font-bold">
                +{fusionResult.rbdShift.toFixed(2)}
              </span>
            </div>
            <span className="material-symbols-outlined text-[14px] text-outline">arrow_forward</span>

            <div className="flex items-center gap-1.5 shrink-0 bg-surface-container px-2.5 py-1 rounded-lg">
              <span className="font-label-sm text-[11px] text-on-surface font-medium">Voice:</span>
              <span className="font-label-sm text-[11px] text-tertiary font-bold">
                +{fusionResult.voiceShift.toFixed(2)}
              </span>
            </div>
            <span className="material-symbols-outlined text-[14px] text-outline">arrow_forward</span>

            <div className="flex items-center gap-1.5 shrink-0 bg-surface-container px-2.5 py-1 rounded-lg">
              <span className="font-label-sm text-[11px] text-on-surface font-medium">Motor:</span>
              <span className="font-label-sm text-[11px] text-secondary font-bold">
                {fusionResult.motorShift > 0 ? `+${fusionResult.motorShift.toFixed(2)}` : fusionResult.motorShift.toFixed(2)}
              </span>
            </div>
            <span className="material-symbols-outlined text-[14px] text-outline">equal</span>

            <div className="flex items-center gap-1.5 shrink-0 bg-primary text-on-primary px-3 py-1 rounded-lg shadow-xs">
              <span className="font-label-sm text-[11px] text-on-primary font-medium">Fusion:</span>
              <span className="font-label-sm text-[11px] text-on-primary font-bold">
                {fusionResult.integratedRiskScore.toFixed(2)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Modality Importance Horizontal Feature Attribution Chart */}
      <div className="flex flex-col bg-surface-container-lowest p-space-lg rounded-2xl shadow-xs border border-surface-container-high/40 gap-space-md">
        <div className="flex flex-col gap-1">
          <div className="flex items-center justify-between">
            <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">
              Feature Attribution Vectors
            </span>
            <span className="font-label-sm text-label-sm text-primary font-medium">
              Scale: |ΔP| Probability Impact
            </span>
          </div>
          <h2 className="font-headline-sm text-headline-sm text-on-surface font-semibold">
            Individual Modality Contributions
          </h2>
          <p className="font-body-sm text-body-sm text-on-surface-variant">
            Tap any feature bar below to inspect raw biomarker readings and statistical z-scores.
          </p>
        </div>

        {/* Diverging SHAP Bar Stack */}
        <div className="flex flex-col gap-space-md mt-space-xs">
          {/* Feature 1: Olfactory */}
          <div
            onClick={() => toggleFeature('olfactory')}
            className="group cursor-pointer flex flex-col gap-1 p-space-sm rounded-xl bg-surface-container-low transition-all duration-200 hover:bg-surface-container border border-surface-container-high/30 select-none"
          >
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-space-xs">
                <span className="material-symbols-outlined text-[18px] text-primary">view_in_ar_new</span>
                <span className="font-headline-sm text-headline-sm text-on-surface font-medium">
                  Olfactory Deficit
                </span>
                <span className="px-1.5 py-0.2 rounded bg-surface-container-highest text-on-surface-variant font-label-sm text-[10px]">
                  UPSIT ≤ 18
                </span>
              </div>
              <span className="font-label-md text-label-md text-primary font-bold">
                +{fusionResult.olfactoryShift.toFixed(2)}
              </span>
            </div>

            {/* Bar representation */}
            <div className="w-full bg-surface-container-high h-3 rounded-full overflow-hidden flex">
              <div className="bg-primary h-full rounded-full transition-all duration-500" style={{ width: '82%' }}></div>
            </div>

            <div className="flex justify-between items-center text-on-surface-variant font-body-sm text-body-sm pt-0.5">
              <span>Severe hyposmia pattern</span>
              <span className="text-primary font-label-sm text-[11px] font-medium flex items-center gap-0.5">
                <span>{expandedFeatures.olfactory ? 'Collapse telemetry' : 'Expand telemetry'}</span>
                <span
                  className="material-symbols-outlined text-[14px] transition-transform"
                  style={{ transform: expandedFeatures.olfactory ? 'rotate(180deg)' : 'rotate(0deg)' }}
                >
                  expand_more
                </span>
              </span>
            </div>

            {/* Collapsible detail pane */}
            {expandedFeatures.olfactory && (
              <div className="flex flex-col gap-space-xs pt-space-sm mt-space-xs bg-surface-container-lowest p-space-sm rounded-lg border border-surface-container-high/40 animate-in fade-in duration-150">
                <div className="grid grid-cols-2 gap-2 text-on-surface">
                  <div className="flex flex-col">
                    <span className="font-label-sm text-label-sm text-on-surface-variant">Standardized Score</span>
                    <span className="font-headline-sm text-headline-sm font-semibold">
                      {assessmentData.olfactoryScore} / 40 (Age-adj &lt; 5th percentile)
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className="font-label-sm text-label-sm text-on-surface-variant">Cross-Entropy Gain</span>
                    <span className="font-headline-sm text-headline-sm font-semibold">+0.34 nat</span>
                  </div>
                </div>
                <p className="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">
                  Primary driver: Olfactory bulb signaling dysregulation matches classic prodromal Lewy body spectrum markers.
                </p>
              </div>
            )}
          </div>

          {/* Feature 2: REM Sleep Behavior Disorder */}
          <div
            onClick={() => toggleFeature('rbd')}
            className="group cursor-pointer flex flex-col gap-1 p-space-sm rounded-xl bg-surface-container-low transition-all duration-200 hover:bg-surface-container border border-surface-container-high/30 select-none"
          >
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-space-xs">
                <span className="material-symbols-outlined text-[18px] text-primary-container">bedtime</span>
                <span className="font-headline-sm text-headline-sm text-on-surface font-medium">
                  REM Sleep Behavior Disorder
                </span>
                <span className="px-1.5 py-0.2 rounded bg-surface-container-highest text-on-surface-variant font-label-sm text-[10px]">
                  RBDSQ ≥ 8
                </span>
              </div>
              <span className="font-label-md text-label-md text-primary-container font-bold">
                +{fusionResult.rbdShift.toFixed(2)}
              </span>
            </div>

            <div className="w-full bg-surface-container-high h-3 rounded-full overflow-hidden flex">
              <div className="bg-primary-container h-full rounded-full transition-all duration-500" style={{ width: '65%' }}></div>
            </div>

            <div className="flex justify-between items-center text-on-surface-variant font-body-sm text-body-sm pt-0.5">
              <span>High motor dream reenactment</span>
              <span className="text-primary font-label-sm text-[11px] font-medium flex items-center gap-0.5">
                <span>{expandedFeatures.rbd ? 'Collapse telemetry' : 'Expand telemetry'}</span>
                <span
                  className="material-symbols-outlined text-[14px] transition-transform"
                  style={{ transform: expandedFeatures.rbd ? 'rotate(180deg)' : 'rotate(0deg)' }}
                >
                  expand_more
                </span>
              </span>
            </div>

            {expandedFeatures.rbd && (
              <div className="flex flex-col gap-space-xs pt-space-sm mt-space-xs bg-surface-container-lowest p-space-sm rounded-lg border border-surface-container-high/40 animate-in fade-in duration-150">
                <div className="grid grid-cols-2 gap-2 text-on-surface">
                  <div className="flex flex-col">
                    <span className="font-label-sm text-label-sm text-on-surface-variant">RBDSQ Metric</span>
                    <span className="font-headline-sm text-headline-sm font-semibold">
                      {assessmentData.rbdsqScore}.0 points (Threshold: 5.0)
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className="font-label-sm text-label-sm text-on-surface-variant">Polysomnography</span>
                    <span className="font-headline-sm text-headline-sm font-semibold">RSWA Confirmed (28.4%)</span>
                  </div>
                </div>
                <p className="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">
                  Loss of physiological REM atonia observed across 3 consecutive longitudinal sensor recording cycles.
                </p>
              </div>
            )}
          </div>

          {/* Feature 3: Voice Acoustic Biomarker */}
          <div
            onClick={() => toggleFeature('voice')}
            className="group cursor-pointer flex flex-col gap-1 p-space-sm rounded-xl bg-surface-container-low transition-all duration-200 hover:bg-surface-container border border-surface-container-high/30 select-none"
          >
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-space-xs">
                <span className="material-symbols-outlined text-[18px] text-tertiary">mic</span>
                <span className="font-headline-sm text-headline-sm text-on-surface font-medium">
                  Voice Vocal Tremor &amp; CPP
                </span>
                <span className="px-1.5 py-0.2 rounded bg-surface-container-highest text-on-surface-variant font-label-sm text-[10px]">
                  Acoustic Jitter
                </span>
              </div>
              <span className="font-label-md text-label-md text-tertiary font-bold">
                +{fusionResult.voiceShift.toFixed(2)}
              </span>
            </div>

            <div className="w-full bg-surface-container-high h-3 rounded-full overflow-hidden flex">
              <div className="bg-tertiary h-full rounded-full transition-all duration-500" style={{ width: '32%' }}></div>
            </div>

            <div className="flex justify-between items-center text-on-surface-variant font-body-sm text-body-sm pt-0.5">
              <span>Mild phonatory micro-instability</span>
              <span className="text-primary font-label-sm text-[11px] font-medium flex items-center gap-0.5">
                <span>{expandedFeatures.voice ? 'Collapse telemetry' : 'Expand telemetry'}</span>
                <span
                  className="material-symbols-outlined text-[14px] transition-transform"
                  style={{ transform: expandedFeatures.voice ? 'rotate(180deg)' : 'rotate(0deg)' }}
                >
                  expand_more
                </span>
              </span>
            </div>

            {expandedFeatures.voice && (
              <div className="flex flex-col gap-space-xs pt-space-sm mt-space-xs bg-surface-container-lowest p-space-sm rounded-lg border border-surface-container-high/40 animate-in fade-in duration-150">
                <div className="grid grid-cols-2 gap-2 text-on-surface">
                  <div className="flex flex-col">
                    <span className="font-label-sm text-label-sm text-on-surface-variant">Smoothed Cepstral Peak</span>
                    <span className="font-headline-sm text-headline-sm font-semibold">11.2 dB (Marginal low)</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="font-label-sm text-label-sm text-on-surface-variant">Fundamental Freq F0</span>
                    <span className="font-headline-sm text-headline-sm font-semibold">Tremor modulation 4.1 Hz</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Feature 4: Age Covariate */}
          <div
            onClick={() => toggleFeature('age')}
            className="group cursor-pointer flex flex-col gap-1 p-space-sm rounded-xl bg-surface-container-low transition-all duration-200 hover:bg-surface-container border border-surface-container-high/30 select-none"
          >
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-space-xs">
                <span className="material-symbols-outlined text-[18px] text-secondary">calendar_today</span>
                <span className="font-headline-sm text-headline-sm text-on-surface font-medium">
                  Age Covariate
                </span>
                <span className="px-1.5 py-0.2 rounded bg-surface-container-highest text-on-surface-variant font-label-sm text-[10px]">
                  {assessmentData.age} Years
                </span>
              </div>
              <span className="font-label-md text-label-md text-secondary font-bold">
                +{fusionResult.ageShift.toFixed(2)}
              </span>
            </div>

            <div className="w-full bg-surface-container-high h-3 rounded-full overflow-hidden flex">
              <div className="bg-secondary h-full rounded-full transition-all duration-500" style={{ width: '21%' }}></div>
            </div>

            <div className="flex justify-between items-center text-on-surface-variant font-body-sm text-body-sm pt-0.5">
              <span>Non-modifiable cohort prior shift</span>
              <span className="text-primary font-label-sm text-[11px] font-medium flex items-center gap-0.5">
                <span>{expandedFeatures.age ? 'Collapse telemetry' : 'Expand telemetry'}</span>
                <span
                  className="material-symbols-outlined text-[14px] transition-transform"
                  style={{ transform: expandedFeatures.age ? 'rotate(180deg)' : 'rotate(0deg)' }}
                >
                  expand_more
                </span>
              </span>
            </div>

            {expandedFeatures.age && (
              <div className="flex flex-col gap-space-xs pt-space-sm mt-space-xs bg-surface-container-lowest p-space-sm rounded-lg border border-surface-container-high/40 animate-in fade-in duration-150">
                <p className="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">
                  Calculated against standard epidemiological baseline using European multicenter longitudinal registries.
                </p>
              </div>
            )}
          </div>

          {/* Feature 5: Motor Alternating Tapping Speed (Protective / Negative impact) */}
          <div
            onClick={() => toggleFeature('motor')}
            className="group cursor-pointer flex flex-col gap-1 p-space-sm rounded-xl bg-surface-container-low transition-all duration-200 hover:bg-surface-container border border-surface-container-high/30 select-none"
          >
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-space-xs">
                <span className="material-symbols-outlined text-[18px] text-secondary-fixed-dim">touch_app</span>
                <span className="font-headline-sm text-headline-sm text-on-surface font-medium">
                  Motor Alternating Tapping
                </span>
                <span className="px-1.5 py-0.2 rounded bg-surface-container-highest text-on-surface-variant font-label-sm text-[10px]">
                  Speed &amp; Rhythm
                </span>
              </div>
              <span className="font-label-md text-label-md text-secondary-fixed-dim font-bold">
                {fusionResult.motorShift > 0 ? `+${fusionResult.motorShift.toFixed(2)}` : fusionResult.motorShift.toFixed(2)}
              </span>
            </div>

            {/* Protective bar with divergent styling */}
            <div className="w-full bg-surface-container-high h-3 rounded-full overflow-hidden flex justify-end">
              <div className="bg-secondary-fixed-dim h-full rounded-full transition-all duration-500" style={{ width: '15%' }}></div>
            </div>

            <div className="flex justify-between items-center text-on-surface-variant font-body-sm text-body-sm pt-0.5">
              <span className="text-secondary font-medium">Protective / Offset: Preserved speed</span>
              <span className="text-primary font-label-sm text-[11px] font-medium flex items-center gap-0.5">
                <span>{expandedFeatures.motor ? 'Collapse telemetry' : 'Expand telemetry'}</span>
                <span
                  className="material-symbols-outlined text-[14px] transition-transform"
                  style={{ transform: expandedFeatures.motor ? 'rotate(180deg)' : 'rotate(0deg)' }}
                >
                  expand_more
                </span>
              </span>
            </div>

            {expandedFeatures.motor && (
              <div className="flex flex-col gap-space-xs pt-space-sm mt-space-xs bg-surface-container-lowest p-space-sm rounded-lg border border-surface-container-high/40 animate-in fade-in duration-150">
                <div className="grid grid-cols-2 gap-2 text-on-surface">
                  <div className="flex flex-col">
                    <span className="font-label-sm text-label-sm text-on-surface-variant">Tap Interval Mean</span>
                    <span className="font-headline-sm text-headline-sm font-semibold">184 ms (Well within bounds)</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="font-label-sm text-label-sm text-on-surface-variant">Kinetic Fatigue Coefficient</span>
                    <span className="font-headline-sm text-headline-sm font-semibold">0.02 (Normative resilience)</span>
                  </div>
                </div>
                <p className="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">
                  Upper-limb kinematic cadence lacks bradykinetic decline, partially mitigating global fusion trajectory.
                </p>
              </div>
            )}
          </div>

          {/* Feature 6: Retinal RNFL Thickness (Unobserved / Missing) */}
          <div className="flex flex-col gap-1 p-space-sm rounded-xl bg-surface-container-low opacity-80 border border-surface-container-high/30">
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-space-xs">
                <span className="material-symbols-outlined text-[18px] text-outline">
                  {assessmentData.retinalMissing ? 'visibility_off' : 'visibility'}
                </span>
                <span className="font-headline-sm text-headline-sm text-on-surface-variant font-medium">
                  Retinal RNFL Thickness
                </span>
                <span className="px-1.5 py-0.2 rounded bg-surface-container text-on-surface-variant font-label-sm text-[10px]">
                  OCT Layer
                </span>
              </div>
              <span className="font-label-md text-label-md text-outline font-bold">
                {fusionResult.retinalShift === 0 ? '0.00' : `+${fusionResult.retinalShift.toFixed(2)}`}
              </span>
            </div>
            <div className="w-full bg-surface-container-high h-2 rounded-full overflow-hidden flex">
              <div
                className="bg-outline-variant h-full"
                style={{ width: assessmentData.retinalMissing ? '0%' : '18%' }}
              ></div>
            </div>
            <div className="flex justify-between items-center text-outline font-body-sm text-body-sm pt-0.5">
              <span>
                {assessmentData.retinalMissing
                  ? 'Unobserved modality (Modality missing at test time)'
                  : 'Acquired macular scan active'}
              </span>
              <span className="font-label-sm text-[10px] uppercase tracking-wider text-outline">
                {assessmentData.retinalMissing ? 'Priors Assigned' : 'Observed'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Interactive Research Alerts Section */}
      <div className="flex flex-col gap-space-sm">
        <div className="flex items-center gap-space-xs px-1">
          <span className="material-symbols-outlined text-primary text-[18px]">verified_user</span>
          <span className="font-label-sm text-label-sm text-on-surface uppercase tracking-wider font-semibold">
            Active Research Alert Stream
          </span>
        </div>

        {/* Alert 1 */}
        <div className="flex flex-col bg-surface-container-lowest p-space-md rounded-xl shadow-xs border border-surface-container-high/40 gap-space-xs">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-space-xs">
              <div className="w-6 h-6 rounded-md bg-secondary-container flex items-center justify-center text-on-secondary-container">
                <span className="material-symbols-outlined text-[16px]">sync_problem</span>
              </div>
              <span className="font-headline-sm text-headline-sm text-on-surface font-semibold">
                Concordant Phenotype
              </span>
            </div>
            <span className="px-2 py-0.5 rounded-full bg-secondary-container text-on-secondary-container font-label-sm text-label-sm font-semibold">
              High Synergy
            </span>
          </div>
          <p className="font-body-md text-body-md text-on-surface-variant">
            Olfactory &amp; Sleep concordant prodromal marker pattern detected.
          </p>
          <div className="flex items-center gap-2 pt-1 flex-wrap">
            <span className="font-body-sm text-body-sm text-tertiary">Co-activation index: 0.88</span>
            <span className="text-outline-variant">•</span>
            <span className="font-body-sm text-body-sm text-on-surface-variant">
              Cross-modal interaction amplifies baseline risk ratio by 1.4x
            </span>
          </div>
        </div>

        {/* Alert 2 */}
        {assessmentData.retinalMissing && (
          <div className="flex flex-col bg-surface-container-lowest p-space-md rounded-xl shadow-xs border border-surface-container-high/40 gap-space-xs">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-space-xs">
                <div className="w-6 h-6 rounded-md bg-surface-container-highest flex items-center justify-center text-on-surface-variant">
                  <span className="material-symbols-outlined text-[16px]">warning</span>
                </div>
                <span className="font-headline-sm text-headline-sm text-on-surface font-semibold">
                  Epistemic Uncertainty Expanded
                </span>
              </div>
              <span className="px-2 py-0.5 rounded-full bg-surface-container text-on-surface-variant font-label-sm text-label-sm font-semibold">
                Variance Shift
              </span>
            </div>
            <p className="font-body-md text-body-md text-on-surface-variant">
              Retinal biomarker missing: Epistemic uncertainty margin expanded from ±0.03 to ±0.06.
            </p>
            <div className="flex items-center gap-2 pt-1">
              <span className="font-body-sm text-body-sm text-on-surface-variant">
                Recommend acquiring spectral OCT imaging if cohort criteria requires tight variance bounds.
              </span>
            </div>
          </div>
        )}
      </div>
        </div>

        {/* Right Column (Desktop): Imagery, Clinical Recommendations, Governance */}
        <div className="lg:col-span-5 flex flex-col gap-space-lg">
          {/* Visual Scientific Imagery Placeholder */}
      <div className="relative w-full rounded-2xl overflow-hidden shadow-xs bg-surface-container-low border border-surface-container-high/40">
        <div
          className="bg-cover bg-center w-full h-36 relative"
          style={{
            backgroundImage: `url('https://lh3.googleusercontent.com/aida-public/AB6AXuBbJwEnPEmDIVXKif-2ib_UNajJgpZ07m7TGEkkE_l3k6xigm8cqRU7jZqJPUBsAZW6Q_-_jjH-F13s-38bVUCk0IBTmcGl7aQzgbBewNXrWynHp3HkNrxV8SRUnLdmmpM1iVwjoinJjbDLWFLf5P44OUSk-_qzp1EODuDL2Z9DBnwOc-bLzPjSOugryFY1tMuMivPS3xliF_sUoFzVfABchqHo4c88rur5TL-sdiPzq1Obv_IxzlC4')`,
          }}
        >
          <div className="absolute inset-0 bg-gradient-to-t from-surface-container-lowest via-surface-container-lowest/40 to-transparent flex items-end p-space-md">
            <div className="flex items-center justify-between w-full">
              <div className="flex flex-col">
                <span className="font-label-sm text-[10px] uppercase tracking-wider text-primary font-bold">
                  Multimodal Latent Space
                </span>
                <span className="font-headline-sm text-headline-sm text-on-surface font-semibold">
                  Projection Geometry v2.4
                </span>
              </div>
              <span className="material-symbols-outlined text-primary text-[20px]">hub</span>
            </div>
          </div>
        </div>
      </div>

      {/* Clinical Research Next Steps / Context Panel */}
      <div className="flex flex-col bg-surface-container-lowest p-space-lg rounded-2xl shadow-xs border border-surface-container-high/40 gap-space-md">
        <div className="flex items-center gap-space-xs">
          <div className="w-7 h-7 rounded-lg bg-primary text-on-primary flex items-center justify-center">
            <span className="material-symbols-outlined text-[18px]">clinical_notes</span>
          </div>
          <div>
            <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider block">
              Contextual Interpretation
            </span>
            <h3 className="font-headline-sm text-headline-sm text-on-surface font-semibold">
              Clinical Research Next Steps
            </h3>
          </div>
        </div>

        {/* Observation / Evidence / Action cards */}
        <div className="flex flex-col gap-space-sm">
          <div className="p-space-md rounded-xl bg-surface-container-low flex flex-col gap-1 border border-surface-container-high/30">
            <div className="flex items-center gap-1.5 text-primary">
              <span className="material-symbols-outlined text-[16px]">visibility</span>
              <span className="font-label-sm text-label-sm font-semibold uppercase tracking-wider">
                Clinical Observation
              </span>
            </div>
            <p className="font-body-md text-body-md text-on-surface">
              Elevated risk pattern observed predominantly in Olfactory and RBD modalities.
            </p>
          </div>

          <div className="p-space-md rounded-xl bg-surface-container-low flex flex-col gap-1 border border-surface-container-high/30">
            <div className="flex items-center gap-1.5 text-tertiary">
              <span className="material-symbols-outlined text-[16px]">rule</span>
              <span className="font-label-sm text-label-sm font-semibold uppercase tracking-wider">
                Consensus Evidence
              </span>
            </div>
            <p className="font-body-md text-body-md text-on-surface">
              Scores exceed validated age-adjusted prodromal research criteria (MDS prodromal threshold &gt; 80% likelihood ratio).
            </p>
          </div>

          <div className="p-space-md rounded-xl bg-primary-fixed flex flex-col gap-1 text-on-primary-fixed border border-primary/20">
            <div className="flex items-center gap-1.5 text-primary">
              <span className="material-symbols-outlined text-[16px]">assignment_turned_in</span>
              <span className="font-label-sm text-label-sm font-semibold uppercase tracking-wider text-primary">
                Actionable Recommendation
              </span>
            </div>
            <p className="font-body-md text-body-md text-on-primary-fixed font-medium leading-relaxed">
              Consider longitudinal follow-up in 6 months with DaTscan or biomarker re-test in an approved academic protocol.
            </p>
          </div>
        </div>

        {/* Export Actions */}
        <div className="flex gap-space-sm pt-space-xs">
          <button
            type="button"
            onClick={handleExportClick}
            className="flex-1 h-10 px-4 rounded-lg bg-primary text-on-primary font-label-md text-label-md font-semibold flex items-center justify-center gap-2 hover:bg-primary-container transition-colors shadow-xs cursor-pointer active:scale-98"
          >
            <span className="material-symbols-outlined text-[18px]">download</span>
            <span>Export SHAP Dossier</span>
          </button>

          <button
            type="button"
            onClick={() => setShowAuditModal(true)}
            className="h-10 px-4 rounded-lg bg-surface-container text-on-surface font-label-md text-label-md font-medium flex items-center justify-center gap-1.5 hover:bg-surface-container-highest transition-colors cursor-pointer active:scale-98 border border-surface-container-high/40"
          >
            <span className="material-symbols-outlined text-[18px]">policy</span>
            <span>Audit Log</span>
          </button>
        </div>
      </div>

      {/* Research Disclaimer & Ethics Banner */}
      <div className="flex items-start gap-space-sm bg-surface-container p-space-md rounded-xl text-on-surface-variant border border-surface-container-high/40">
        <span className="material-symbols-outlined text-[20px] text-tertiary shrink-0 mt-0.5">verified</span>
        <div className="flex flex-col gap-0.5">
          <span className="font-label-sm text-label-sm text-on-surface font-semibold uppercase tracking-wider">
            Ethics &amp; Protocol Governance
          </span>
          <p className="font-disclaimer-text text-disclaimer-text text-on-surface-variant leading-relaxed">
            Research estimate. Not a diagnosis. MPF-PD models probabilistic multimodal patterns for clinical investigational use only. Calculations do not constitute diagnostic medical decisions or guarantee neurodegenerative conversion. Study institutional IRB Protocol: #2024-IRB-8821.
          </p>
        </div>
      </div>
        </div>
      </div>

      {/* Audit Log Modal */}
      <AuditLogModal
        isOpen={showAuditModal}
        onClose={() => setShowAuditModal(false)}
        subjectId={fusionResult.subjectId}
      />

      {/* Export SHAP Dossier Modal */}
      <ExportModal
        isOpen={showExportModal}
        onClose={() => setShowExportModal(false)}
        result={fusionResult}
      />
    </div>
  );
};
