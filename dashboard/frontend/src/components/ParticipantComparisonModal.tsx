import React, { useMemo } from 'react';
import { CohortParticipant } from '../types';
import { calculateMultimodalRisk } from '../utils/riskModel';

interface ParticipantComparisonModalProps {
  isOpen: boolean;
  onClose: () => void;
  participantA: CohortParticipant;
  participantB: CohortParticipant;
  onSelectParticipant: (participant: CohortParticipant) => void;
  onSwap?: () => void;
}

export const ParticipantComparisonModal: React.FC<ParticipantComparisonModalProps> = ({
  isOpen,
  onClose,
  participantA,
  participantB,
  onSelectParticipant,
  onSwap,
}) => {
  if (!isOpen || !participantA || !participantB) return null;

  const fusionA = useMemo(() => calculateMultimodalRisk(participantA.assessmentData), [participantA]);
  const fusionB = useMemo(() => calculateMultimodalRisk(participantB.assessmentData), [participantB]);

  const riskDelta = Number((participantA.riskIndex - participantB.riskIndex).toFixed(2));
  const absDelta = Math.abs(riskDelta);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-black/50 backdrop-blur-xs animate-in fade-in"
      onClick={onClose}
    >
      <div
        className="bg-surface-container-lowest rounded-2xl shadow-2xl border border-surface-container-high w-full max-w-3xl max-h-[92vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between p-4 sm:p-5 border-b border-surface-container-high bg-surface-container-low shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-primary-fixed flex items-center justify-center text-primary shrink-0">
              <span className="material-symbols-outlined text-[20px]">compare_arrows</span>
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span className="font-panchang text-xs sm:text-sm font-bold text-on-surface">
                  Cohort Risk Profile Comparison
                </span>
                <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary font-panchang text-[9px] font-bold">
                  Side-by-Side
                </span>
              </div>
              <span className="font-panchang text-[10px] text-on-surface-variant">
                Cross-modal phenotype divergence &amp; SHAP attribution
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {onSwap && (
              <button
                type="button"
                onClick={onSwap}
                className="px-2.5 py-1 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface font-panchang text-[10px] font-semibold flex items-center gap-1 transition-colors cursor-pointer"
                title="Swap column positions"
              >
                <span className="material-symbols-outlined text-[14px]">swap_horiz</span>
                <span className="hidden sm:inline">Swap</span>
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="text-on-surface-variant hover:text-on-surface p-1 rounded-lg hover:bg-surface-container transition-colors cursor-pointer"
              title="Close comparison"
            >
              <span className="material-symbols-outlined text-[20px]">close</span>
            </button>
          </div>
        </div>

        {/* Scrollable Content Body */}
        <div className="overflow-y-auto p-4 sm:p-6 flex flex-col gap-space-md text-xs">
          {/* Top Column Identity Cards */}
          <div className="grid grid-cols-2 gap-3 sm:gap-4">
            {/* Participant A Identity */}
            <div className="bg-surface-container-low p-space-md rounded-xl border border-surface-container-high flex flex-col gap-2 relative">
              <div className="flex items-center justify-between">
                <span className="px-2 py-0.5 rounded bg-primary text-on-primary font-panchang text-[9px] font-bold">
                  Participant A
                </span>
                <span className="font-panchang text-[10px] text-on-surface-variant font-medium">
                  {participantA.visit}
                </span>
              </div>
              <div className="flex items-center gap-2.5 mt-0.5">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
                    participantA.avatarType === 'amber'
                      ? 'bg-amber-100 text-amber-800'
                      : participantA.avatarType === 'emerald'
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-surface-container-high text-on-surface-variant'
                  }`}
                >
                  <span className="material-symbols-outlined text-[20px]">
                    {participantA.avatarType === 'amber'
                      ? 'warning_amber'
                      : participantA.avatarType === 'emerald'
                      ? 'check_circle'
                      : 'tune'}
                  </span>
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="font-panchang text-sm font-bold text-on-surface truncate">
                    {participantA.id}
                  </span>
                  <span className="font-panchang text-[10px] text-on-surface-variant">
                    {participantA.assessmentData.age}y • {participantA.assessmentData.biologicalSex} • {participantA.assessmentData.familyHistory ? 'Fam. Hist. (+)' : 'No Fam. Hist.'}
                  </span>
                </div>
              </div>
              <p className="font-panchang text-[10px] text-on-surface-variant italic line-clamp-2">
                &ldquo;{participantA.notes}&rdquo;
              </p>
              <button
                type="button"
                onClick={() => onSelectParticipant(participantA)}
                className="mt-1 w-full py-1.5 px-2 rounded-lg bg-surface-container-highest hover:bg-primary hover:text-on-primary text-on-surface font-panchang text-[10px] font-bold transition-all text-center flex items-center justify-center gap-1 cursor-pointer"
              >
                <span>Inspect in Dashboard</span>
                <span className="material-symbols-outlined text-[13px]">open_in_new</span>
              </button>
            </div>

            {/* Participant B Identity */}
            <div className="bg-surface-container-low p-space-md rounded-xl border border-surface-container-high flex flex-col gap-2 relative">
              <div className="flex items-center justify-between">
                <span className="px-2 py-0.5 rounded bg-secondary text-on-secondary font-panchang text-[9px] font-bold">
                  Participant B
                </span>
                <span className="font-panchang text-[10px] text-on-surface-variant font-medium">
                  {participantB.visit}
                </span>
              </div>
              <div className="flex items-center gap-2.5 mt-0.5">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
                    participantB.avatarType === 'amber'
                      ? 'bg-amber-100 text-amber-800'
                      : participantB.avatarType === 'emerald'
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-surface-container-high text-on-surface-variant'
                  }`}
                >
                  <span className="material-symbols-outlined text-[20px]">
                    {participantB.avatarType === 'amber'
                      ? 'warning_amber'
                      : participantB.avatarType === 'emerald'
                      ? 'check_circle'
                      : 'tune'}
                  </span>
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="font-panchang text-sm font-bold text-on-surface truncate">
                    {participantB.id}
                  </span>
                  <span className="font-panchang text-[10px] text-on-surface-variant">
                    {participantB.assessmentData.age}y • {participantB.assessmentData.biologicalSex} • {participantB.assessmentData.familyHistory ? 'Fam. Hist. (+)' : 'No Fam. Hist.'}
                  </span>
                </div>
              </div>
              <p className="font-panchang text-[10px] text-on-surface-variant italic line-clamp-2">
                &ldquo;{participantB.notes}&rdquo;
              </p>
              <button
                type="button"
                onClick={() => onSelectParticipant(participantB)}
                className="mt-1 w-full py-1.5 px-2 rounded-lg bg-surface-container-highest hover:bg-secondary hover:text-on-secondary text-on-surface font-panchang text-[10px] font-bold transition-all text-center flex items-center justify-center gap-1 cursor-pointer"
              >
                <span>Inspect in Dashboard</span>
                <span className="material-symbols-outlined text-[13px]">open_in_new</span>
              </button>
            </div>
          </div>

          {/* Integrated Risk Index Comparison Bar */}
          <div className="bg-surface-container-lowest p-space-md rounded-xl border border-surface-container-high shadow-xs flex flex-col gap-space-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[18px] text-primary">speed</span>
                <span className="font-panchang text-[11px] font-bold text-on-surface">
                  Integrated Prodromal Risk Index
                </span>
              </div>
              <span className="font-panchang text-[10px] font-bold px-2 py-0.5 rounded-full bg-surface-container text-on-surface">
                Δ {riskDelta > 0 ? `+${riskDelta.toFixed(2)}` : riskDelta.toFixed(2)} {riskDelta !== 0 ? `(${riskDelta > 0 ? participantA.id : participantB.id} higher)` : '(Equal)'}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 sm:gap-4 pt-1">
              {/* Score A */}
              <div className="flex flex-col gap-1.5">
                <div className="flex items-baseline justify-between">
                  <span className="font-panchang text-xl sm:text-2xl font-bold text-on-surface">
                    {participantA.riskIndex.toFixed(2)}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded-full font-panchang text-[9px] font-bold ${
                      participantA.riskClass === 'Elevated Pattern'
                        ? 'bg-amber-100 text-amber-900'
                        : participantA.riskClass === 'Low Risk Pattern'
                        ? 'bg-emerald-100 text-emerald-900'
                        : 'bg-secondary-container text-on-secondary-container'
                    }`}
                  >
                    {participantA.riskClass}
                  </span>
                </div>
                {/* Visual Bar A */}
                <div className="h-2.5 w-full bg-surface-container rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      participantA.riskIndex >= 0.55 ? 'bg-amber-500' : participantA.riskIndex >= 0.3 ? 'bg-secondary' : 'bg-emerald-500'
                    }`}
                    style={{ width: `${Math.min(100, Math.max(5, participantA.riskIndex * 100))}%` }}
                  />
                </div>
                <span className="font-panchang text-[9px] text-on-surface-variant">
                  Uncertainty: ±{fusionA.uncertaintyMargin.toFixed(2)} ({fusionA.confidenceLevel})
                </span>
              </div>

              {/* Score B */}
              <div className="flex flex-col gap-1.5">
                <div className="flex items-baseline justify-between">
                  <span className="font-panchang text-xl sm:text-2xl font-bold text-on-surface">
                    {participantB.riskIndex.toFixed(2)}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded-full font-panchang text-[9px] font-bold ${
                      participantB.riskClass === 'Elevated Pattern'
                        ? 'bg-amber-100 text-amber-900'
                        : participantB.riskClass === 'Low Risk Pattern'
                        ? 'bg-emerald-100 text-emerald-900'
                        : 'bg-secondary-container text-on-secondary-container'
                    }`}
                  >
                    {participantB.riskClass}
                  </span>
                </div>
                {/* Visual Bar B */}
                <div className="h-2.5 w-full bg-surface-container rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      participantB.riskIndex >= 0.55 ? 'bg-amber-500' : participantB.riskIndex >= 0.3 ? 'bg-secondary' : 'bg-emerald-500'
                    }`}
                    style={{ width: `${Math.min(100, Math.max(5, participantB.riskIndex * 100))}%` }}
                  />
                </div>
                <span className="font-panchang text-[9px] text-on-surface-variant">
                  Uncertainty: ±{fusionB.uncertaintyMargin.toFixed(2)} ({fusionB.confidenceLevel})
                </span>
              </div>
            </div>
          </div>

          {/* Modality by Modality SHAP & Biomarker Breakdown Table */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="font-panchang text-[11px] font-bold text-on-surface flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[18px] text-tertiary">tune</span>
                Cross-Modal Biomarkers &amp; SHAP Decomposition
              </span>
              <span className="font-panchang text-[9px] text-on-surface-variant">
                Δ SHAP Shift (Risk Attribution)
              </span>
            </div>

            <div className="flex flex-col gap-2">
              {/* Row 1: Olfactory */}
              <div className="bg-surface-container-low p-space-sm rounded-xl border border-surface-container-high/60 flex flex-col gap-1.5">
                <div className="flex items-center justify-between text-on-surface">
                  <div className="flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[16px] text-primary">local_florist</span>
                    <span className="font-panchang text-[10px] font-bold">Olfactory Psychophysics (UPSIT)</span>
                  </div>
                  <span className="font-panchang text-[9px] text-on-surface-variant">Cutoff: ≥32 pts</span>
                </div>
                <div className="grid grid-cols-2 gap-3 text-xs bg-surface-container-lowest p-2 rounded-lg border border-surface-container-high/30">
                  <div className="flex flex-col">
                    <span className="font-panchang text-[11px] font-bold text-on-surface">
                      {participantA.assessmentData.olfactoryScore} / 40 items
                    </span>
                    <span className="font-panchang text-[9px] font-semibold text-primary">
                      SHAP: +{fusionA.olfactoryShift.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className="font-panchang text-[11px] font-bold text-on-surface">
                      {participantB.assessmentData.olfactoryScore} / 40 items
                    </span>
                    <span className="font-panchang text-[9px] font-semibold text-secondary">
                      SHAP: +{fusionB.olfactoryShift.toFixed(2)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Row 2: REM Sleep */}
              <div className="bg-surface-container-low p-space-sm rounded-xl border border-surface-container-high/60 flex flex-col gap-1.5">
                <div className="flex items-center justify-between text-on-surface">
                  <div className="flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[16px] text-primary">bedtime</span>
                    <span className="font-panchang text-[10px] font-bold">REM Sleep Behavior (RBDSQ)</span>
                  </div>
                  <span className="font-panchang text-[9px] text-on-surface-variant">Cutoff: ≥5 pts</span>
                </div>
                <div className="grid grid-cols-2 gap-3 text-xs bg-surface-container-lowest p-2 rounded-lg border border-surface-container-high/30">
                  <div className="flex flex-col">
                    <span className="font-panchang text-[11px] font-bold text-on-surface">
                      {participantA.assessmentData.rbdsqScore} / 13 pts
                    </span>
                    <span className="font-panchang text-[9px] font-semibold text-primary">
                      SHAP: +{fusionA.rbdShift.toFixed(2)}
                    </span>
                    <span className="font-panchang text-[8.5px] text-on-surface-variant truncate">
                      {participantA.assessmentData.dreamEnactmentBehavior}
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className="font-panchang text-[11px] font-bold text-on-surface">
                      {participantB.assessmentData.rbdsqScore} / 13 pts
                    </span>
                    <span className="font-panchang text-[9px] font-semibold text-secondary">
                      SHAP: +{fusionB.rbdShift.toFixed(2)}
                    </span>
                    <span className="font-panchang text-[8.5px] text-on-surface-variant truncate">
                      {participantB.assessmentData.dreamEnactmentBehavior}
                    </span>
                  </div>
                </div>
              </div>

              {/* Row 3: Acoustic Voice */}
              <div className="bg-surface-container-low p-space-sm rounded-xl border border-surface-container-high/60 flex flex-col gap-1.5">
                <div className="flex items-center justify-between text-on-surface">
                  <div className="flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[16px] text-primary">mic</span>
                    <span className="font-panchang text-[10px] font-bold">Acoustic Phonation (Voice Jitter)</span>
                  </div>
                  <span className="font-panchang text-[9px] text-on-surface-variant">Baseline: &lt;1.04%</span>
                </div>
                <div className="grid grid-cols-2 gap-3 text-xs bg-surface-container-lowest p-2 rounded-lg border border-surface-container-high/30">
                  <div className="flex flex-col">
                    <span className="font-panchang text-[11px] font-bold text-on-surface">
                      {participantA.assessmentData.voiceJitter}% Jitter
                    </span>
                    <span className="font-panchang text-[9px] font-semibold text-primary">
                      SHAP: +{fusionA.voiceShift.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className="font-panchang text-[11px] font-bold text-on-surface">
                      {participantB.assessmentData.voiceJitter}% Jitter
                    </span>
                    <span className="font-panchang text-[9px] font-semibold text-secondary">
                      SHAP: +{fusionB.voiceShift.toFixed(2)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Row 4: Motor Kinematics */}
              <div className="bg-surface-container-low p-space-sm rounded-xl border border-surface-container-high/60 flex flex-col gap-1.5">
                <div className="flex items-center justify-between text-on-surface">
                  <div className="flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[16px] text-primary">touch_app</span>
                    <span className="font-panchang text-[10px] font-bold">Motor Kinematics (Finger Tapping)</span>
                  </div>
                  <span className="font-panchang text-[9px] text-on-surface-variant">Preserved: &gt;4.5 taps/s</span>
                </div>
                <div className="grid grid-cols-2 gap-3 text-xs bg-surface-container-lowest p-2 rounded-lg border border-surface-container-high/30">
                  <div className="flex flex-col">
                    <span className="font-panchang text-[11px] font-bold text-on-surface">
                      {participantA.assessmentData.tappingFrequency} taps/s
                    </span>
                    <span className={`font-panchang text-[9px] font-semibold ${fusionA.motorShift < 0 ? 'text-emerald-700' : 'text-primary'}`}>
                      SHAP: {fusionA.motorShift > 0 ? `+${fusionA.motorShift.toFixed(2)}` : fusionA.motorShift.toFixed(2)} {fusionA.motorShift < 0 ? '(Protective)' : ''}
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className="font-panchang text-[11px] font-bold text-on-surface">
                      {participantB.assessmentData.tappingFrequency} taps/s
                    </span>
                    <span className={`font-panchang text-[9px] font-semibold ${fusionB.motorShift < 0 ? 'text-emerald-700' : 'text-secondary'}`}>
                      SHAP: {fusionB.motorShift > 0 ? `+${fusionB.motorShift.toFixed(2)}` : fusionB.motorShift.toFixed(2)} {fusionB.motorShift < 0 ? '(Protective)' : ''}
                    </span>
                  </div>
                </div>
              </div>

              {/* Row 5: Retinal OCT */}
              <div className="bg-surface-container-low p-space-sm rounded-xl border border-surface-container-high/60 flex flex-col gap-1.5">
                <div className="flex items-center justify-between text-on-surface">
                  <div className="flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[16px] text-primary">visibility</span>
                    <span className="font-panchang text-[10px] font-bold">Retinal OCT Morphology</span>
                  </div>
                  <span className="font-panchang text-[9px] text-on-surface-variant">RNFL Thickness</span>
                </div>
                <div className="grid grid-cols-2 gap-3 text-xs bg-surface-container-lowest p-2 rounded-lg border border-surface-container-high/30">
                  <div className="flex flex-col">
                    <span className="font-panchang text-[11px] font-bold text-on-surface">
                      {participantA.assessmentData.retinalMissing ? 'Data Gap (Imputed)' : 'Layer Scan Validated'}
                    </span>
                    <span className="font-panchang text-[9px] font-semibold text-primary">
                      SHAP: {fusionA.retinalShift === 0 ? '0.00' : `+${fusionA.retinalShift.toFixed(2)}`}
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className="font-panchang text-[11px] font-bold text-on-surface">
                      {participantB.assessmentData.retinalMissing ? 'Data Gap (Imputed)' : 'Layer Scan Validated'}
                    </span>
                    <span className="font-panchang text-[9px] font-semibold text-secondary">
                      SHAP: {fusionB.retinalShift === 0 ? '0.00' : `+${fusionB.retinalShift.toFixed(2)}`}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Clinical Phenotype Takeaway */}
          <div className="bg-surface-container-low p-3.5 rounded-xl border border-surface-container-high flex flex-col gap-1 text-on-surface-variant">
            <span className="font-panchang text-[10px] font-bold text-on-surface flex items-center gap-1">
              <span className="material-symbols-outlined text-[15px] text-primary">insights</span>
              Comparative Clinical Takeaway
            </span>
            <p className="font-panchang text-[10px] leading-relaxed">
              {absDelta > 0.3 ? (
                <>
                  <span className="font-bold text-on-surface">{participantA.id}</span> and <span className="font-bold text-on-surface">{participantB.id}</span> exhibit a substantial risk index divergence of <span className="font-bold text-primary">{absDelta.toFixed(2)}</span>. This separation is primarily governed by discordant olfactory and sleep impairment channels, where non-motor prodromal markers show high discriminatory power.
                </>
              ) : (
                <>
                  <span className="font-bold text-on-surface">{participantA.id}</span> and <span className="font-bold text-on-surface">{participantB.id}</span> share closely aligned risk strata (delta {absDelta.toFixed(2)}). Cross-modal attribution shifts reflect similar kinematic compensation and biomarker stability profiles.
                </>
              )}
            </p>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-3.5 sm:p-4 border-t border-surface-container-high bg-surface-container-low flex items-center justify-between gap-2 shrink-0">
          <span className="font-panchang text-[10px] text-on-surface-variant hidden sm:inline">
            Comparative analysis based on MPF-PD v2.4 XGBoost SHAP vectors
          </span>
          <div className="flex items-center gap-2 ml-auto">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-surface-container hover:bg-surface-container-high text-on-surface font-panchang text-[11px] font-bold transition-colors cursor-pointer"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
