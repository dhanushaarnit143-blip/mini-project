import React, { useState } from 'react';
import WelcomeScreen from './WelcomeScreen.jsx';
import ConsentScreen from './ConsentScreen.jsx';
import PermissionsScreen from './PermissionsScreen.jsx';
import BaselineExplanation from './BaselineExplanation.jsx';
import AccountSetup from './AccountSetup.jsx';
import { ShieldCheck, CheckCircle2, Calendar, Lock, ArrowRight } from 'lucide-react';

/**
 * Onboarding Flow Coordinator
 * Manages step-by-step navigation across all 6 onboarding screens:
 * 1. Welcome
 * 2. What We Collect / Consent
 * 3. Permissions
 * 4. Research Consent Agreement
 * 5. Baseline Explanation
 * 6. Account Setup
 */
export function OnboardingFlow({ onOnboardingComplete, supabaseClient }) {
  const [currentStep, setCurrentStep] = useState(1);

  const [consentData, setConsentData] = useState({
    hasReadUnderstand: false,
    data_collection: false,
    audio_storage: false,
    research_export: false,
    consent_version: '1.0.0'
  });

  const [permissionsData, setPermissionsData] = useState({
    microphone: true,
    motion: true,
    keyboard: true,
    camera: false
  });

  const [completedParticipant, setCompletedParticipant] = useState(null);

  const handleNext = () => {
    setCurrentStep(prev => prev + 1);
  };

  const handleBack = () => {
    setCurrentStep(prev => Math.max(1, prev - 1));
  };

  const handleComplete = (participantInfo) => {
    setCompletedParticipant(participantInfo);
    if (onOnboardingComplete) {
      onOnboardingComplete(participantInfo);
    }
  };

  // Completion confirmation view
  if (completedParticipant) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between p-6 max-w-md mx-auto font-sans">
        <div className="pt-10 text-center space-y-4">
          <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center justify-center mx-auto shadow-lg shadow-emerald-500/20">
            <CheckCircle2 className="w-8 h-8" />
          </div>

          <h2 className="text-2xl font-bold text-white tracking-tight">
            Onboarding Complete!
          </h2>
          <p className="text-xs text-slate-400 max-w-xs mx-auto leading-relaxed">
            Your consent records and 14-day baseline calibration have been successfully registered.
          </p>

          <div className="mt-6 p-4 rounded-2xl bg-slate-900 border border-slate-800 text-left space-y-2 text-xs">
            <div className="flex justify-between items-center text-slate-400">
              <span>Research Pseudonym:</span>
              <span className="font-mono text-indigo-400 font-bold">{completedParticipant.pseudonymousId}</span>
            </div>
            <div className="flex justify-between items-center text-slate-400">
              <span>Consent Version:</span>
              <span className="font-mono text-slate-300">v{completedParticipant.consentVersion}</span>
            </div>
            <div className="flex justify-between items-center text-slate-400">
              <span>Baseline Status:</span>
              <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-semibold text-[10px]">
                Collecting (Day 1 of 14)
              </span>
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-amber-950/30 border border-amber-600/30 text-amber-200 text-left text-[11px] leading-relaxed">
            <strong>Remember:</strong> MPF is a research prototype. Zero risk scores will be generated during the initial 14-day calibration.
          </div>
        </div>

        <div className="pt-6 pb-2">
          <button
            onClick={() => {
              if (typeof window !== 'undefined') {
                window.location.href = '/';
              }
            }}
            className="w-full py-3.5 px-5 rounded-xl bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white font-semibold text-sm shadow-lg shadow-indigo-500/25 flex items-center justify-center gap-2 transition cursor-pointer"
          >
            <span>Enter Daily Assessment Hub</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    );
  }

  // Render Step
  return (
    <div className="relative">
      {/* Step Progress Dots */}
      <div className="max-w-md mx-auto px-6 pt-4 pb-1 bg-slate-950 flex items-center justify-between">
        {[1, 2, 3, 4, 5].map((step) => (
          <div
            key={step}
            className={`h-1.5 flex-1 rounded-full mx-0.5 transition-all ${
              step === currentStep
                ? 'bg-indigo-500'
                : step < currentStep
                ? 'bg-indigo-900/60'
                : 'bg-slate-800'
            }`}
          />
        ))}
      </div>

      {currentStep === 1 && (
        <WelcomeScreen onNext={handleNext} />
      )}

      {currentStep === 2 && (
        <ConsentScreen
          onNext={handleNext}
          onBack={handleBack}
          consentState={consentData}
          onUpdateConsent={(data) => setConsentData(prev => ({ ...prev, ...data }))}
        />
      )}

      {currentStep === 3 && (
        <PermissionsScreen
          onNext={handleNext}
          onBack={handleBack}
          permissionsState={permissionsData}
          onUpdatePermissions={(perms) => setPermissionsData(perms)}
        />
      )}

      {currentStep === 4 && (
        <BaselineExplanation
          onNext={handleNext}
          onBack={handleBack}
        />
      )}

      {currentStep === 5 && (
        <AccountSetup
          onComplete={handleComplete}
          onBack={handleBack}
          consentData={consentData}
          permissionsData={permissionsData}
          supabaseClient={supabaseClient}
        />
      )}
    </div>
  );
}

export default OnboardingFlow;
