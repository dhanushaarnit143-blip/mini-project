import React from 'react';
import { FusionCard } from './FusionCard';
import { MissingModalityCallout } from './MissingModalityCallout';
import { ModalityCards } from './ModalityCards';
import { ExplainabilityPanel } from './ExplainabilityPanel';
import { ReportExport } from './ReportExport';
import { AnalysisResponse } from '../../types/pipeline';

interface ResultsDashboardProps {
  result: AnalysisResponse;
}

export const ResultsDashboard: React.FC<ResultsDashboardProps> = ({ result }) => {
  return (
    <section data-testid="results-dashboard" className="space-y-6 pt-4 animate-in fade-in duration-500">
      <div className="border-b border-slate-200 pb-3 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-slate-900 tracking-tight">
            Step 4: Multimodal Screening Analysis Results
          </h2>
          <p className="text-xs text-slate-500">
            Fused prodromal risk score, feature attributions, and dynamic gating breakdown.
          </p>
        </div>
      </div>

      {/* Primary Fusion Card */}
      <FusionCard fusion={result.fusion} participantId={result.participant_id} />

      {/* Missing Modality Callout */}
      <MissingModalityCallout missingModalities={result.missing_modalities} />

      {/* Individual Modality Cards */}
      <ModalityCards modalities={result.individual_modalities} />

      {/* Explainability & SHAP Attribution Panel */}
      <ExplainabilityPanel explainability={result.explainability} />

      {/* Report & Artifact Export */}
      <ReportExport result={result} />
    </section>
  );
};
