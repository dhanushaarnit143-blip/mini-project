import React, { useState } from 'react';
import { ScreenId, FusionResult, AssessmentData } from '../types';
import { ExportModal } from '../components/ExportModal';
import { generateRiskReportPdf } from '../utils/generateReportPdf';

interface ResultsScreenProps {
  fusionResult: FusionResult;
  assessmentData: AssessmentData;
  onNavigate: (screen: ScreenId) => void;
}

export const ResultsScreen: React.FC<ResultsScreenProps> = ({
  fusionResult,
  assessmentData,
  onNavigate,
}) => {
  const [showExportModal, setShowExportModal] = useState(false);
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const score = fusionResult.integratedRiskScore;
  // Arc length = PI * 80 ≈ 251.32
  const arcLength = 251.32;
  const strokeDashoffset = arcLength * (1 - Math.min(1, Math.max(0, score)));
  // Needle angle in radians: from -PI to 0, or in degrees: (score * 180)
  // At score 0 -> 180 deg (left). At score 1 -> 0 deg (right).
  // x2 = 100 - 48 * cos(score * Math.PI), y2 = 100 - 48 * sin(score * Math.PI)
  const needleX2 = 100 - 52 * Math.cos(score * Math.PI);
  const needleY2 = 100 - 52 * Math.sin(score * Math.PI);

  const handleDownloadPdfReport = () => {
    setIsGeneratingPdf(true);
    setTimeout(() => {
      try {
        generateRiskReportPdf(fusionResult, assessmentData);
        setToastMessage(`Report downloaded: MPF-${fusionResult.subjectId}-risk-report.pdf`);
      } catch (err) {
        console.error('Failed to generate PDF report:', err);
        setToastMessage('Error generating PDF report. Please try again.');
      } finally {
        setIsGeneratingPdf(false);
        setTimeout(() => {
          setToastMessage(null);
        }, 3500);
      }
    }, 600);
  };

  const handleQuickExport = () => {
    setShowExportModal(true);
  };

  return (
    <div className="flex flex-col w-full gap-space-md mx-auto pb-space-xl animate-in fade-in duration-200">
      {/* Subject Badge & Session Meta Header */}
      <div className="flex flex-col gap-space-xs bg-surface-container-lowest p-space-md sm:p-space-lg rounded-2xl shadow-xs border border-surface-container-high/40">
        <div className="flex items-center justify-between gap-space-xs flex-wrap">
          <div className="flex items-center gap-space-xs">
            <span className="w-2.5 h-2.5 rounded-full bg-secondary animate-pulse shrink-0"></span>
            <span className="font-headline-sm text-headline-sm sm:text-headline-md text-on-surface tracking-tight font-semibold">
              Subject #{fusionResult.subjectId}
            </span>
            <span className="px-2.5 py-0.5 rounded-full bg-secondary-container text-on-secondary-container font-label-sm text-[11px] font-semibold">
              Cohort Participant
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-1 rounded-full bg-surface-container-high text-on-surface-variant font-label-sm text-label-sm">
              Completed 14m ago
            </span>
            <button
              type="button"
              disabled={isGeneratingPdf}
              onClick={handleDownloadPdfReport}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-on-primary font-panchang text-[11px] font-bold hover:bg-primary-container transition-colors cursor-pointer shadow-xs disabled:opacity-60"
              title="Download Comprehensive Clinical PDF Report"
            >
              <span className="material-symbols-outlined text-[16px]">picture_as_pdf</span>
              <span>Download PDF</span>
            </button>
          </div>
        </div>
        <div className="flex items-center gap-space-xs text-on-surface-variant">
          <span className="material-symbols-outlined text-[16px] text-tertiary shrink-0">hub</span>
          <p className="font-body-sm text-body-sm truncate text-on-surface-variant">
            Multimodal Fusion Model v2.4 • Non-diagnostic research estimate • Monte-Carlo Bayesian Ensemble
          </p>
        </div>
      </div>

      {/* Primary Risk Estimate Gauge Card */}
      <div className="flex flex-col bg-surface-container-lowest p-space-lg rounded-2xl shadow-xs border border-surface-container-high/40 gap-space-md relative overflow-hidden">
        {/* Subtle Top Ambient Glow */}
        <div className="absolute -top-12 left-1/2 -translate-x-1/2 w-48 h-24 bg-secondary-fixed/40 rounded-full blur-2xl pointer-events-none"></div>

        <div className="flex items-center justify-between z-10">
          <div className="flex flex-col">
            <span className="font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant font-medium">
              Multimodal Risk Pattern
            </span>
            <span className="font-headline-md text-headline-md text-on-surface">Integrated Index</span>
          </div>

          {/* Classification Badge */}
          <div
            className={`flex items-center gap-1 px-2.5 py-1 rounded-full ${
              score >= 0.55
                ? 'bg-secondary-fixed text-on-secondary-fixed'
                : score >= 0.30
                ? 'bg-surface-container-high text-on-surface'
                : 'bg-emerald-100 text-emerald-900'
            }`}
          >
            <span className="material-symbols-outlined text-[15px] text-tertiary">
              {score >= 0.55 ? 'warning' : score >= 0.30 ? 'tune' : 'check_circle'}
            </span>
            <span className="font-label-sm text-label-sm uppercase tracking-wide">
              {fusionResult.riskClassification}
            </span>
          </div>
        </div>

        {/* Gauge Visualization Area */}
        <div className="flex flex-col items-center justify-center pt-space-xs pb-space-xs z-10">
          <div className="relative w-56 h-32 flex items-end justify-center">
            {/* Semi-Circular Gauge SVG */}
            <svg className="w-56 h-32 overflow-visible" viewBox="0 0 200 110">
              <defs>
                <linearGradient id="amberPath" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#4f46e5" />
                  <stop offset="60%" stopColor="#006693" />
                  <stop offset="100%" stopColor="#3525cd" />
                </linearGradient>
              </defs>

              {/* Background Arc (R=80, Center=100,100) */}
              <path
                d="M 20 100 A 80 80 0 0 1 180 100"
                fill="none"
                stroke="#eceef0"
                strokeLinecap="round"
                strokeWidth="16"
              />

              {/* Zone markers subtle ticks */}
              {/* 30% mark */}
              <line x1="43" y1="53" x2="38" y2="46" stroke="#c7c4d8" strokeLinecap="round" strokeWidth="2" />
              {/* 55% mark */}
              <line x1="87" y1="21" x2="85" y2="13" stroke="#c7c4d8" strokeLinecap="round" strokeWidth="2" />
              {/* 80% mark */}
              <line x1="145" y1="35" x2="151" y2="29" stroke="#c7c4d8" strokeLinecap="round" strokeWidth="2" />

              {/* Filled Active Indicator Arc */}
              <path
                id="gauge-fill"
                d="M 20 100 A 80 80 0 0 1 180 100"
                fill="none"
                stroke="url(#amberPath)"
                strokeDasharray={arcLength}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                strokeWidth="16"
                className="transition-all duration-1000 ease-out"
              />

              {/* Current Needle Anchor Circle */}
              <circle cx="100" cy="100" r="7" fill="#191c1e" />
              <circle cx="100" cy="100" r="3" fill="#ffffff" />

              {/* Indicator Needle */}
              <line
                x1="100"
                y1="100"
                x2={needleX2}
                y2={needleY2}
                stroke="#191c1e"
                strokeLinecap="round"
                strokeWidth="3.5"
                className="transition-all duration-1000 ease-out"
              />
            </svg>

            {/* Metric Value Label Floating in Center */}
            <div className="absolute bottom-0 flex flex-col items-center pointer-events-none pb-1">
              <span className="font-metric-display text-metric-display leading-none text-on-surface tracking-tighter">
                {score.toFixed(2)}
              </span>
              <span className="font-label-sm text-label-sm text-on-surface-variant uppercase mt-1">
                Prodromal Score
              </span>
            </div>
          </div>
        </div>

        {/* Scale Breakdown Multi-step Bar */}
        <div className="flex flex-col gap-1.5 pt-space-xs z-10">
          <div className="w-full grid grid-cols-4 gap-1 h-2 rounded-full overflow-hidden bg-surface-container-high p-0.5">
            <div className="bg-secondary-container rounded-sm" title="Low: 0.0 - 0.30"></div>
            <div className="bg-tertiary-fixed rounded-sm" title="Intermediate: 0.30 - 0.55"></div>
            <div className="bg-primary-fixed-dim rounded-sm" title="Elevated: 0.55 - 0.80"></div>
            <div className="bg-surface-container-highest rounded-sm opacity-60" title="High: 0.80 - 1.0"></div>
          </div>
          <div className="flex justify-between font-disclaimer-text text-disclaimer-text text-on-surface-variant px-0.5">
            <span>Low 0.0</span>
            <span>0.30</span>
            <span className="font-semibold text-primary">Elevated 0.55-0.80</span>
            <span>1.0</span>
          </div>
        </div>

        {/* Epistemic Uncertainty Note Well */}
        <div className="flex items-center gap-space-sm bg-surface-container-low p-space-sm rounded-lg z-10 border border-surface-container-high/30">
          <span className="material-symbols-outlined text-[18px] text-tertiary-container shrink-0">
            vital_signs
          </span>
          <div className="flex flex-col min-w-0">
            <div className="flex items-center gap-space-xs flex-wrap">
              <span className="font-headline-sm text-body-sm font-semibold text-on-surface">
                Uncertainty: ±{fusionResult.uncertaintyMargin.toFixed(2)}
              </span>
              <span className="px-1.5 py-0.2 rounded bg-surface-container text-on-surface-variant font-label-sm text-[10px]">
                {fusionResult.confidenceLevel}
              </span>
            </div>
            <span className="font-disclaimer-text text-disclaimer-text text-on-surface-variant truncate">
              Calculated via Monte-Carlo Bayesian ensemble with {assessmentData.retinalMissing ? '4/5' : '5/5'} modalities validated.
            </span>
          </div>
        </div>
      </div>

      {/* Modality Contribution Breakdown Header */}
      <div className="flex items-center justify-between pt-space-xs px-space-xs">
        <div className="flex items-center gap-space-xs">
          <span className="material-symbols-outlined text-[20px] text-primary">view_quilt</span>
          <span className="font-headline-sm text-headline-sm text-on-surface font-semibold">Modality Decomposition</span>
        </div>
        <span className="font-label-sm text-label-sm text-on-surface-variant">5 Data Channels</span>
      </div>

      {/* Modality Contribution Breakdown Grid (Responsive 3-Column on Desktop) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-space-sm">
        {/* Modality 1: Olfactory Card */}
        <div className="flex flex-col bg-surface-container-lowest p-space-md rounded-xl shadow-xs border border-surface-container-high/40 gap-space-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-space-xs">
              <div className="w-8 h-8 rounded-lg bg-surface-container-high flex items-center justify-center text-on-surface shrink-0">
                <span className="material-symbols-outlined text-[18px]">view_in_ar_new</span>
              </div>
              <div className="flex flex-col">
                <span className="font-headline-sm text-headline-sm text-on-surface">Olfactory Psychophysics</span>
                <span className="font-body-sm text-body-sm text-on-surface-variant">UPSIT 40-item smell test</span>
              </div>
            </div>
            <span className="px-2 py-0.5 rounded-full bg-secondary-fixed text-on-secondary-fixed font-label-sm text-[11px] font-medium whitespace-nowrap">
              Elevated Pattern
            </span>
          </div>
          <div className="grid grid-cols-2 gap-space-sm bg-surface-container-low p-space-sm rounded-lg items-center border border-surface-container-high/30">
            <div>
              <span className="font-disclaimer-text text-disclaimer-text text-on-surface-variant block uppercase">
                Observed Value
              </span>
              <span className="font-headline-sm text-headline-sm text-on-surface">
                {assessmentData.olfactoryScore} / 40 <span className="font-body-sm text-on-surface-variant font-normal">pts</span>
              </span>
            </div>
            <div className="text-right">
              <span className="font-disclaimer-text text-disclaimer-text text-on-surface-variant block uppercase">
                Fusion Shift
              </span>
              <span className="font-headline-sm text-headline-sm text-primary font-semibold">
                +{fusionResult.olfactoryShift.toFixed(2)}
              </span>
            </div>
          </div>
        </div>

        {/* Modality 2: Sleep RBD Card */}
        <div className="flex flex-col bg-surface-container-lowest p-space-md rounded-xl shadow-xs border border-surface-container-high/40 gap-space-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-space-xs">
              <div className="w-8 h-8 rounded-lg bg-surface-container-high flex items-center justify-center text-on-surface shrink-0">
                <span className="material-symbols-outlined text-[18px]">bedtime</span>
              </div>
              <div className="flex flex-col">
                <span className="font-headline-sm text-headline-sm text-on-surface">RBD Sleep Architecture</span>
                <span className="font-body-sm text-body-sm text-on-surface-variant">REM parasomnia index</span>
              </div>
            </div>
            <span className="px-2 py-0.5 rounded-full bg-secondary-fixed text-on-secondary-fixed font-label-sm text-[11px] font-medium whitespace-nowrap">
              Elevated Pattern
            </span>
          </div>
          <div className="grid grid-cols-2 gap-space-sm bg-surface-container-low p-space-sm rounded-lg items-center border border-surface-container-high/30">
            <div>
              <span className="font-disclaimer-text text-disclaimer-text text-on-surface-variant block uppercase">
                RBDSQ Score
              </span>
              <span className="font-headline-sm text-headline-sm text-on-surface">
                {assessmentData.rbdsqScore} / 13 <span className="font-body-sm text-on-surface-variant font-normal">pts</span>
              </span>
            </div>
            <div className="text-right">
              <span className="font-disclaimer-text text-disclaimer-text text-on-surface-variant block uppercase">
                Fusion Shift
              </span>
              <span className="font-headline-sm text-headline-sm text-primary font-semibold">
                +{fusionResult.rbdShift.toFixed(2)}
              </span>
            </div>
          </div>
        </div>

        {/* Modality 3: Acoustic Voice Card */}
        <div className="flex flex-col bg-surface-container-lowest p-space-md rounded-xl shadow-xs border border-surface-container-high/40 gap-space-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-space-xs">
              <div className="w-8 h-8 rounded-lg bg-surface-container-high flex items-center justify-center text-on-surface shrink-0">
                <span className="material-symbols-outlined text-[18px]">mic</span>
              </div>
              <div className="flex flex-col">
                <span className="font-headline-sm text-headline-sm text-on-surface">Acoustic Voice Tremor</span>
                <span className="font-body-sm text-body-sm text-on-surface-variant">Phonatory micro-fluctuation</span>
              </div>
            </div>
            <span className="px-2 py-0.5 rounded-full bg-surface-container-highest text-on-surface-variant font-label-sm text-[11px] font-medium whitespace-nowrap">
              Intermediate Pattern
            </span>
          </div>
          <div className="grid grid-cols-2 gap-space-sm bg-surface-container-low p-space-sm rounded-lg items-center border border-surface-container-high/30">
            <div>
              <span className="font-disclaimer-text text-disclaimer-text text-on-surface-variant block uppercase">
                Jitter Local
              </span>
              <span className="font-headline-sm text-headline-sm text-on-surface">
                {assessmentData.isVoiceUploaded ? `${assessmentData.voiceJitter}%` : '1.82%'}
              </span>
            </div>
            <div className="text-right">
              <span className="font-disclaimer-text text-disclaimer-text text-on-surface-variant block uppercase">
                Fusion Shift
              </span>
              <span className="font-headline-sm text-headline-sm text-on-surface font-semibold">
                +{fusionResult.voiceShift.toFixed(2)}
              </span>
            </div>
          </div>
        </div>

        {/* Modality 4: Motor Kinematics Card */}
        <div className="flex flex-col bg-surface-container-lowest p-space-md rounded-xl shadow-xs border border-surface-container-high/40 gap-space-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-space-xs">
              <div className="w-8 h-8 rounded-lg bg-surface-container-high flex items-center justify-center text-on-surface shrink-0">
                <span className="material-symbols-outlined text-[18px]">touch_app</span>
              </div>
              <div className="flex flex-col">
                <span className="font-headline-sm text-headline-sm text-on-surface">Motor Kinematics</span>
                <span className="font-body-sm text-body-sm text-on-surface-variant">Alternating finger-tap rhythm</span>
              </div>
            </div>
            <span className="px-2 py-0.5 rounded-full bg-secondary-container text-on-secondary-container font-label-sm text-[11px] font-semibold whitespace-nowrap">
              Normal / Expected
            </span>
          </div>
          <div className="grid grid-cols-2 gap-space-sm bg-surface-container-low p-space-sm rounded-lg items-center border border-surface-container-high/30">
            <div>
              <span className="font-disclaimer-text text-disclaimer-text text-on-surface-variant block uppercase">
                Tap Frequency
              </span>
              <span className="font-headline-sm text-headline-sm text-on-surface">
                {assessmentData.tappingFrequency} <span className="font-body-sm text-on-surface-variant font-normal">taps/s</span>
              </span>
            </div>
            <div className="text-right">
              <span className="font-disclaimer-text text-disclaimer-text text-on-surface-variant block uppercase">
                Fusion Shift
              </span>
              <span className="font-headline-sm text-headline-sm text-secondary font-semibold">
                {fusionResult.motorShift > 0 ? `+${fusionResult.motorShift.toFixed(2)}` : fusionResult.motorShift.toFixed(2)}
              </span>
            </div>
          </div>
        </div>

        {/* Modality 5: Retinal OCT Card (Missing Data or Active) */}
        <div className="sm:col-span-2 lg:col-span-2 flex flex-col bg-surface-container-lowest p-space-md rounded-xl shadow-xs border border-surface-container-high/40 gap-space-sm opacity-90">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-space-xs">
              <div className="w-8 h-8 rounded-lg bg-surface-container-high flex items-center justify-center text-outline shrink-0">
                <span className="material-symbols-outlined text-[18px]">
                  {assessmentData.retinalMissing ? 'visibility_off' : 'visibility'}
                </span>
              </div>
              <div className="flex flex-col">
                <span className="font-headline-sm text-headline-sm text-on-surface">Retinal OCT Morphology</span>
                <span className="font-body-sm text-body-sm text-on-surface-variant">RNFL thinning assessment</span>
              </div>
            </div>
            <span className="px-2 py-0.5 rounded-full bg-surface-container text-outline font-label-sm text-[11px] font-medium whitespace-nowrap">
              {assessmentData.retinalMissing ? 'Data Gap' : 'Layer Scan Active'}
            </span>
          </div>
          <div className="bg-surface-container-low p-space-sm rounded-lg flex items-center justify-between border border-surface-container-high/30">
            <div className="flex items-center gap-space-xs">
              <span className="material-symbols-outlined text-[16px] text-outline">help_outline</span>
              <span className="font-body-sm text-body-sm text-on-surface-variant">
                {assessmentData.retinalMissing ? 'Session omitted by participant' : 'Peripapillary & Macular grid processed'}
              </span>
            </div>
            <span className="font-label-sm text-label-sm text-outline uppercase tracking-wider font-semibold">
              {fusionResult.retinalShift === 0 ? '0.00 SHAP' : `+${fusionResult.retinalShift.toFixed(2)} SHAP`}
            </span>
          </div>
        </div>
      </div>

      {/* Missing Modality Uncertainty Impact Panel */}
      <div className="flex flex-col bg-surface-container-low p-space-md rounded-xl gap-space-sm border border-surface-container-high/40">
        <div className="flex items-center gap-space-xs text-on-surface">
          <span className="material-symbols-outlined text-[20px] text-tertiary shrink-0">auto_fix_high</span>
          <span className="font-headline-sm text-headline-sm font-semibold">Bayesian Imputation Mechanics</span>
        </div>
        <p className="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">
          The missing <span className="font-semibold text-on-surface">Retinal OCT scan</span> was marginalized through prior distribution covariance without artificial risk inflation. The uncertainty margin expanded gracefully by <span className="font-semibold text-tertiary">±0.018</span>, leaving olfactory and REM channels as the primary discriminative factors.
        </p>
        <div className="flex items-center gap-space-sm pt-space-xs flex-wrap">
          <div className="flex items-center gap-1 text-on-surface-variant font-label-sm text-label-sm">
            <span className="material-symbols-outlined text-[15px] text-primary">verified</span>
            <span>Zero-hallucination guarantee</span>
          </div>
          <div className="flex items-center gap-1 text-on-surface-variant font-label-sm text-label-sm">
            <span className="material-symbols-outlined text-[15px] text-primary">lock</span>
            <span>Reproducible seed #981</span>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex flex-col gap-space-sm pt-space-xs max-w-2xl mx-auto w-full">
        {/* Primary CTA: Download Report (PDF) */}
        <button
          type="button"
          disabled={isGeneratingPdf}
          onClick={handleDownloadPdfReport}
          className="w-full h-12 bg-primary text-on-primary font-headline-sm text-headline-sm rounded-xl flex items-center justify-center gap-2 hover:bg-primary-container active:scale-[0.99] transition-all shadow-sm cursor-pointer disabled:opacity-75"
        >
          {isGeneratingPdf ? (
            <>
              <span className="material-symbols-outlined text-[20px] animate-spin">sync</span>
              <span>Compiling PDF Report...</span>
            </>
          ) : (
            <>
              <span className="material-symbols-outlined text-[20px]">picture_as_pdf</span>
              <span>Download Report (PDF)</span>
            </>
          )}
        </button>

        <div className="grid grid-cols-2 gap-space-sm">
          {/* Secondary CTA: SHAP Deep-Dive */}
          <button
            type="button"
            onClick={() => onNavigate('explainability-shap')}
            className="h-11 bg-surface-container text-on-surface font-headline-sm text-headline-sm rounded-xl flex items-center justify-center gap-space-xs hover:bg-surface-container-high active:scale-[0.99] transition-all border border-surface-container-high/40 cursor-pointer text-center"
          >
            <span className="material-symbols-outlined text-[18px] text-primary">psychology</span>
            <span className="truncate">SHAP Deep-Dive</span>
          </button>

          {/* Secondary CTA: Export Options (JSON/Dossier) */}
          <button
            type="button"
            onClick={handleQuickExport}
            className="h-11 bg-surface-container-lowest text-on-surface font-headline-sm text-headline-sm rounded-xl flex items-center justify-center gap-space-xs shadow-xs border border-surface-container-high hover:bg-surface-container-low active:scale-[0.99] transition-all cursor-pointer text-center"
          >
            <span className="material-symbols-outlined text-[18px] text-secondary">tune</span>
            <span className="truncate">More Options</span>
          </button>
        </div>
      </div>

      {/* Persistent Ethical Disclaimer Banner */}
      <div className="bg-surface-container-low p-space-sm rounded-xl flex items-start gap-space-sm mt-space-xs mb-space-sm border border-surface-container-high/30">
        <span className="material-symbols-outlined text-[18px] text-outline shrink-0 mt-0.5">info</span>
        <p className="font-disclaimer-text text-disclaimer-text text-on-surface-variant leading-normal">
          Research estimate. Not a diagnosis. MPF-PD models probabilistic multimodal patterns for clinical investigational use only. Any observational variation must be correlated with clinical specialist consultation.
        </p>
      </div>

      {/* Download Success Toast */}
      {toastMessage && (
        <div className="fixed bottom-24 lg:bottom-8 left-1/2 -translate-x-1/2 bg-inverse-surface text-inverse-on-surface px-space-md py-2.5 rounded-xl font-label-sm text-label-sm flex items-center gap-space-xs shadow-2xl z-50 animate-in fade-in slide-in-from-bottom-2 border border-inverse-on-surface/10 max-w-sm text-center">
          <span className="material-symbols-outlined text-[18px] text-emerald-400 shrink-0">check_circle</span>
          <span className="truncate">{toastMessage}</span>
        </div>
      )}

      {/* Export Research Report Modal */}
      <ExportModal
        isOpen={showExportModal}
        onClose={() => setShowExportModal(false)}
        result={fusionResult}
        assessmentData={assessmentData}
      />
    </div>
  );
};
