import React, { useState } from 'react';
import { 
  Keyboard, 
  Mic, 
  Activity, 
  Eye, 
  Moon, 
  ShieldX, 
  ShieldCheck, 
  CheckSquare, 
  Square, 
  ArrowRight, 
  ArrowLeft,
  FileText,
  AlertTriangle 
} from 'lucide-react';

const CURRENT_CONSENT_VERSION = '1.0.0';

/**
 * Screen 2 & 4: What We Collect & Research Informed Consent
 * Section A: Data categories with plain-language rationale & what is NOT collected.
 * Section B: Formal informed consent agreement, versioning, required & optional checkboxes.
 */
export function ConsentScreen({ onNext, onBack, consentState, onUpdateConsent }) {
  // Step sub-tab: 'collect_scope' -> 'consent_form'
  const [subStep, setSubStep] = useState('collect_scope');

  const [hasReadUnderstand, setHasReadUnderstand] = useState(consentState?.hasReadUnderstand || false);
  const [consentCollection, setConsentCollection] = useState(consentState?.data_collection || false);
  const [consentAudio, setConsentAudio] = useState(consentState?.audio_storage || false);
  const [consentExport, setConsentExport] = useState(consentState?.research_export || false);

  const collectedItems = [
    {
      icon: Keyboard,
      title: 'Typing Dynamics',
      color: 'text-sky-400 bg-sky-500/10 border-sky-500/20',
      reason: 'Measures key-press hold times and flight time intervals. Captures fine motor coordination variations without reading typed characters.'
    },
    {
      icon: Mic,
      title: 'Acoustic Voice Tasks',
      color: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
      reason: 'Extracts pitch variability, jitter, and shimmer during brief sustained phonation tasks (/a/ vowel). Raw audio is analyzed on-device.'
    },
    {
      icon: Activity,
      title: 'Motor & Tremor Micro-Tasks',
      color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
      reason: 'Records tap timing alternating between two targets and resting hand tremor via accelerometer and gyroscope.'
    },
    {
      icon: Eye,
      title: 'Ocular / Visual Behavior',
      color: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
      reason: 'Tracks fixational gaze stability and saccade latency during visual prompts. (Not retinal fundus/OCT imaging).'
    },
    {
      icon: Moon,
      title: 'Sleep & Daily Survey',
      color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20',
      reason: 'Logs subjective sleep regularity, dream-enactment indicators (RBD screening), and self-reported physical state.'
    }
  ];

  const notCollectedItems = [
    'Passwords, PINs, or authentication tokens',
    'Message contents, emails, or typed private text',
    'Financial, banking, or credit card details',
    'Background audio or passive room listening',
    'Uncontrolled background camera surveillance'
  ];

  const handleUnderstandScope = () => {
    setSubStep('consent_form');
  };

  const handleConsentSubmit = () => {
    onUpdateConsent({
      hasReadUnderstand,
      data_collection: consentCollection,
      audio_storage: consentAudio,
      research_export: consentExport,
      consent_version: CURRENT_CONSENT_VERSION
    });
    onNext();
  };

  const canSubmit = hasReadUnderstand && consentCollection;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between p-6 max-w-md mx-auto font-sans">
      {/* Top Header */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={() => {
              if (subStep === 'consent_form') setSubStep('collect_scope');
              else onBack();
            }}
            className="p-2 -ml-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-900 transition"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            {subStep === 'collect_scope' ? 'Step 2: What We Collect' : 'Step 4: Informed Consent'}
          </div>
          <div className="w-5" />
        </div>

        {subStep === 'collect_scope' ? (
          <>
            <h2 className="text-2xl font-bold tracking-tight text-white">
              Data Collection Transparency
            </h2>
            <p className="mt-2 text-xs text-slate-400 leading-relaxed">
              We practice strict data minimization. Every recorded metric serves a specific scientific purpose to model your personal baseline.
            </p>

            {/* Collected Categories */}
            <div className="mt-4 space-y-2.5 max-h-[46vh] overflow-y-auto pr-1">
              {collectedItems.map((item, idx) => {
                const Icon = item.icon;
                return (
                  <div key={idx} className="p-3 rounded-xl bg-slate-900/70 border border-slate-800 text-xs">
                    <div className="flex items-center gap-2.5 mb-1.5">
                      <div className={`p-1.5 rounded-lg border ${item.color}`}>
                        <Icon className="w-4 h-4" />
                      </div>
                      <span className="font-semibold text-slate-200">{item.title}</span>
                    </div>
                    <p className="text-slate-400 pl-8 leading-relaxed text-[11px]">
                      {item.reason}
                    </p>
                  </div>
                );
              })}
            </div>

            {/* What is NOT collected */}
            <div className="mt-4 p-3.5 rounded-xl bg-rose-950/20 border border-rose-800/40 text-xs">
              <div className="flex items-center gap-2 text-rose-300 font-bold mb-2">
                <ShieldX className="w-4 h-4 text-rose-400 shrink-0" />
                <span>What We NEVER Collect:</span>
              </div>
              <ul className="space-y-1 text-rose-200/80 text-[11px] list-disc list-inside">
                {notCollectedItems.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>
          </>
        ) : (
          <>
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold tracking-tight text-white">
                Research Informed Consent
              </h2>
              <span className="px-2.5 py-1 rounded-full bg-slate-800 border border-slate-700 text-slate-300 text-[10px] font-mono">
                v{CURRENT_CONSENT_VERSION}
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-400">
              Please review your participation rights and grant explicit research permissions.
            </p>

            {/* Consent Text Agreement */}
            <div className="mt-3 p-3.5 rounded-xl bg-slate-900 border border-slate-800 text-[11px] text-slate-300 space-y-2 max-h-[36vh] overflow-y-auto leading-relaxed">
              <div className="flex items-center gap-2 text-amber-300 font-semibold text-xs">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>Non-Diagnostic Research Agreement</span>
              </div>
              <p>
                1. <strong>Voluntary Participation:</strong> I understand that participation is completely voluntary. I may revoke my consent or stop participating at any time without penalty.
              </p>
              <p>
                2. <strong>Personal Baseline Calibration:</strong> I understand that during the initial 14-day calibration period, measurements establish my individual baseline, and no risk scores are generated.
              </p>
              <p>
                3. <strong>Data Security & Rights:</strong> My records are pseudonymized with an irreversible UUID and encrypted in transit and at rest in Supabase. I retain full rights to export all my recorded data or request complete, irreversible data deletion at any time.
              </p>
              <p>
                4. <strong>Not a Medical Diagnosis:</strong> I explicitly acknowledge that this app is a research prototype, not a medical device, and does not diagnose Parkinson's disease.
              </p>
            </div>

            {/* Checkboxes */}
            <div className="mt-4 space-y-2.5">
              {/* Mandatory: Read & Understand */}
              <label className="flex items-start gap-3 p-2.5 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 cursor-pointer transition text-xs">
                <input
                  type="checkbox"
                  checked={hasReadUnderstand}
                  onChange={(e) => setHasReadUnderstand(e.target.checked)}
                  className="mt-0.5 rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 h-4 w-4 shrink-0 bg-slate-800"
                />
                <span className="text-slate-200 font-medium text-[11px]">
                  I have read, understood, and accept the research scope and voluntary conditions. <strong className="text-amber-400">(Required)</strong>
                </span>
              </label>

              {/* Mandatory: Data Collection */}
              <label className="flex items-start gap-3 p-2.5 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 cursor-pointer transition text-xs">
                <input
                  type="checkbox"
                  checked={consentCollection}
                  onChange={(e) => setConsentCollection(e.target.checked)}
                  className="mt-0.5 rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 h-4 w-4 shrink-0 bg-slate-800"
                />
                <span className="text-slate-200 font-medium text-[11px]">
                  I consent to the collection of anonymized digital biomarker features for MPF baseline research. <strong className="text-amber-400">(Required)</strong>
                </span>
              </label>

              {/* Optional: Audio Storage */}
              <label className="flex items-start gap-3 p-2.5 rounded-xl bg-slate-900/40 border border-slate-800/60 hover:border-slate-700 cursor-pointer transition text-xs">
                <input
                  type="checkbox"
                  checked={consentAudio}
                  onChange={(e) => setConsentAudio(e.target.checked)}
                  className="mt-0.5 rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 h-4 w-4 shrink-0 bg-slate-800"
                />
                <span className="text-slate-300 text-[11px]">
                  (Optional) I consent to secure encrypted research audio snippet storage for acoustic model validation.
                </span>
              </label>

              {/* Optional: Research Dataset Export */}
              <label className="flex items-start gap-3 p-2.5 rounded-xl bg-slate-900/40 border border-slate-800/60 hover:border-slate-700 cursor-pointer transition text-xs">
                <input
                  type="checkbox"
                  checked={consentExport}
                  onChange={(e) => setConsentExport(e.target.checked)}
                  className="mt-0.5 rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 h-4 w-4 shrink-0 bg-slate-800"
                />
                <span className="text-slate-300 text-[11px]">
                  (Optional) I consent to inclusion of my de-identified feature vectors in open research benchmarking datasets.
                </span>
              </label>
            </div>
          </>
        )}
      </div>

      {/* Bottom Action Button */}
      <div className="pt-4 pb-2">
        {subStep === 'collect_scope' ? (
          <button
            onClick={handleUnderstandScope}
            className="w-full py-3.5 px-5 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:scale-[0.99] text-white font-semibold text-sm shadow-lg shadow-indigo-600/25 flex items-center justify-center gap-2 transition cursor-pointer"
          >
            <span>I Understand</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        ) : (
          <button
            onClick={handleConsentSubmit}
            disabled={!canSubmit}
            className={`w-full py-3.5 px-5 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 transition cursor-pointer ${
              canSubmit
                ? 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-lg shadow-emerald-600/25'
                : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700/50'
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            <span>I Consent</span>
          </button>
        )}
      </div>
    </div>
  );
}

export default ConsentScreen;
