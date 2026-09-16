import React, { useState, useMemo, useEffect, useCallback } from 'react';
import { ScreenId, AssessmentData, CohortParticipant, FusionResult } from './types';
import { initialAssessmentData } from './data/mockCohort';
import { calculateMultimodalRisk } from './utils/riskModel';
import { checkApiHealth, runClinicalFusion } from './lib/api';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { BottomNav } from './components/BottomNav';
import { OverviewScreen } from './screens/OverviewScreen';
import { AssessmentScreen } from './screens/AssessmentScreen';
import { ResultsScreen } from './screens/ResultsScreen';
import { ExplainabilityScreen } from './screens/ExplainabilityScreen';

export const App: React.FC = () => {
  const [currentScreen, setCurrentScreen] = useState<ScreenId>('overview');
  const [assessmentData, setAssessmentData] = useState<AssessmentData>(initialAssessmentData);
  const [backendStatus, setBackendStatus] = useState<'online' | 'simulation' | 'checking'>('checking');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Sidebar state with localStorage persistence
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(() => {
    if (typeof window === 'undefined') return true;
    try {
      const saved = localStorage.getItem('sidebar_state');
      if (saved !== null) {
        return saved === 'open';
      }
    } catch {
      // Fallback
    }
    // On mobile (< 768px), default to false; on desktop (>= 768px), default to true
    return window.innerWidth >= 768;
  });

  // Persist sidebar state changes on desktop
  useEffect(() => {
    try {
      if (typeof window !== 'undefined' && window.innerWidth >= 768) {
        localStorage.setItem('sidebar_state', isSidebarOpen ? 'open' : 'closed');
      }
    } catch (e) {
      console.error('Error saving sidebar state to localStorage:', e);
    }
  }, [isSidebarOpen]);

  const toggleSidebar = useCallback(() => {
    setIsSidebarOpen((prev) => {
      const next = !prev;
      if (typeof window !== 'undefined' && window.innerWidth >= 768) {
        try {
          localStorage.setItem('sidebar_state', next ? 'open' : 'closed');
        } catch (e) {
          console.error(e);
        }
      }
      return next;
    });
  }, []);

  const closeMobileDrawer = useCallback(() => {
    setIsSidebarOpen(false);
  }, []);

  const handleNavigate = useCallback((screen: ScreenId) => {
    setCurrentScreen(screen);
    // Automatically close drawer on mobile after navigation
    if (typeof window !== 'undefined' && window.innerWidth < 768) {
      setIsSidebarOpen(false);
    }
  }, []);

  // Initial fusion result based on initial state
  const [fusionResult, setFusionResult] = useState<FusionResult>(() => {
    return calculateMultimodalRisk(initialAssessmentData);
  });

  // Check FastAPI backend health on mount and periodically
  const verifyBackend = useCallback(async () => {
    try {
      await checkApiHealth();
      setBackendStatus('online');
    } catch {
      setBackendStatus('simulation');
    }
  }, []);

  useEffect(() => {
    verifyBackend();
    const interval = setInterval(verifyBackend, 25000);
    return () => clearInterval(interval);
  }, [verifyBackend]);

  // Scroll to top upon navigating to a new screen
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' });
  }, [currentScreen]);

  const handleSelectCohortParticipant = (participant: CohortParticipant) => {
    setAssessmentData(participant.assessmentData);
    const result = calculateMultimodalRisk(participant.assessmentData);
    setFusionResult(result);
    handleNavigate('results-dashboard');
  };

  const handleRunFusion = async () => {
    setIsAnalyzing(true);
    setErrorMessage(null);
    try {
      const result = await runClinicalFusion(assessmentData);
      setFusionResult(result);
      if (result.isBackendLive) {
        setBackendStatus('online');
      }
      handleNavigate('results-dashboard');
    } catch (err: any) {
      console.error('Fusion analysis encountered an unexpected error:', err);
      // Clean fallback so UI never breaks
      const fallback = calculateMultimodalRisk(assessmentData);
      setFusionResult(fallback);
      handleNavigate('results-dashboard');
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="bg-surface font-body-md text-on-surface flex min-h-screen w-full overflow-x-hidden">
      {/* Left Collapsible Navigation Sidebar (Push-flex on desktop, drawer on mobile) */}
      <Sidebar
        currentScreen={currentScreen}
        onNavigate={handleNavigate}
        isOpen={isSidebarOpen}
        onToggle={toggleSidebar}
        onClose={closeMobileDrawer}
      />

      {/* Main Content Column (flex: 1 pushes and resizes automatically) */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen transition-all duration-300 ease-in-out relative">
        {/* Floating toggle button on left edge when collapsed */}
        {!isSidebarOpen && (
          <button
            type="button"
            onClick={toggleSidebar}
            data-testid="sidebar-collapsed-toggle-btn"
            aria-label="Expand sidebar"
            title="Expand sidebar"
            className="fixed left-0 top-24 z-30 flex items-center justify-center gap-1 pl-2 pr-2.5 py-2 rounded-r-xl bg-surface-container-lowest/95 hover:bg-surface-container text-on-surface border border-l-0 border-surface-container-high shadow-lg transition-all duration-300 hover:translate-x-0.5 active:scale-95 cursor-pointer backdrop-blur-xs group"
          >
            <span
              data-testid="sidebar-collapsed-chevron-icon"
              className="material-symbols-outlined text-[18px] transition-transform duration-300 group-hover:scale-110 rotate-180 inline-block"
            >
              chevron_right
            </span>
            <span className="material-symbols-outlined text-[16px] text-on-surface-variant group-hover:text-primary">
              menu
            </span>
          </button>
        )}

        {/* Fixed/Sticky Top Protocol Header with live backend badge & toggle */}
        <Header
          currentScreen={currentScreen}
          onNavigate={handleNavigate}
          backendStatus={backendStatus}
          onToggleSidebar={toggleSidebar}
          isSidebarOpen={isSidebarOpen}
        />

        {/* Main Content Area: Responsive desktop layout with fluid flex: 1 width */}
        <main className="flex-1 flex flex-col relative w-full py-6 pb-28 sm:pb-16 px-space-md sm:px-6 lg:px-8 xl:px-12 2xl:px-16 bg-surface">
          <div className="w-full max-w-[1800px] 2xl:max-w-[1960px] mx-auto">
            {errorMessage && (
              <div className="mb-4 p-4 rounded-xl bg-error-container text-on-error-container flex items-center justify-between">
                <span>{errorMessage}</span>
                <button onClick={() => setErrorMessage(null)} className="font-bold underline text-sm">Dismiss</button>
              </div>
            )}

            {currentScreen === 'overview' && (
              <OverviewScreen
                onNavigate={handleNavigate}
                onSelectCohortParticipant={handleSelectCohortParticipant}
              />
            )}

            {currentScreen === 'new-assessment' && (
              <AssessmentScreen
                assessmentData={assessmentData}
                onUpdateAssessmentData={setAssessmentData}
                onRunFusion={handleRunFusion}
                onNavigate={handleNavigate}
              />
            )}

            {currentScreen === 'results-dashboard' && (
              <ResultsScreen
                fusionResult={fusionResult}
                assessmentData={assessmentData}
                onNavigate={handleNavigate}
              />
            )}

            {currentScreen === 'explainability-shap' && (
              <ExplainabilityScreen
                fusionResult={fusionResult}
                assessmentData={assessmentData}
                onNavigate={handleNavigate}
              />
            )}
          </div>
        </main>
      </div>

      {/* Fixed Bottom Multi-Screen Navigation Bar (Mobile only, hidden on lg:) */}
      <BottomNav
        currentScreen={currentScreen}
        onNavigate={handleNavigate}
      />
    </div>
  );
};

export default App;
