import React from 'react';
import { DisclaimerBanner } from './components/layout/DisclaimerBanner';
import { Header } from './components/layout/Header';
import { Footer } from './components/layout/Footer';
import { ParticipantForm } from './components/forms/ParticipantForm';
import { ModalityInputs } from './components/forms/ModalityInputs';
import { AnalysisButton } from './components/forms/AnalysisButton';
import { ResultsDashboard } from './components/results/ResultsDashboard';
import { usePipelineStore } from './store/usePipelineStore';

export const App: React.FC = () => {
  const { result } = usePipelineStore();

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      {/* Persistent Disclaimer Banner */}
      <DisclaimerBanner />

      {/* Main Header */}
      <Header />

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Intro description */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <h2 className="text-xl font-bold tracking-tight text-slate-900">
              Multimodal Prodromal Risk Screening Prototype
            </h2>
            <p className="text-xs sm:text-sm text-slate-600 max-w-2xl">
              Research prototype evaluating cross-modality sensory, motor, and neurodegenerative biomarkers for early Parkinson's risk pattern detection. Integrates 5 modalities with dynamic neural gating attention.
            </p>
          </div>
          <div className="px-3 py-1.5 bg-teal-50 border border-teal-200 rounded-xl text-teal-800 text-xs font-semibold shrink-0">
            Phase 8 Full-Stack Build
          </div>
        </div>

        {/* Step 1: Participant Information */}
        <ParticipantForm />

        {/* Step 2: Modality Inputs & Missingness Toggles */}
        <ModalityInputs />

        {/* Step 3: Trigger Analysis */}
        <AnalysisButton />

        {/* Step 4-7: Results Dashboard */}
        {result && <ResultsDashboard result={result} />}
      </main>

      {/* Footer */}
      <Footer />
    </div>
  );
};

export default App;
