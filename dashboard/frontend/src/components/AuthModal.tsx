import React, { useState } from 'react';
import { supabase } from '../lib/supabase';
import { X, Lock, Mail, User, CheckCircle2, AlertCircle } from 'lucide-react';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentUser: any;
  onAuthChange: () => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  currentUser,
  onAuthChange,
}) => {
  const [mode, setMode] = useState<'signin' | 'signup' | 'reset'>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);

    try {
      if (mode === 'signup') {
        const { error } = await supabase.auth.signUp({
          email: email.trim(),
          password,
          options: {
            data: {
              full_name: fullName.trim(),
            },
          },
        });
        if (error) throw error;
        setMessage({
          text: 'Account created successfully! Check your email or sign in.',
          type: 'success',
        });
        onAuthChange();
      } else if (mode === 'signin') {
        const { error } = await supabase.auth.signInWithPassword({
          email: email.trim(),
          password,
        });
        if (error) throw error;
        setMessage({ text: 'Signed in successfully!', type: 'success' });
        onAuthChange();
        setTimeout(onClose, 800);
      } else if (mode === 'reset') {
        const { error } = await supabase.auth.resetPasswordForEmail(email.trim());
        if (error) throw error;
        setMessage({
          text: 'Password reset link sent to your email address.',
          type: 'success',
        });
      }
    } catch (err: any) {
      setMessage({
        text: err.message || 'Authentication failed. Please verify credentials.',
        type: 'error',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSignOut = async () => {
    setLoading(true);
    await supabase.auth.signOut();
    setLoading(false);
    onAuthChange();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="relative w-full max-w-md p-6 bg-surface-container-lowest border border-surface-container-high/60 rounded-2xl shadow-xl">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-on-surface-variant hover:bg-surface-container transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {currentUser ? (
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-12 h-12 rounded-full bg-primary-container text-on-primary-container font-semibold text-lg">
                {currentUser.email?.charAt(0).toUpperCase()}
              </div>
              <div>
                <h3 className="font-semibold text-on-surface text-base">
                  {currentUser.user_metadata?.full_name || 'Clinical Researcher'}
                </h3>
                <p className="text-xs text-on-surface-variant">{currentUser.email}</p>
              </div>
            </div>

            <div className="p-3 text-xs rounded-xl bg-surface-container-low text-on-surface-variant border border-surface-container">
              Connected to <strong>mini project</strong> (Supabase). Row-Level Security is active.
            </div>

            <button
              onClick={handleSignOut}
              disabled={loading}
              className="w-full py-2.5 mt-2 rounded-xl bg-error text-on-error font-medium text-sm hover:opacity-90 transition-opacity"
            >
              Sign Out
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <h2 className="text-lg font-bold text-on-surface">
                {mode === 'signin' && 'Researcher Sign In'}
                {mode === 'signup' && 'Create Researcher Account'}
                {mode === 'reset' && 'Reset Password'}
              </h2>
              <p className="text-xs text-on-surface-variant mt-0.5">
                {mode === 'signin' && 'Sign in to access cohort records and persist assessments.'}
                {mode === 'signup' && 'Register to manage participants with Row-Level Security.'}
                {mode === 'reset' && 'Enter your email to receive a recovery link.'}
              </p>
            </div>

            {message && (
              <div
                className={`flex items-start gap-2 p-3 text-xs rounded-xl border ${
                  message.type === 'success'
                    ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                    : 'bg-rose-50 text-rose-800 border-rose-200'
                }`}
              >
                {message.type === 'success' ? (
                  <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600 mt-0.5" />
                ) : (
                  <AlertCircle className="w-4 h-4 shrink-0 text-rose-600 mt-0.5" />
                )}
                <span>{message.text}</span>
              </div>
            )}

            {mode === 'signup' && (
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-on-surface-variant">Full Name</label>
                <div className="relative flex items-center">
                  <User className="absolute left-3 w-4 h-4 text-on-surface-variant" />
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Dr. Jane Doe"
                    className="w-full pl-9 pr-3 py-2 text-sm bg-surface-container-low border border-surface-container rounded-xl focus:outline-hidden focus:ring-2 focus:ring-primary/20 text-on-surface"
                  />
                </div>
              </div>
            )}

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-on-surface-variant">Email</label>
              <div className="relative flex items-center">
                <Mail className="absolute left-3 w-4 h-4 text-on-surface-variant" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="researcher@hospital.org"
                  className="w-full pl-9 pr-3 py-2 text-sm bg-surface-container-low border border-surface-container rounded-xl focus:outline-hidden focus:ring-2 focus:ring-primary/20 text-on-surface"
                />
              </div>
            </div>

            {mode !== 'reset' && (
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-on-surface-variant">Password</label>
                <div className="relative flex items-center">
                  <Lock className="absolute left-3 w-4 h-4 text-on-surface-variant" />
                  <input
                    type="password"
                    required
                    minLength={6}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-9 pr-3 py-2 text-sm bg-surface-container-low border border-surface-container rounded-xl focus:outline-hidden focus:ring-2 focus:ring-primary/20 text-on-surface"
                  />
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 rounded-xl bg-primary text-on-primary font-semibold text-sm hover:opacity-90 transition-opacity mt-1 disabled:opacity-50"
            >
              {loading ? 'Processing...' : mode === 'signin' ? 'Sign In' : mode === 'signup' ? 'Create Account' : 'Send Reset Email'}
            </button>

            <div className="flex items-center justify-between text-xs text-on-surface-variant mt-2 pt-2 border-t border-surface-container">
              {mode === 'signin' ? (
                <>
                  <button
                    type="button"
                    onClick={() => {
                      setMode('signup');
                      setMessage(null);
                    }}
                    className="hover:underline text-primary"
                  >
                    Need an account? Sign up
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setMode('reset');
                      setMessage(null);
                    }}
                    className="hover:underline"
                  >
                    Forgot password?
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  onClick={() => {
                    setMode('signin');
                    setMessage(null);
                  }}
                  className="hover:underline text-primary mx-auto"
                >
                  Already have an account? Sign in
                </button>
              )}
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
