import React, { useState } from 'react';
import { ScreenId } from '../types';

interface HeaderProps {
  currentScreen: ScreenId;
  onNavigate: (screen: ScreenId) => void;
  backendStatus?: 'online' | 'simulation' | 'checking';
  onToggleSidebar?: () => void;
  isSidebarOpen?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  currentScreen,
  onNavigate,
  backendStatus = 'checking',
  onToggleSidebar,
  isSidebarOpen,
}) => {
  const [showProfile, setShowProfile] = useState(false);

  const getScreenSubtitle = (screen: ScreenId) => {
    switch (screen) {
      case 'overview':
        return 'Overview';
      case 'new-assessment':
        return 'New Assessment';
      case 'results-dashboard':
        return 'Results Dashboard';
      case 'explainability-shap':
        return 'Explainability Shap';
      default:
        return 'Clinical Intelligence';
    }
  };

  return (
    <>
      <header className="sticky top-0 w-full z-30 pt-safe bg-surface/90 backdrop-blur-xl shadow-[0_1px_8px_rgba(0,0,0,0.03)] border-b border-surface-container-high/40">
        <div className="h-20 px-space-md sm:px-6 lg:px-8 xl:px-12 w-full max-w-[1800px] 2xl:max-w-[1920px] mx-auto flex flex-col justify-center gap-space-xs">
          <div className="flex items-center justify-between gap-space-sm">
            <div className="flex items-center gap-2 min-w-0">
              {onToggleSidebar && (
                <button
                  type="button"
                  onClick={onToggleSidebar}
                  data-testid="header-sidebar-toggle"
                  aria-label={isSidebarOpen ? 'Collapse sidebar' : 'Open sidebar'}
                  title={isSidebarOpen ? 'Collapse sidebar' : 'Open sidebar'}
                  className="w-9 h-9 rounded-xl flex items-center justify-center text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors cursor-pointer shrink-0"
                >
                  <span className="material-symbols-outlined text-[22px]">menu</span>
                </button>
              )}
              <div 
                className="flex items-center gap-space-sm min-w-0 cursor-pointer select-none"
                onClick={() => onNavigate('overview')}
                title="Return to Home Overview"
              >
                {/* Logo icon - visible on mobile, subtle on desktop */}
                <img
                  alt="MPF-PD Multimodal Fusion Emblem"
                  className="h-8 w-auto object-contain shrink-0 lg:hidden"
                  src="https://lh3.googleusercontent.com/aida/AEtjO1VTCTk6dwTtL7MSvNBsD3F31nd21T-yhwzMlp1n50ei159X7W__eBS1VboTHeE3wSfBqHRhv1v8ffPRVsGSOkzgwJN9q70cd46BqmCffVAWrzVqa-HJa6Baj4ZJiHGKANoGmhAVTf5Ev1fMQzaahmAhp34ACrONbNKzmhwOC34Fwely50kAiMheBlVNIAqBp_YMaGaxHEMi82sx39uc1s9t9d_mjTBGfJywy2clLuKJA4-olcEnfryncfs"
                />
              <div className="flex flex-col min-w-0">
                <div className="flex items-center gap-space-xs">
                  <span className="font-headline-sm text-headline-sm text-on-surface tracking-tight truncate">
                    MPF-PD
                  </span>
                  <span className="px-1.5 py-0.5 rounded-full bg-secondary-container text-on-secondary-container font-label-sm text-[10px] tracking-wide whitespace-nowrap">
                    Protocol v2.4
                  </span>
                  <span className="hidden md:inline-flex px-2 py-0.5 rounded-full bg-surface-container text-on-surface-variant font-label-sm text-[10px]">
                    Site 04 Academic Core
                  </span>
                </div>
                <div className="flex items-center gap-1.5 font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider truncate">
                  <span className="text-primary font-bold">{getScreenSubtitle(currentScreen)}</span>
                  <span className="hidden sm:inline text-outline-variant">•</span>
                  <span className="hidden sm:inline font-normal normal-case">Cross-Institutional Cohort Validation</span>
                </div>
              </div>
            </div>
            </div>

            <div className="flex items-center gap-space-sm shrink-0">
              {backendStatus === 'online' ? (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-300 text-[11px] font-medium shadow-xs">
                  <span className="w-2 h-2 rounded-full bg-emerald-600 animate-pulse"></span>
                  <span className="hidden sm:inline">FastAPI ML</span>
                  <span>Active</span>
                </div>
              ) : backendStatus === 'checking' ? (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-container-high text-on-surface-variant text-[11px] font-medium">
                  <span className="w-2 h-2 rounded-full bg-slate-400 animate-spin"></span>
                  <span>Checking API</span>
                </div>
              ) : (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-50 text-amber-800 border border-amber-300 text-[11px] font-medium">
                  <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                  <span className="hidden sm:inline">Local Model</span>
                  <span>Simulation</span>
                </div>
              )}

              <button
                type="button"
                onClick={() => setShowProfile(!showProfile)}
                aria-label="Investigator Profile"
                className="w-8 h-8 rounded-full bg-primary flex items-center justify-center hover:opacity-90 active:scale-95 transition-all shadow-xs"
              >
                <span className="material-symbols-outlined text-on-primary text-[18px]">person</span>
              </button>
            </div>
          </div>

          <div className="flex items-center justify-between gap-space-xs bg-surface-container px-space-sm py-0.5 rounded-lg text-on-surface-variant overflow-hidden">
            <div className="flex items-center gap-1.5 min-w-0">
              <span className="material-symbols-outlined text-[13px] text-tertiary shrink-0">shield</span>
              <p className="font-disclaimer-text text-disclaimer-text truncate text-on-surface-variant">
                Research prototype only. Not a diagnostic tool. Language uses Risk Pattern only.
              </p>
            </div>
            <span className="hidden md:inline-block font-disclaimer-text text-[10px] text-on-surface-variant whitespace-nowrap shrink-0">
              IRB Protocol #2024-NEURO-09
            </span>
          </div>
        </div>
      </header>

      {/* Investigator Profile Popover Dialog */}
      {showProfile && (
        <div 
          className="fixed inset-0 z-50 flex items-start justify-end p-4 pt-24 bg-black/20 backdrop-blur-xs"
          onClick={() => setShowProfile(false)}
        >
          <div 
            className="bg-surface-container-lowest rounded-2xl p-space-md shadow-2xl border border-surface-container-high w-80 flex flex-col gap-3"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-2 border-b border-surface-container-high">
              <div className="flex items-center gap-2">
                <div className="w-9 h-9 rounded-full bg-primary-fixed text-primary flex items-center justify-center font-bold font-panchang text-xs">
                  EM
                </div>
                <div className="flex flex-col">
                  <span className="font-panchang text-xs font-bold text-on-surface">Dr. Elena Martinez</span>
                  <span className="font-label-sm text-[10px] text-on-surface-variant">Lead Neuro-Phenotype PI</span>
                </div>
              </div>
              <button 
                onClick={() => setShowProfile(false)}
                className="text-on-surface-variant hover:text-on-surface p-1 rounded-lg"
              >
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            </div>

            <div className="flex flex-col gap-1.5 text-xs text-on-surface-variant">
              <div className="flex justify-between py-1 bg-surface-container-low px-2 rounded-lg">
                <span>Site Node:</span>
                <span className="font-semibold text-on-surface">Site 04 (Academic Core)</span>
              </div>
              <div className="flex justify-between py-1 bg-surface-container-low px-2 rounded-lg">
                <span>IRB Protocol:</span>
                <span className="font-semibold text-on-surface">#2024-NEURO-09</span>
              </div>
              <div className="flex justify-between py-1 bg-surface-container-low px-2 rounded-lg">
                <span>Cert Status:</span>
                <span className="font-semibold text-tertiary">HIPAA / GDPR Validated</span>
              </div>
            </div>

            <button
              type="button"
              onClick={() => {
                setShowProfile(false);
                onNavigate('overview');
              }}
              className="mt-1 w-full py-2 rounded-lg bg-surface-container text-on-surface font-panchang text-[11px] font-semibold hover:bg-surface-container-high transition-colors"
            >
              Session Overview
            </button>
          </div>
        </div>
      )}
    </>
  );
};
