import React, { useState, useMemo } from 'react';
import { ScreenId, CohortParticipant } from '../types';
import { activeCohortList } from '../data/mockCohort';
import { ParticipantComparisonModal } from '../components/ParticipantComparisonModal';

interface OverviewScreenProps {
  onNavigate: (screen: ScreenId) => void;
  onSelectCohortParticipant: (participant: CohortParticipant) => void;
}

export const OverviewScreen: React.FC<OverviewScreenProps> = ({
  onNavigate,
  onSelectCohortParticipant,
}) => {
  const [isProtocolOpen, setIsProtocolOpen] = useState(false);
  const [expandedModality, setExpandedModality] = useState<string | null>(null);

  // Search and Filter State
  const [searchQuery, setSearchQuery] = useState('');
  const [riskFilter, setRiskFilter] = useState<'all' | 'Elevated Pattern' | 'Intermediate' | 'Low Risk Pattern'>('all');
  const [familyHistoryOnly, setFamilyHistoryOnly] = useState(false);
  const [sortBy, setSortBy] = useState<'risk-desc' | 'risk-asc' | 'id-asc'>('risk-desc');

  // Side-by-Side Comparison State (holds up to 2 participant IDs)
  const [selectedForCompare, setSelectedForCompare] = useState<string[]>([]);
  const [isComparisonModalOpen, setIsComparisonModalOpen] = useState(false);

  const participantA = useMemo(
    () => activeCohortList.find((p) => p.id === selectedForCompare[0]),
    [selectedForCompare]
  );
  const participantB = useMemo(
    () => activeCohortList.find((p) => p.id === selectedForCompare[1]),
    [selectedForCompare]
  );

  const toggleCompareParticipant = (id: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setSelectedForCompare((prev) => {
      if (prev.includes(id)) {
        return prev.filter((p) => p !== id);
      }
      if (prev.length >= 2) {
        return [prev[1], id];
      }
      return [...prev, id];
    });
  };

  const handleSwapCompare = () => {
    if (selectedForCompare.length === 2) {
      setSelectedForCompare([selectedForCompare[1], selectedForCompare[0]]);
    }
  };

  const handleQuickPresetCompare = (idA: string, idB: string) => {
    setSelectedForCompare([idA, idB]);
    setIsComparisonModalOpen(true);
  };

  const toggleModality = (id: string) => {
    setExpandedModality(expandedModality === id ? null : id);
  };

  // Pre-calculated filter counts
  const filterCounts = useMemo(() => {
    return {
      all: activeCohortList.length,
      elevated: activeCohortList.filter(p => p.riskClass === 'Elevated Pattern').length,
      intermediate: activeCohortList.filter(p => p.riskClass === 'Intermediate').length,
      low: activeCohortList.filter(p => p.riskClass === 'Low Risk Pattern').length,
      familyHistory: activeCohortList.filter(p => p.assessmentData.familyHistory).length,
    };
  }, []);

  // Filtered and sorted cohort list
  const filteredCohort = useMemo(() => {
    return activeCohortList
      .filter((participant) => {
        // Risk Pattern Filter
        if (riskFilter !== 'all' && participant.riskClass !== riskFilter) {
          return false;
        }

        // Family History Filter
        if (familyHistoryOnly && !participant.assessmentData.familyHistory) {
          return false;
        }

        // Text Search Filter (matches ID, cohort ID, clinical notes, visit, sex, age, risk class)
        if (searchQuery.trim()) {
          const query = searchQuery.toLowerCase().trim();
          const idMatch = participant.id.toLowerCase().includes(query) || participant.assessmentData.cohortId.toLowerCase().includes(query);
          const notesMatch = participant.notes.toLowerCase().includes(query);
          const visitMatch = participant.visit.toLowerCase().includes(query);
          const sexMatch = participant.assessmentData.biologicalSex.toLowerCase().includes(query);
          const ageMatch = `${participant.assessmentData.age}`.includes(query);
          const riskClassMatch = participant.riskClass.toLowerCase().includes(query);
          return idMatch || notesMatch || visitMatch || sexMatch || ageMatch || riskClassMatch;
        }

        return true;
      })
      .sort((a, b) => {
        if (sortBy === 'risk-desc') return b.riskIndex - a.riskIndex;
        if (sortBy === 'risk-asc') return a.riskIndex - b.riskIndex;
        if (sortBy === 'id-asc') return a.id.localeCompare(b.id);
        return 0;
      });
  }, [searchQuery, riskFilter, familyHistoryOnly, sortBy]);

  const hasActiveFilters = searchQuery.trim() !== '' || riskFilter !== 'all' || familyHistoryOnly;

  const resetFilters = () => {
    setSearchQuery('');
    setRiskFilter('all');
    setFamilyHistoryOnly(false);
    setSortBy('risk-desc');
  };

  return (
    <div className="flex flex-col w-full gap-space-lg pb-space-xl mx-auto animate-in fade-in duration-200">
      {/* Hero Section - Multi-column on Desktop */}
      <section className="bg-surface-container-lowest p-space-md sm:p-space-lg lg:p-8 rounded-3xl shadow-xs border border-surface-container-high/40 flex flex-col lg:flex-row lg:items-center justify-between gap-space-lg">
        <div className="flex flex-col gap-space-md max-w-2xl">
          {/* Super-Badge */}
          <div className="inline-flex items-center self-start gap-space-xs px-2.5 py-1 rounded-full bg-secondary-container text-on-secondary-container">
            <span className="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
            <span className="font-panchang text-[10px] tracking-wider uppercase font-semibold">
              MPF-PD • MULTIMODAL PRODROMAL FUSION
            </span>
          </div>

          {/* Main Headline & Description */}
          <div className="flex flex-col gap-space-xs">
            <h1 className="font-panchang text-headline-xl-mobile sm:text-2xl lg:text-3xl xl:text-4xl text-on-surface font-bold leading-tight tracking-tight">
              Early Parkinson’s Risk Pattern Estimation
            </h1>
            <p className="font-panchang text-body-sm sm:text-body-md text-on-surface-variant leading-relaxed">
              A clinical research prototype fusing olfactory psychophysics, REM sleep (RBD), acoustic vocal tremor, motor finger tapping kinematics, and retinal microvascular OCT into unified, explainable risk inference.
            </p>
          </div>

          {/* Primary & Secondary CTAs */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-space-sm pt-space-xs">
            <button
              type="button"
              onClick={() => onNavigate('new-assessment')}
              className="flex items-center justify-center gap-space-sm bg-primary hover:bg-primary-container text-on-primary py-3 px-space-lg rounded-xl shadow-[0_8px_20px_rgba(53,37,205,0.25)] transition-all active:scale-[0.98] cursor-pointer"
            >
              <span className="font-panchang text-label-md font-bold tracking-wide">
                Start New Assessment
              </span>
              <span className="material-symbols-outlined text-[20px]">arrow_forward</span>
            </button>

            <button
              type="button"
              onClick={() => setIsProtocolOpen(!isProtocolOpen)}
              className={`flex items-center justify-center gap-space-xs py-3 px-space-md rounded-xl transition-colors cursor-pointer ${
                isProtocolOpen
                  ? 'bg-surface-container-highest text-on-surface font-semibold'
                  : 'bg-surface-container hover:bg-surface-container-high text-on-surface'
              }`}
            >
              <span className="material-symbols-outlined text-[18px] text-secondary">tune</span>
              <span className="font-panchang text-label-md font-semibold">Explore Protocol Specs</span>
            </button>
          </div>
        </div>

        {/* Right Column on Desktop: Clinical Safety & Protocol Highlights */}
        <div className="flex flex-col gap-space-sm lg:w-80 xl:w-96 shrink-0">
          <div className="flex items-start gap-space-sm bg-surface-container-low p-space-md rounded-2xl shadow-xs border border-surface-container-high/40">
            <div className="w-9 h-9 rounded-xl bg-tertiary-fixed flex items-center justify-center shrink-0 mt-0.5">
              <span className="material-symbols-outlined text-[20px] text-tertiary">verified_user</span>
            </div>
            <div className="flex flex-col gap-0.5 min-w-0">
              <span className="font-panchang text-[11px] font-bold text-on-surface uppercase tracking-wide">
                Investigational Rigor
              </span>
              <p className="font-panchang text-[11px] text-on-surface-variant leading-normal">
                Identify elevated risk patterns earlier. Research prototype only. Never a diagnostic tool.
              </p>
            </div>
          </div>

          <div className="bg-surface-container-low p-space-md rounded-2xl border border-surface-container-high/40 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="font-panchang text-[10px] font-bold text-primary uppercase">
                Consensus Cohort v2.4
              </span>
              <span className="px-2 py-0.5 rounded-full bg-surface-container text-on-surface-variant font-panchang text-[9px] font-semibold">
                IRB Active
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-[10px] font-panchang text-on-surface-variant">
              <div className="bg-surface-container p-2 rounded-xl">
                <span className="block text-[8.5px] uppercase">Calibration</span>
                <span className="font-bold text-on-surface">Isotonic Tensor</span>
              </div>
              <div className="bg-surface-container p-2 rounded-xl">
                <span className="block text-[8.5px] uppercase">Latency</span>
                <span className="font-bold text-on-surface">&lt;420ms</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Expandable Protocol Sheet */}
      {isProtocolOpen && (
        <div className="flex flex-col gap-space-sm p-space-md sm:p-space-lg rounded-2xl bg-surface-container-lowest shadow-sm border border-surface-container-high/60 animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="flex items-center justify-between">
            <span className="font-panchang text-xs font-bold tracking-wide text-primary uppercase">
              Cohort Protocol v2.4 Spec Sheet
            </span>
            <span className="font-panchang text-[10px] text-on-surface-variant">IRB #2024-NEURO-09</span>
          </div>
          <p className="font-panchang text-xs text-on-surface-variant leading-relaxed">
            Cross-institutional consensus sampling protocol combining deep spectral entropy across 44.1kHz vocal recordings, 12-channel tri-axial accelerometer sampling (200Hz), and automated segmented ganglion cell complex (GCC) scans.
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-space-xs pt-1">
            <div className="bg-surface-container-low p-2.5 rounded-xl">
              <p className="font-panchang text-[9px] text-on-surface-variant uppercase">Calibration Model</p>
              <p className="font-panchang text-xs font-bold text-on-surface">Isotonic Recalibrated</p>
            </div>
            <div className="bg-surface-container-low p-2.5 rounded-xl">
              <p className="font-panchang text-[9px] text-on-surface-variant uppercase">Inference Latency</p>
              <p className="font-panchang text-xs font-bold text-on-surface">&lt; 420ms Latency</p>
            </div>
            <div className="bg-surface-container-low p-2.5 rounded-xl">
              <p className="font-panchang text-[9px] text-on-surface-variant uppercase">Validation Cohort</p>
              <p className="font-panchang text-xs font-bold text-on-surface">N=1,420 Subjects</p>
            </div>
            <div className="bg-surface-container-low p-2.5 rounded-xl">
              <p className="font-panchang text-[9px] text-on-surface-variant uppercase">Framework</p>
              <p className="font-panchang text-xs font-bold text-primary">TreeSHAP v1.8</p>
            </div>
          </div>
        </div>
      )}

      {/* Key System Metrics (2x2 Grid) */}
      <section className="flex flex-col gap-space-sm">
        <div className="flex items-center justify-between">
          <span className="font-panchang text-[11px] font-bold uppercase tracking-wider text-on-surface-variant">
            System Benchmarks
          </span>
          <span className="font-panchang text-[10px] text-tertiary font-semibold flex items-center gap-0.5">
            <span className="material-symbols-outlined text-[12px]">sync</span>
            N=1,420 Cohort
          </span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-space-sm">
          {/* Metric 1 */}
          <div className="bg-surface-container-lowest p-space-md rounded-2xl shadow-xs border border-surface-container-high/40 flex flex-col justify-between gap-space-sm">
            <div className="flex items-center justify-between">
              <span className="material-symbols-outlined text-primary text-[20px]">hub</span>
              <span className="px-1.5 py-0.5 rounded-full bg-secondary-container font-panchang text-[9px] text-on-secondary-container font-bold">
                FUSED
              </span>
            </div>
            <div>
              <div className="font-panchang text-headline-xl-mobile font-bold text-on-surface tracking-tight">5</div>
              <p className="font-panchang text-[11px] font-bold text-on-surface mt-0.5">Modalities</p>
              <p className="font-panchang text-[10px] text-on-surface-variant leading-tight">
                Olfactory, RBD, Voice, Motor, Retina
              </p>
            </div>
          </div>

          {/* Metric 2 */}
          <div className="bg-surface-container-lowest p-space-md rounded-2xl shadow-xs border border-surface-container-high/40 flex flex-col justify-between gap-space-sm">
            <div className="flex items-center justify-between">
              <span className="material-symbols-outlined text-tertiary text-[20px]">ssid_chart</span>
              <span className="px-1.5 py-0.5 rounded-full bg-tertiary-fixed font-panchang text-[9px] text-on-tertiary-fixed font-bold">
                VAL-SET
              </span>
            </div>
            <div>
              <div className="font-panchang text-headline-xl-mobile font-bold text-on-surface tracking-tight">94.2%</div>
              <p className="font-panchang text-[11px] font-bold text-on-surface mt-0.5">Mean AUC</p>
              <p className="font-panchang text-[10px] text-on-surface-variant leading-tight">
                Multi-center prodromal cohort
              </p>
            </div>
          </div>

          {/* Metric 3 */}
          <div className="bg-surface-container-lowest p-space-md rounded-2xl shadow-xs border border-surface-container-high/40 flex flex-col justify-between gap-space-sm">
            <div className="flex items-center justify-between">
              <span className="material-symbols-outlined text-secondary text-[20px]">linear_scale</span>
              <span className="px-1.5 py-0.5 rounded-full bg-surface-container font-panchang text-[9px] text-on-surface-variant font-bold">
                SCALE
              </span>
            </div>
            <div>
              <div className="font-panchang text-headline-xl-mobile font-bold text-on-surface tracking-tight">0.0–1.0</div>
              <p className="font-panchang text-[11px] font-bold text-on-surface mt-0.5">Risk Index</p>
              <p className="font-panchang text-[10px] text-on-surface-variant leading-tight">
                Continuous likelihood distribution
              </p>
            </div>
          </div>

          {/* Metric 4 */}
          <div className="bg-surface-container-lowest p-space-md rounded-2xl shadow-xs border border-surface-container-high/40 flex flex-col justify-between gap-space-sm">
            <div className="flex items-center justify-between">
              <span className="material-symbols-outlined text-primary text-[20px]">psychology</span>
              <span className="px-1.5 py-0.5 rounded-full bg-primary-fixed font-panchang text-[9px] text-on-primary-fixed font-bold">
                XAI
              </span>
            </div>
            <div>
              <div className="font-panchang text-headline-xl-mobile font-bold text-on-surface tracking-tight">100%</div>
              <p className="font-panchang text-[11px] font-bold text-on-surface mt-0.5">SHAP Fused</p>
              <p className="font-panchang text-[10px] text-on-surface-variant leading-tight">
                Explainable feature attribution
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Interactive Biomarker Modality Pipeline Showcase */}
      <section className="flex flex-col gap-space-sm">
        <div className="flex items-center justify-between">
          <span className="font-panchang text-[11px] font-bold uppercase tracking-wider text-on-surface-variant">
            5 Biomarker Modality Streams
          </span>
          <span className="font-panchang text-[10px] text-on-surface-variant font-medium">Tap to Inspect</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-5 gap-space-sm items-start">
          {/* Modality 1: Olfactory */}
          <div
            onClick={() => toggleModality('olfactory')}
            className="bg-surface-container-lowest rounded-2xl p-space-md shadow-xs border border-surface-container-high/40 transition-all cursor-pointer select-none hover:bg-surface-container-lowest/90"
          >
            <div className="flex items-center justify-between gap-space-sm">
              <div className="flex items-center gap-space-sm min-w-0">
                <div className="w-10 h-10 rounded-xl bg-tertiary-fixed flex items-center justify-center shrink-0">
                  <span className="material-symbols-outlined text-tertiary text-[20px]">air</span>
                </div>
                <div className="flex flex-col min-w-0">
                  <h2 className="font-panchang text-[13px] font-bold text-on-surface truncate">
                    Olfactory Psychophysics
                  </h2>
                  <span className="font-panchang text-[10px] text-on-surface-variant truncate">
                    UPSIT • 40-item Odor Identification
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-space-xs shrink-0">
                <span className="px-2 py-0.5 rounded-full bg-surface-container-high text-on-surface-variant font-panchang text-[9px] font-bold">
                  W=0.28
                </span>
                <span
                  className="material-symbols-outlined text-[18px] text-on-surface-variant transition-transform duration-200"
                  style={{ transform: expandedModality === 'olfactory' ? 'rotate(180deg)' : 'rotate(0deg)' }}
                >
                  expand_more
                </span>
              </div>
            </div>

            {expandedModality === 'olfactory' && (
              <div className="pt-space-md flex flex-col gap-space-xs animate-in fade-in duration-150">
                <div className="p-space-sm rounded-xl bg-surface-container-low flex flex-col gap-1">
                  <div className="flex justify-between items-center text-[10px] font-panchang text-on-surface-variant">
                    <span>Sensor Resolution</span>
                    <span className="font-bold text-on-surface">Sub-threshold Olfactometry</span>
                  </div>
                  <div className="flex justify-between items-center text-[10px] font-panchang text-on-surface-variant">
                    <span>Model Feature Weight</span>
                    <span className="font-bold text-primary">28.4% Attribution</span>
                  </div>
                  <p className="font-panchang text-[10px] text-on-surface-variant mt-1 leading-normal">
                    Detects anosmia and microsmia variations correlating with early Lewy-body pathology in olfactory bulb and anterior olfactory nucleus.
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Modality 2: REM Sleep */}
          <div
            onClick={() => toggleModality('sleep')}
            className="bg-surface-container-lowest rounded-2xl p-space-md shadow-xs border border-surface-container-high/40 transition-all cursor-pointer select-none hover:bg-surface-container-lowest/90"
          >
            <div className="flex items-center justify-between gap-space-sm">
              <div className="flex items-center gap-space-sm min-w-0">
                <div className="w-10 h-10 rounded-xl bg-secondary-container flex items-center justify-center shrink-0">
                  <span className="material-symbols-outlined text-on-secondary-container text-[20px]">bedtime</span>
                </div>
                <div className="flex flex-col min-w-0">
                  <h2 className="font-panchang text-[13px] font-bold text-on-surface truncate">
                    REM Sleep Degradation
                  </h2>
                  <span className="font-panchang text-[10px] text-on-surface-variant truncate">
                    RBDSQ Questionnaire &amp; Actigraphy
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-space-xs shrink-0">
                <span className="px-2 py-0.5 rounded-full bg-surface-container-high text-on-surface-variant font-panchang text-[9px] font-bold">
                  W=0.24
                </span>
                <span
                  className="material-symbols-outlined text-[18px] text-on-surface-variant transition-transform duration-200"
                  style={{ transform: expandedModality === 'sleep' ? 'rotate(180deg)' : 'rotate(0deg)' }}
                >
                  expand_more
                </span>
              </div>
            </div>

            {expandedModality === 'sleep' && (
              <div className="pt-space-md flex flex-col gap-space-xs animate-in fade-in duration-150">
                <div className="p-space-sm rounded-xl bg-surface-container-low flex flex-col gap-1">
                  <div className="flex justify-between items-center text-[10px] font-panchang text-on-surface-variant">
                    <span>Atonia Loss Index</span>
                    <span className="font-bold text-on-surface">Sub-mental EMG proxy</span>
                  </div>
                  <div className="flex justify-between items-center text-[10px] font-panchang text-on-surface-variant">
                    <span>Model Feature Weight</span>
                    <span className="font-bold text-primary">24.1% Attribution</span>
                  </div>
                  <p className="font-panchang text-[10px] text-on-surface-variant mt-1 leading-normal">
                    Evaluates dream-enacting motor behaviors and sub-clinical REM sleep without atonia (RSWA) as an early prodromal synucleinopathy hallmark.
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Modality 3: Acoustic Voice */}
          <div
            onClick={() => toggleModality('voice')}
            className="bg-surface-container-lowest rounded-2xl p-space-md shadow-xs border border-surface-container-high/40 transition-all cursor-pointer select-none hover:bg-surface-container-lowest/90"
          >
            <div className="flex items-center justify-between gap-space-sm">
              <div className="flex items-center gap-space-sm min-w-0">
                <div className="w-10 h-10 rounded-xl bg-primary-fixed flex items-center justify-center shrink-0">
                  <span className="material-symbols-outlined text-primary text-[20px]">graphic_eq</span>
                </div>
                <div className="flex flex-col min-w-0">
                  <h2 className="font-panchang text-[13px] font-bold text-on-surface truncate">
                    Acoustic Voice Tremor
                  </h2>
                  <span className="font-panchang text-[10px] text-on-surface-variant truncate">
                    Sustained /a/ • Jitter &amp; Shimmer
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-space-xs shrink-0">
                <span className="px-2 py-0.5 rounded-full bg-surface-container-high text-on-surface-variant font-panchang text-[9px] font-bold">
                  W=0.19
                </span>
                <span
                  className="material-symbols-outlined text-[18px] text-on-surface-variant transition-transform duration-200"
                  style={{ transform: expandedModality === 'voice' ? 'rotate(180deg)' : 'rotate(0deg)' }}
                >
                  expand_more
                </span>
              </div>
            </div>

            {expandedModality === 'voice' && (
              <div className="pt-space-md flex flex-col gap-space-xs animate-in fade-in duration-150">
                <div className="p-space-sm rounded-xl bg-surface-container-low flex flex-col gap-1">
                  <div className="flex justify-between items-center text-[10px] font-panchang text-on-surface-variant">
                    <span>Harmonic-to-Noise Ratio</span>
                    <span className="font-bold text-on-surface">Micro-dysphonia tracking</span>
                  </div>
                  <div className="flex justify-between items-center text-[10px] font-panchang text-on-surface-variant">
                    <span>Model Feature Weight</span>
                    <span className="font-bold text-primary">19.2% Attribution</span>
                  </div>
                  <p className="font-panchang text-[10px] text-on-surface-variant mt-1 leading-normal">
                    Measures sub-audible vocal fold hypokinesia, fundamental frequency perturbations, and subtle phonation instability.
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Modality 4: Motor Kinematics */}
          <div
            onClick={() => toggleModality('motor')}
            className="bg-surface-container-lowest rounded-2xl p-space-md shadow-xs border border-surface-container-high/40 transition-all cursor-pointer select-none hover:bg-surface-container-lowest/90"
          >
            <div className="flex items-center justify-between gap-space-sm">
              <div className="flex items-center gap-space-sm min-w-0">
                <div className="w-10 h-10 rounded-xl bg-surface-container-high flex items-center justify-center shrink-0">
                  <span className="material-symbols-outlined text-on-surface text-[20px]">touch_app</span>
                </div>
                <div className="flex flex-col min-w-0">
                  <h2 className="font-panchang text-[13px] font-bold text-on-surface truncate">
                    Finger Tapping Kinematics
                  </h2>
                  <span className="font-panchang text-[10px] text-on-surface-variant truncate">
                    Sub-clinical Bradykinesia &amp; Cadence
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-space-xs shrink-0">
                <span className="px-2 py-0.5 rounded-full bg-surface-container-high text-on-surface-variant font-panchang text-[9px] font-bold">
                  W=0.18
                </span>
                <span
                  className="material-symbols-outlined text-[18px] text-on-surface-variant transition-transform duration-200"
                  style={{ transform: expandedModality === 'motor' ? 'rotate(180deg)' : 'rotate(0deg)' }}
                >
                  expand_more
                </span>
              </div>
            </div>

            {expandedModality === 'motor' && (
              <div className="pt-space-md flex flex-col gap-space-xs animate-in fade-in duration-150">
                <div className="p-space-sm rounded-xl bg-surface-container-low flex flex-col gap-1">
                  <div className="flex justify-between items-center text-[10px] font-panchang text-on-surface-variant">
                    <span>Key-dwell Coefficient</span>
                    <span className="font-bold text-on-surface">15-second Alternating Sequence</span>
                  </div>
                  <div className="flex justify-between items-center text-[10px] font-panchang text-on-surface-variant">
                    <span>Model Feature Weight</span>
                    <span className="font-bold text-primary">18.0% Attribution</span>
                  </div>
                  <p className="font-panchang text-[10px] text-on-surface-variant mt-1 leading-normal">
                    Extracts micro-hesitations, velocity decrement (fatigue slope), and intra-individual tapping variability.
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Modality 5: Retinal Microvascular */}
          <div
            onClick={() => toggleModality('retina')}
            className="bg-surface-container-lowest rounded-2xl p-space-md shadow-xs border border-surface-container-high/40 transition-all cursor-pointer select-none hover:bg-surface-container-lowest/90"
          >
            <div className="flex items-center justify-between gap-space-sm">
              <div className="flex items-center gap-space-sm min-w-0">
                <div className="w-10 h-10 rounded-xl bg-tertiary-fixed-dim flex items-center justify-center shrink-0">
                  <span className="material-symbols-outlined text-tertiary text-[20px]">visibility</span>
                </div>
                <div className="flex flex-col min-w-0">
                  <h2 className="font-panchang text-[13px] font-bold text-on-surface truncate">
                    Retinal Layering (OCT)
                  </h2>
                  <span className="font-panchang text-[10px] text-on-surface-variant truncate">
                    Ganglion Cell &amp; Microvascular Density
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-space-xs shrink-0">
                <span className="px-2 py-0.5 rounded-full bg-surface-container-high text-on-surface-variant font-panchang text-[9px] font-bold">
                  W=0.11
                </span>
                <span
                  className="material-symbols-outlined text-[18px] text-on-surface-variant transition-transform duration-200"
                  style={{ transform: expandedModality === 'retina' ? 'rotate(180deg)' : 'rotate(0deg)' }}
                >
                  expand_more
                </span>
              </div>
            </div>

            {expandedModality === 'retina' && (
              <div className="pt-space-md flex flex-col gap-space-xs animate-in fade-in duration-150">
                <div className="p-space-sm rounded-xl bg-surface-container-low flex flex-col gap-1">
                  <div className="flex justify-between items-center text-[10px] font-panchang text-on-surface-variant">
                    <span>GCC Thinning Metric</span>
                    <span className="font-bold text-on-surface">Macular Volume Cross-section</span>
                  </div>
                  <div className="flex justify-between items-center text-[10px] font-panchang text-on-surface-variant">
                    <span>Model Feature Weight</span>
                    <span className="font-bold text-primary">10.3% Attribution</span>
                  </div>
                  <p className="font-panchang text-[10px] text-on-surface-variant mt-1 leading-normal">
                    Non-invasive window into central neurodegeneration detecting inner retinal thinning correlating with striatal dopamine transporter binding.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Recent Cohort Assessments Quick-Access with Search & Filter */}
      <section className="flex flex-col gap-space-sm">
        <div className="flex items-center justify-between">
          <div className="flex flex-col">
            <span className="font-panchang text-[11px] font-bold uppercase tracking-wider text-on-surface-variant">
              Active Research Cohort
            </span>
            <span className="font-panchang text-[10px] text-on-surface-variant">
              Longitudinal tracking &amp; cross-sectional search
            </span>
          </div>
          <div className="flex items-center gap-2">
            {selectedForCompare.length === 2 && (
              <button
                type="button"
                onClick={() => setIsComparisonModalOpen(true)}
                className="px-2.5 py-1 rounded-lg bg-primary text-on-primary font-panchang text-[10px] font-bold flex items-center gap-1 shadow-xs hover:bg-primary-container transition-all cursor-pointer animate-pulse"
              >
                <span className="material-symbols-outlined text-[14px]">compare_arrows</span>
                <span>Compare (2)</span>
              </button>
            )}
            <button
              type="button"
              onClick={() => onNavigate('results-dashboard')}
              className="font-panchang text-[11px] font-bold text-primary flex items-center gap-0.5 hover:underline cursor-pointer"
            >
              <span>Telemetry View</span>
              <span className="material-symbols-outlined text-[14px]">chevron_right</span>
            </button>
          </div>
        </div>

        {/* Quick Comparison Presets Bar */}
        <div className="flex items-center gap-1.5 overflow-x-auto py-1 no-scrollbar text-[10px] font-panchang">
          <span className="text-on-surface-variant font-semibold shrink-0 flex items-center gap-1">
            <span className="material-symbols-outlined text-[14px] text-primary">bolt</span>
            <span>Quick Compare:</span>
          </span>
          <button
            type="button"
            onClick={() => handleQuickPresetCompare('#PD-7821', '#PD-7819')}
            className="px-2.5 py-1 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface font-semibold shrink-0 transition-colors cursor-pointer border border-surface-container-high/40 flex items-center gap-1"
          >
            <span className="text-amber-700 font-bold">#PD-7821</span>
            <span className="text-on-surface-variant">vs</span>
            <span className="text-emerald-700 font-bold">#PD-7819</span>
            <span className="text-[9px] text-on-surface-variant/70 hidden sm:inline">(Elevated vs Low)</span>
          </button>
          <button
            type="button"
            onClick={() => handleQuickPresetCompare('#PD-7825', '#PD-7836')}
            className="px-2.5 py-1 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface font-semibold shrink-0 transition-colors cursor-pointer border border-surface-container-high/40 flex items-center gap-1"
          >
            <span className="text-amber-700 font-bold">#PD-7825</span>
            <span className="text-on-surface-variant">vs</span>
            <span className="text-emerald-700 font-bold">#PD-7836</span>
            <span className="text-[9px] text-on-surface-variant/70 hidden sm:inline">(Anosmia vs Normal)</span>
          </button>
        </div>

        {/* Search & Filter Controls Container */}
        <div className="bg-surface-container-lowest p-space-md rounded-2xl shadow-xs border border-surface-container-high/40 flex flex-col gap-space-sm">
          {/* Top Row: Search Input & Sort Dropdown */}
          <div className="flex flex-col sm:flex-row gap-2 items-stretch sm:items-center">
            {/* Search Input Box */}
            <div className="relative flex-1 flex items-center">
              <span className="material-symbols-outlined absolute left-3 text-[18px] text-on-surface-variant pointer-events-none">
                search
              </span>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by ID (e.g. PD-7821), notes, visit, age..."
                className="w-full h-10 pl-9 pr-8 rounded-xl bg-surface-container-low text-on-surface font-panchang text-[11px] outline-none focus:ring-2 focus:ring-primary/40 transition-all placeholder:text-on-surface-variant/60"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2.5 text-on-surface-variant hover:text-on-surface p-0.5 rounded-full cursor-pointer"
                  title="Clear search query"
                >
                  <span className="material-symbols-outlined text-[16px]">close</span>
                </button>
              )}
            </div>

            {/* Sort Dropdown Selector */}
            <div className="relative shrink-0 flex items-center">
              <span className="material-symbols-outlined absolute left-2.5 text-[16px] text-on-surface-variant pointer-events-none">
                sort
              </span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as 'risk-desc' | 'risk-asc' | 'id-asc')}
                className="h-10 pl-8 pr-7 rounded-xl bg-surface-container-low text-on-surface font-panchang text-[10px] font-semibold outline-none cursor-pointer appearance-none focus:ring-2 focus:ring-primary/40"
              >
                <option value="risk-desc">Risk: High → Low</option>
                <option value="risk-asc">Risk: Low → High</option>
                <option value="id-asc">Participant ID</option>
              </select>
              <span className="material-symbols-outlined absolute right-2 text-[16px] text-on-surface-variant pointer-events-none">
                expand_more
              </span>
            </div>
          </div>

          {/* Filter Chips Row */}
          <div className="flex items-center gap-1.5 overflow-x-auto py-0.5 no-scrollbar -mx-1 px-1">
            {/* All Filter */}
            <button
              type="button"
              onClick={() => setRiskFilter('all')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full font-panchang text-[10px] font-bold transition-all shrink-0 cursor-pointer ${
                riskFilter === 'all'
                  ? 'bg-primary text-on-primary shadow-xs'
                  : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container'
              }`}
            >
              <span>All</span>
              <span className={`px-1.5 py-0.2 rounded-full text-[9px] ${
                riskFilter === 'all' ? 'bg-on-primary/20 text-on-primary' : 'bg-surface-container text-on-surface-variant'
              }`}>
                {filterCounts.all}
              </span>
            </button>

            {/* Elevated Filter */}
            <button
              type="button"
              onClick={() => setRiskFilter('Elevated Pattern')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full font-panchang text-[10px] font-bold transition-all shrink-0 cursor-pointer ${
                riskFilter === 'Elevated Pattern'
                  ? 'bg-amber-600 text-white shadow-xs'
                  : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container'
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-amber-400 shrink-0"></span>
              <span>Elevated</span>
              <span className={`px-1.5 py-0.2 rounded-full text-[9px] ${
                riskFilter === 'Elevated Pattern' ? 'bg-white/25 text-white' : 'bg-surface-container text-on-surface-variant'
              }`}>
                {filterCounts.elevated}
              </span>
            </button>

            {/* Intermediate Filter */}
            <button
              type="button"
              onClick={() => setRiskFilter('Intermediate')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full font-panchang text-[10px] font-bold transition-all shrink-0 cursor-pointer ${
                riskFilter === 'Intermediate'
                  ? 'bg-secondary text-on-secondary shadow-xs'
                  : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container'
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-secondary-fixed shrink-0"></span>
              <span>Intermediate</span>
              <span className={`px-1.5 py-0.2 rounded-full text-[9px] ${
                riskFilter === 'Intermediate' ? 'bg-white/25 text-white' : 'bg-surface-container text-on-surface-variant'
              }`}>
                {filterCounts.intermediate}
              </span>
            </button>

            {/* Low Risk Filter */}
            <button
              type="button"
              onClick={() => setRiskFilter('Low Risk Pattern')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full font-panchang text-[10px] font-bold transition-all shrink-0 cursor-pointer ${
                riskFilter === 'Low Risk Pattern'
                  ? 'bg-emerald-600 text-white shadow-xs'
                  : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container'
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-emerald-400 shrink-0"></span>
              <span>Low Risk</span>
              <span className={`px-1.5 py-0.2 rounded-full text-[9px] ${
                riskFilter === 'Low Risk Pattern' ? 'bg-white/25 text-white' : 'bg-surface-container text-on-surface-variant'
              }`}>
                {filterCounts.low}
              </span>
            </button>

            {/* Family History Toggle */}
            <button
              type="button"
              onClick={() => setFamilyHistoryOnly(!familyHistoryOnly)}
              className={`flex items-center gap-1 px-2.5 py-1.5 rounded-full font-panchang text-[10px] font-bold transition-all shrink-0 cursor-pointer border ${
                familyHistoryOnly
                  ? 'bg-tertiary-fixed text-on-tertiary-fixed border-tertiary shadow-xs'
                  : 'bg-surface-container-low text-on-surface-variant border-transparent hover:bg-surface-container'
              }`}
            >
              <span className="material-symbols-outlined text-[14px]">genetics</span>
              <span>Family Hist.</span>
              {familyHistoryOnly && <span className="material-symbols-outlined text-[13px]">check</span>}
            </button>
          </div>

          {/* Search Result Counter & Reset Button */}
          <div className="flex items-center justify-between text-on-surface-variant pt-1 text-[10px] font-panchang border-t border-surface-container-high/30">
            <span>
              Showing <span className="font-bold text-on-surface">{filteredCohort.length}</span> of {activeCohortList.length} participants
            </span>
            {hasActiveFilters && (
              <button
                type="button"
                onClick={resetFilters}
                className="text-primary hover:underline font-bold flex items-center gap-1 cursor-pointer"
              >
                <span className="material-symbols-outlined text-[13px]">restart_alt</span>
                <span>Clear Filters</span>
              </button>
            )}
          </div>
        </div>

        {/* Cohort Participant List or Empty State */}
        {filteredCohort.length === 0 ? (
          <div className="bg-surface-container-lowest p-space-lg rounded-2xl shadow-xs border border-surface-container-high/40 flex flex-col items-center justify-center text-center gap-space-xs py-8">
            <div className="w-12 h-12 rounded-full bg-surface-container-low flex items-center justify-center text-on-surface-variant">
              <span className="material-symbols-outlined text-[24px]">person_search</span>
            </div>
            <span className="font-panchang text-[12px] font-bold text-on-surface mt-1">
              No matching cohort participants
            </span>
            <p className="font-panchang text-[10px] text-on-surface-variant max-w-xs leading-normal">
              {searchQuery
                ? `No participants match "${searchQuery}" under the current filter combination.`
                : 'No participants match the selected filter combination.'}
            </p>
            <button
              type="button"
              onClick={resetFilters}
              className="mt-2 px-3.5 py-1.5 rounded-xl bg-primary text-on-primary font-panchang text-[10px] font-bold shadow-xs hover:bg-primary-container transition-colors cursor-pointer"
            >
              Reset Search &amp; Filters
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-2 2xl:grid-cols-3 gap-3">
            {filteredCohort.map((participant) => {
              const isSelected = selectedForCompare.includes(participant.id);
              const selectionIndex = selectedForCompare.indexOf(participant.id);

              return (
                <div
                  key={participant.id}
                  onClick={() => onSelectCohortParticipant(participant)}
                  className={`flex items-center justify-between p-space-md rounded-2xl bg-surface-container-lowest shadow-xs border transition-all cursor-pointer select-none ${
                    isSelected
                      ? 'border-primary ring-2 ring-primary/20 bg-primary-fixed/5'
                      : 'border-surface-container-high/40 hover:bg-surface-container-low'
                  }`}
                >
                  <div className="flex items-center gap-space-sm min-w-0">
                    {/* Compare Selection Toggle */}
                    <button
                      type="button"
                      onClick={(e) => toggleCompareParticipant(participant.id, e)}
                      className={`w-7 h-7 rounded-lg flex items-center justify-center transition-all shrink-0 cursor-pointer border ${
                        isSelected
                          ? 'bg-primary border-primary text-on-primary shadow-xs ring-2 ring-primary/30'
                          : 'bg-surface-container-low border-surface-container-high/60 text-on-surface-variant hover:border-primary/50 hover:text-on-surface'
                      }`}
                      title={isSelected ? 'Remove from comparison' : 'Select for side-by-side comparison (max 2)'}
                    >
                      {isSelected ? (
                        <span className="font-panchang text-[10px] font-bold">
                          {selectionIndex === 0 ? 'A' : 'B'}
                        </span>
                      ) : (
                        <span className="material-symbols-outlined text-[15px] opacity-40 hover:opacity-100">
                          add
                        </span>
                      )}
                    </button>

                    <div
                      className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
                        participant.avatarType === 'amber'
                          ? 'bg-amber-50 text-amber-700'
                          : participant.avatarType === 'emerald'
                          ? 'bg-emerald-50 text-emerald-700'
                          : 'bg-surface-container-high text-on-surface-variant'
                      }`}
                    >
                      <span className="material-symbols-outlined text-[20px]">
                        {participant.avatarType === 'amber'
                          ? 'warning_amber'
                          : participant.avatarType === 'emerald'
                          ? 'check_circle'
                          : 'tune'}
                      </span>
                    </div>
                    <div className="flex flex-col min-w-0">
                      <div className="flex items-center gap-space-xs">
                        <span className="font-panchang text-[12px] font-bold text-on-surface">
                          {participant.id}
                        </span>
                        <span className="px-1.5 py-0.2 rounded bg-surface-container font-panchang text-[9px] text-on-surface-variant">
                          {participant.visit}
                        </span>
                        {participant.assessmentData.familyHistory && (
                          <span className="px-1.5 py-0.2 rounded bg-tertiary-fixed font-panchang text-[8px] font-bold text-on-tertiary-fixed">
                            1st° Fam
                          </span>
                        )}
                        {isSelected && (
                          <span className="px-1.5 py-0.2 rounded bg-primary/10 text-primary font-panchang text-[8px] font-bold">
                            Selected ({selectionIndex === 0 ? 'A' : 'B'})
                          </span>
                        )}
                      </div>
                      <span className="font-panchang text-[10px] text-on-surface-variant truncate">
                        {participant.notes}
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-col items-end shrink-0 gap-0.5">
                    <div className="flex items-baseline gap-1">
                      <span className="font-panchang text-[15px] font-bold text-on-surface">
                        {participant.riskIndex.toFixed(2)}
                      </span>
                      <span className="font-panchang text-[9px] text-on-surface-variant">idx</span>
                    </div>
                    <span
                      className={`px-2 py-0.5 rounded-full font-panchang text-[9px] font-bold ${
                        participant.riskClass === 'Elevated Pattern'
                          ? 'bg-amber-100 text-amber-900'
                          : participant.riskClass === 'Low Risk Pattern'
                          ? 'bg-emerald-100 text-emerald-900'
                          : 'bg-secondary-container text-on-secondary-container'
                      }`}
                    >
                      {participant.riskClass}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Floating Comparison Dock when participants are selected */}
      {selectedForCompare.length > 0 && (
        <div className="fixed bottom-24 lg:bottom-8 left-1/2 -translate-x-1/2 lg:left-auto lg:right-8 lg:translate-x-0 w-[92%] max-w-lg lg:max-w-md z-40 bg-surface-container-lowest/95 backdrop-blur-md p-3.5 rounded-2xl shadow-2xl border border-primary/30 flex items-center justify-between gap-3 animate-in slide-in-from-bottom-3 duration-200">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-8 h-8 rounded-xl bg-primary-fixed flex items-center justify-center text-primary shrink-0">
              <span className="material-symbols-outlined text-[18px]">compare_arrows</span>
            </div>
            <div className="flex flex-col min-w-0">
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="px-2 py-0.5 rounded-md bg-primary text-on-primary font-panchang text-[9px] font-bold">
                  A: {selectedForCompare[0]}
                </span>
                <span className="font-panchang text-[10px] text-on-surface-variant font-bold">vs</span>
                {selectedForCompare[1] ? (
                  <span className="px-2 py-0.5 rounded-md bg-secondary text-on-secondary font-panchang text-[9px] font-bold">
                    B: {selectedForCompare[1]}
                  </span>
                ) : (
                  <span className="font-panchang text-[9px] text-on-surface-variant italic animate-pulse">
                    Select 2nd participant...
                  </span>
                )}
              </div>
              <span className="font-panchang text-[9px] text-on-surface-variant hidden sm:inline">
                {selectedForCompare.length === 2 ? 'Ready for side-by-side risk fusion comparison' : 'Choose one more from cohort below'}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => setSelectedForCompare([])}
              className="px-2.5 py-1.5 rounded-xl text-on-surface-variant hover:bg-surface-container font-panchang text-[10px] font-semibold transition-colors cursor-pointer"
            >
              Clear
            </button>
            <button
              type="button"
              disabled={selectedForCompare.length < 2}
              onClick={() => setIsComparisonModalOpen(true)}
              className="px-3.5 py-1.5 rounded-xl bg-primary text-on-primary font-panchang text-[10px] font-bold shadow-xs hover:bg-primary-container transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1"
            >
              <span>Compare</span>
              <span className="material-symbols-outlined text-[14px]">open_in_full</span>
            </button>
          </div>
        </div>
      )}

      {/* Side-by-Side Comparison Modal */}
      {participantA && participantB && (
        <ParticipantComparisonModal
          isOpen={isComparisonModalOpen}
          onClose={() => setIsComparisonModalOpen(false)}
          participantA={participantA}
          participantB={participantB}
          onSelectParticipant={(p) => {
            setIsComparisonModalOpen(false);
            onSelectCohortParticipant(p);
          }}
          onSwap={handleSwapCompare}
        />
      )}

      {/* Interactive Risk Simulator Teaser */}
      <section className="bg-gradient-to-br from-primary-fixed to-secondary-container p-space-lg lg:p-8 rounded-3xl flex flex-col lg:flex-row lg:items-center lg:justify-between gap-space-md shadow-xs border border-primary/10">
        <div className="flex flex-col gap-1 max-w-2xl">
          <div className="flex items-center gap-2">
            <span className="font-panchang text-[10px] font-bold uppercase tracking-wider text-on-primary-fixed">
              Interactive Simulator
            </span>
            <span className="material-symbols-outlined text-primary text-[18px]">science</span>
          </div>
          <h2 className="font-panchang text-headline-sm lg:text-headline-md text-on-surface font-bold">
            Multimodal Fusion Matrix
          </h2>
          <p className="font-panchang text-[11px] sm:text-xs text-on-secondary-fixed-variant leading-relaxed">
            Simulate synthetic participant values across all 5 streams to preview how the XGBoost + SHAP inference engine computes probabilistic risk indexes.
          </p>
        </div>
        <button
          type="button"
          onClick={() => onNavigate('explainability-shap')}
          className="self-start lg:self-center shrink-0 inline-flex items-center gap-space-xs px-space-lg py-3 rounded-xl bg-on-secondary text-primary font-panchang text-[11px] font-bold shadow-xs hover:bg-surface-container-lowest transition-all cursor-pointer active:scale-98"
        >
          <span>Open Explainability (SHAP) Engine</span>
          <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
        </button>
      </section>

      {/* Ethics & Clinical Disclaimer Footer Card */}
      <footer className="bg-surface-container p-space-md rounded-2xl flex flex-col gap-space-xs mt-space-sm border border-surface-container-high/40">
        <div className="flex items-center gap-space-xs text-on-surface-variant">
          <span className="material-symbols-outlined text-[16px] text-tertiary">balance</span>
          <span className="font-panchang text-[11px] font-bold uppercase tracking-wider">
            Ethical Research Directive
          </span>
        </div>
        <p className="font-panchang text-disclaimer-text text-on-surface-variant leading-normal">
          Research estimate. Not a diagnosis. MPF-PD models probabilistic multimodal patterns for clinical investigational use only. This application does not render medical decisions or replace in-person neurological evaluations. Data transmissions are de-identified under HIPAA &amp; GDPR neuro-phenotype protocols.
        </p>
        <div className="flex items-center justify-between pt-space-xs border-t border-surface-container-high/40 text-[9px] font-panchang text-on-surface-variant">
          <span>Consortium for Prodromal Biomarkers</span>
          <span>Build 2.4.0-RC1</span>
        </div>
      </footer>
    </div>
  );
};
