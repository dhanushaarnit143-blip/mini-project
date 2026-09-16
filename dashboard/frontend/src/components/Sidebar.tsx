import React, { useState } from 'react';
import { ScreenId } from '../types';
import { activeCohortList } from '../data/mockCohort';

interface SidebarProps {
  currentScreen: ScreenId;
  onNavigate: (screen: ScreenId) => void;
  isOpen?: boolean;
  onToggle?: () => void;
  onClose?: () => void;
}

interface NavItem {
  id: ScreenId;
  label: string;
  sublabel: string;
  icon: string;
  badge?: string;
  badgeType?: 'primary' | 'secondary' | 'neutral';
}

const NAV_ITEMS: NavItem[] = [
  {
    id: 'overview',
    label: 'Cohort Overview',
    sublabel: 'Longitudinal Telemetry',
    icon: 'analytics',
    badge: `${activeCohortList.length}`,
    badgeType: 'neutral',
  },
  {
    id: 'new-assessment',
    label: 'New Assessment',
    sublabel: 'Multimodal Ingestion',
    icon: 'assignment_add',
    badge: 'Step 2/5',
    badgeType: 'primary',
  },
  {
    id: 'results-dashboard',
    label: 'Results & Inference',
    sublabel: 'Prodromal Risk Index',
    icon: 'monitoring',
  },
  {
    id: 'explainability-shap',
    label: 'Explainability XAI',
    sublabel: 'TreeSHAP Attribution',
    icon: 'psychology',
    badge: 'TreeSHAP',
    badgeType: 'secondary',
  },
];

export const Sidebar: React.FC<SidebarProps> = ({
  currentScreen,
  onNavigate,
  isOpen = true,
  onToggle,
  onClose,
}) => {
  const [showProfile, setShowProfile] = useState(false);

  const handleNavClick = (screenId: ScreenId, isMobile: boolean) => {
    onNavigate(screenId);
    if (isMobile && onClose) {
      onClose();
    }
  };

  const renderSidebarContent = (isMobile: boolean) => (
    <div className="w-[280px] h-full flex flex-col shrink-0 select-none">
      {/* Brand Header */}
      <div className="p-4 sm:p-5 border-b border-surface-container-high/50 flex flex-col gap-3">
        <div className="flex items-center justify-between gap-2">
          <div
            className="flex items-center gap-3 cursor-pointer group flex-1 min-w-0"
            onClick={() => handleNavClick('overview', isMobile)}
            title="Go to Cohort Overview"
          >
            <div className="w-10 h-10 rounded-xl bg-surface-container flex items-center justify-center p-1 border border-surface-container-high shrink-0 group-hover:border-primary/40 transition-colors">
              <img
                alt="MPF-PD Logo"
                className="w-full h-full object-contain"
                src="https://lh3.googleusercontent.com/aida/AEtjO1VTCTk6dwTtL7MSvNBsD3F31nd21T-yhwzMlp1n50ei159X7W__eBS1VboTHeE3wSfBqHRhv1v8ffPRVsGSOkzgwJN9q70cd46BqmCffVAWrzVqa-HJa6Baj4ZJiHGKANoGmhAVTf5Ev1fMQzaahmAhp34ACrONbNKzmhwOC34Fwely50kAiMheBlVNIAqBp_YMaGaxHEMi82sx39uc1s9t9d_mjTBGfJywy2clLuKJA4-olcEnfryncfs"
              />
            </div>
            <div className="flex flex-col min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="font-panchang text-sm font-bold text-on-surface tracking-tight truncate">
                  MPF-PD
                </span>
                <span className="px-1.5 py-0.2 rounded bg-secondary-container text-on-secondary-container font-panchang text-[9px] font-bold">
                  v2.4
                </span>
              </div>
              <span className="font-panchang text-[10px] text-on-surface-variant truncate">
                Clinical Intelligence
              </span>
            </div>
          </div>

          {/* Toggle / Close Button */}
          <button
            type="button"
            onClick={isMobile ? onClose : onToggle}
            data-testid={isMobile ? 'mobile-sidebar-close-btn' : 'sidebar-toggle-btn'}
            aria-label={isOpen ? 'Collapse sidebar' : 'Expand sidebar'}
            title={isOpen ? 'Collapse sidebar' : 'Expand sidebar'}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors cursor-pointer shrink-0"
          >
            {isMobile ? (
              <span className="material-symbols-outlined text-[20px]">close</span>
            ) : (
              <span
                data-testid="sidebar-chevron-icon"
                className={`material-symbols-outlined text-[20px] inline-block transition-transform duration-300 ease-in-out ${
                  isOpen ? 'rotate-0' : 'rotate-180'
                }`}
              >
                chevron_right
              </span>
            )}
          </button>
        </div>

        {/* Research Protocol Badge */}
        <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-surface-container-low border border-surface-container-high/40 text-on-surface-variant">
          <span className="material-symbols-outlined text-[15px] text-tertiary shrink-0">shield</span>
          <div className="flex flex-col min-w-0">
            <span className="font-panchang text-[9px] font-bold text-on-surface uppercase tracking-wider truncate">
              IRB #2024-NEURO-09
            </span>
            <span className="font-panchang text-[8.5px] text-on-surface-variant truncate">
              Non-diagnostic Research Prototype
            </span>
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <div className="flex-1 py-4 px-3 flex flex-col gap-1 overflow-y-auto">
        <span className="px-3 pb-1 font-panchang text-[9px] font-bold text-on-surface-variant uppercase tracking-wider">
          Navigation Modules
        </span>

        {NAV_ITEMS.map((item) => {
          const isActive = currentScreen === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => handleNavClick(item.id, isMobile)}
              className={`w-full flex items-center justify-between p-2.5 rounded-xl transition-all text-left cursor-pointer group ${
                isActive
                  ? 'bg-primary text-on-primary shadow-xs font-semibold'
                  : 'text-on-surface hover:bg-surface-container-low'
              }`}
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <div
                  className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-colors ${
                    isActive
                      ? 'bg-on-primary/15 text-on-primary'
                      : 'bg-surface-container text-on-surface-variant group-hover:text-primary group-hover:bg-primary-fixed/40'
                  }`}
                >
                  <span className="material-symbols-outlined text-[19px]">{item.icon}</span>
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="font-panchang text-xs font-bold truncate leading-tight">
                    {item.label}
                  </span>
                  <span
                    className={`font-panchang text-[9px] truncate ${
                      isActive ? 'text-on-primary/80' : 'text-on-surface-variant'
                    }`}
                  >
                    {item.sublabel}
                  </span>
                </div>
              </div>

              {item.badge && (
                <span
                  className={`px-1.5 py-0.5 rounded-full font-panchang text-[9px] font-bold shrink-0 ml-1 ${
                    isActive
                      ? 'bg-on-primary text-primary'
                      : item.badgeType === 'primary'
                      ? 'bg-primary-fixed text-primary'
                      : item.badgeType === 'secondary'
                      ? 'bg-secondary-container text-on-secondary-container'
                      : 'bg-surface-container text-on-surface-variant'
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}

        {/* Quick CTA in Sidebar */}
        <div className="mt-4 pt-4 border-t border-surface-container-high/40 px-1 flex flex-col gap-2">
          <span className="font-panchang text-[9px] font-bold text-on-surface-variant uppercase tracking-wider px-2">
            Quick Protocol Actions
          </span>
          <button
            type="button"
            onClick={() => handleNavClick('new-assessment', isMobile)}
            className="w-full py-2.5 px-3 rounded-xl bg-primary-fixed hover:bg-primary-fixed-dim text-primary font-panchang text-xs font-bold flex items-center justify-center gap-1.5 transition-colors cursor-pointer shadow-2xs"
          >
            <span className="material-symbols-outlined text-[17px]">add_circle</span>
            <span>New Patient Ingestion</span>
          </button>
          <button
            type="button"
            onClick={() => handleNavClick('results-dashboard', isMobile)}
            className="w-full py-2 px-3 rounded-xl bg-surface-container hover:bg-surface-container-high text-on-surface font-panchang text-[11px] font-medium flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
          >
            <span className="material-symbols-outlined text-[16px]">speed</span>
            <span>Active Inference Telemetry</span>
          </button>
        </div>

        {/* Model Health Status Micro-card */}
        <div className="mt-auto pt-4 px-1">
          <div className="bg-surface-container-low p-2.5 rounded-xl border border-surface-container-high/40 flex flex-col gap-1.5 text-[10px] font-panchang">
            <div className="flex items-center justify-between">
              <span className="font-bold text-on-surface flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                Model Engine
              </span>
              <span className="text-[9px] text-emerald-700 font-bold bg-emerald-100 px-1.5 py-0.2 rounded-full">
                CALIBRATED
              </span>
            </div>
            <div className="flex justify-between text-on-surface-variant text-[9px]">
              <span>Pipeline Latency:</span>
              <span className="font-bold text-on-surface">&lt;420ms</span>
            </div>
            <div className="flex justify-between text-on-surface-variant text-[9px]">
              <span>Validation AUC:</span>
              <span className="font-bold text-primary">94.2%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Investigator Profile */}
      <div className="p-3 border-t border-surface-container-high/50 bg-surface-container-low/60">
        <div
          onClick={() => setShowProfile(true)}
          className="flex items-center justify-between p-2 rounded-xl hover:bg-surface-container transition-colors cursor-pointer"
        >
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-full bg-primary text-on-primary flex items-center justify-center font-bold font-panchang text-xs shrink-0 shadow-xs">
              EM
            </div>
            <div className="flex flex-col min-w-0">
              <span className="font-panchang text-xs font-bold text-on-surface truncate">
                Dr. Elena Martinez
              </span>
              <span className="font-panchang text-[9px] text-on-surface-variant truncate">
                Lead Neuro PI • Site 04
              </span>
            </div>
          </div>
          <span className="material-symbols-outlined text-[16px] text-on-surface-variant">
            more_vert
          </span>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile Drawer Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 backdrop-blur-xs md:hidden transition-opacity duration-300 animate-in fade-in"
          onClick={onClose}
          data-testid="mobile-drawer-backdrop"
          aria-hidden="true"
        />
      )}

      {/* Mobile Drawer */}
      <aside
        data-testid="mobile-sidebar-drawer"
        className={`fixed inset-y-0 left-0 z-50 w-[280px] bg-surface-container-lowest border-r border-surface-container-high/60 shadow-2xl md:hidden transform transition-transform duration-300 ease-in-out select-none flex flex-col ${
          isOpen ? 'translate-x-0' : '-translate-x-full pointer-events-none'
        }`}
      >
        {renderSidebarContent(true)}
      </aside>

      {/* Desktop Collapsible Flex Sidebar */}
      <aside
        data-testid="desktop-sidebar"
        className={`hidden md:flex flex-col shrink-0 h-screen sticky top-0 z-20 bg-surface-container-lowest border-r border-surface-container-high/60 shadow-[1px_0_12px_rgba(0,0,0,0.02)] select-none transition-all duration-300 ease-in-out overflow-hidden ${
          isOpen
            ? 'w-[280px] min-w-[280px] max-w-[280px] opacity-100'
            : 'w-0 min-w-0 max-w-0 opacity-0 border-r-0 pointer-events-none'
        }`}
        style={{
          transition: 'width 0.3s ease, min-width 0.3s ease, max-width 0.3s ease, opacity 0.3s ease, border-color 0.3s ease',
        }}
      >
        {renderSidebarContent(false)}
      </aside>

      {/* Investigator Profile Dialog */}
      {showProfile && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30 backdrop-blur-xs animate-in fade-in"
          onClick={() => setShowProfile(false)}
        >
          <div
            className="bg-surface-container-lowest rounded-2xl p-space-md shadow-2xl border border-surface-container-high w-80 flex flex-col gap-3 animate-in zoom-in-95"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-2 border-b border-surface-container-high">
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 rounded-full bg-primary-fixed text-primary flex items-center justify-center font-bold font-panchang text-xs">
                  EM
                </div>
                <div className="flex flex-col">
                  <span className="font-panchang text-xs font-bold text-on-surface">
                    Dr. Elena Martinez
                  </span>
                  <span className="font-panchang text-[10px] text-on-surface-variant">
                    Lead Neuro-Phenotype PI
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowProfile(false)}
                className="text-on-surface-variant hover:text-on-surface p-1 rounded-lg hover:bg-surface-container"
              >
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            </div>

            <div className="flex flex-col gap-1.5 text-xs text-on-surface-variant">
              <div className="flex justify-between py-1 bg-surface-container-low px-2.5 rounded-lg">
                <span className="font-panchang text-[10px]">Site Node:</span>
                <span className="font-panchang text-[10px] font-bold text-on-surface">Site 04 (Academic Core)</span>
              </div>
              <div className="flex justify-between py-1 bg-surface-container-low px-2.5 rounded-lg">
                <span className="font-panchang text-[10px]">IRB Protocol:</span>
                <span className="font-panchang text-[10px] font-bold text-on-surface">#2024-NEURO-09</span>
              </div>
              <div className="flex justify-between py-1 bg-surface-container-low px-2.5 rounded-lg">
                <span className="font-panchang text-[10px]">Cert Status:</span>
                <span className="font-panchang text-[10px] font-bold text-tertiary">HIPAA / GDPR Validated</span>
              </div>
            </div>

            <button
              type="button"
              onClick={() => {
                setShowProfile(false);
                onNavigate('overview');
              }}
              className="mt-1 w-full py-2 rounded-xl bg-surface-container text-on-surface font-panchang text-[11px] font-bold hover:bg-surface-container-high transition-colors cursor-pointer"
            >
              Return to Cohort Overview
            </button>
          </div>
        </div>
      )}
    </>
  );
};
