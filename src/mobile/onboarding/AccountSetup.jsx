import React, { useState, useEffect } from 'react';
import { Mail, Lock, KeyRound, ShieldCheck, ArrowRight, ArrowLeft, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { ConsentService } from '../services/consentService.js';

/**
 * Screen 6: Account Setup
 * Secure email registration, strong password creation, pseudonymous ID generation,
 * and atomic commitment of participant and consent records.
 */
export function AccountSetup({ onComplete, onBack, consentData, permissionsData, supabaseClient }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [pseudonymousId, setPseudonymousId] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    // Generate pseudonymous identifier on mount
    const generatedId = ConsentService.generatePseudonymousId();
    setPseudonymousId(generatedId);
  }, []);

  const isPasswordValid = password.length >= 8;
  const isMatch = password === confirmPassword && password.length > 0;
  const isEmailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());

  const canSubmit = isEmailValid && isPasswordValid && isMatch && !isSubmitting;

  const handleCreateAccount = async (e) => {
    e.preventDefault();
    if (!canSubmit) return;

    setIsSubmitting(true);
    setErrorMsg('');

    try {
      const consentService = new ConsentService(supabaseClient);

      // In client mode or with Supabase
      let participantId = null;

      if (supabaseClient) {
        // 1. Sign up user via Supabase Auth
        const { data: authData, error: authErr } = await supabaseClient.auth.signUp({
          email: email.trim().toLowerCase(),
          password: password,
          options: {
            data: {
              pseudonymous_id: pseudonymousId,
              consent_version: consentData?.consent_version || '1.0.0'
            }
          }
        });

        if (authErr) {
          throw new Error(authErr.message);
        }

        participantId = authData?.user?.id;

        // If user is already created or authenticated, insert/upsert into participants table
        if (participantId) {
          const { error: partErr } = await supabaseClient
            .from('participants')
            .upsert({
              id: participantId,
              pseudonymous_id: pseudonymousId,
              consent_version: consentData?.consent_version || '1.0.0',
              consent_timestamp: new Date().toISOString(),
              app_version: '1.0.0',
              model_version: '1.0.0',
              baseline_status: 'collecting'
            });

          if (partErr) {
            throw new Error(`Failed to initialize participant record: ${partErr.message}`);
          }
        }
      }

      // If offline/mock test, generate synthetic UUID
      if (!participantId) {
        participantId = typeof crypto !== 'undefined' && crypto.randomUUID 
          ? crypto.randomUUID() 
          : '00000000-0000-4000-a000-000000000001';
      }

      // 2. Commit informed consent records
      await consentService.recordConsent({
        participantId,
        consentVersion: consentData?.consent_version || '1.0.0',
        consents: {
          data_collection: consentData?.data_collection ?? true,
          audio_storage: consentData?.audio_storage ?? false,
          research_export: consentData?.research_export ?? false,
          camera_access: permissionsData?.camera ?? false,
          microphone_access: permissionsData?.microphone ?? true,
          motion_access: permissionsData?.motion ?? true,
          keyboard_access: permissionsData?.keyboard ?? true,
        }
      });

      // Complete flow
      onComplete({
        participantId,
        pseudonymousId,
        email: email.trim().toLowerCase(),
        consentVersion: consentData?.consent_version || '1.0.0'
      });
    } catch (err) {
      setErrorMsg(err.message || 'Failed to complete registration.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between p-6 max-w-md mx-auto font-sans">
      <div>
        {/* Navigation Bar */}
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={onBack}
            className="p-2 -ml-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-900 transition cursor-pointer"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Step 6: Account Setup
          </div>
          <div className="w-5" />
        </div>

        <h2 className="text-2xl font-bold tracking-tight text-white">
          Secure Account Registration
        </h2>
        <p className="mt-2 text-xs text-slate-400 leading-relaxed">
          Your credentials authenticate securely with Supabase. All research biomarker vectors are tied exclusively to your pseudonymous ID.
        </p>

        {/* Pseudonymous Identifier Display */}
        <div className="mt-4 p-3.5 rounded-xl bg-slate-900/90 border border-indigo-500/30">
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-slate-400 font-medium">Assigned Research Pseudonym:</span>
            <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-mono">
              Zero PII
            </span>
          </div>
          <div className="font-mono text-sm font-bold text-indigo-400 tracking-wider">
            {pseudonymousId || 'Generating pseudonym...'}
          </div>
          <p className="text-[10px] text-slate-500 mt-1">
            Derived cryptographically. Your email is never attached to sensor observation tables.
          </p>
        </div>

        {errorMsg && (
          <div className="mt-3 p-3 rounded-xl bg-rose-950/40 border border-rose-600/40 text-rose-300 text-xs flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Registration Form */}
        <form onSubmit={handleCreateAccount} className="mt-4 space-y-3.5">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Email Address
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                <Mail className="w-4 h-4" />
              </div>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="participant@research.org"
                className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-200 placeholder-slate-600 text-xs focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Password (min. 8 characters)
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                <Lock className="w-4 h-4" />
              </div>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-200 placeholder-slate-600 text-xs focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Confirm Password
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                <KeyRound className="w-4 h-4" />
              </div>
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-200 placeholder-slate-600 text-xs focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
            </div>
          </div>

          {/* Strength & Match indicators */}
          <div className="flex items-center gap-4 text-[11px] text-slate-400 pt-1">
            <span className={isPasswordValid ? 'text-emerald-400 flex items-center gap-1' : 'text-slate-500'}>
              {isPasswordValid && <CheckCircle2 className="w-3 h-3" />} 8+ chars
            </span>
            <span className={isMatch ? 'text-emerald-400 flex items-center gap-1' : 'text-slate-500'}>
              {isMatch && <CheckCircle2 className="w-3 h-3" />} Passwords match
            </span>
          </div>
        </form>
      </div>

      {/* Submit Action */}
      <div className="pt-4 pb-2">
        <button
          onClick={handleCreateAccount}
          disabled={!canSubmit}
          className={`w-full py-3.5 px-5 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 transition cursor-pointer ${
            canSubmit
              ? 'bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 text-white shadow-lg shadow-emerald-500/25 active:scale-[0.99]'
              : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700/50'
          }`}
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Registering Participant...</span>
            </>
          ) : (
            <>
              <ShieldCheck className="w-4 h-4" />
              <span>Create Account</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}

export default AccountSetup;
