import React, { useState, useRef } from 'react';
import { ScreenId, AssessmentData } from '../types';

interface AssessmentScreenProps {
  assessmentData: AssessmentData;
  onUpdateAssessmentData: (data: AssessmentData) => void;
  onRunFusion: () => Promise<void> | void;
  onNavigate: (screen: ScreenId) => void;
}

export const AssessmentScreen: React.FC<AssessmentScreenProps> = ({
  assessmentData,
  onUpdateAssessmentData,
  onRunFusion,
  onNavigate,
}) => {
  const [isRunning, setIsRunning] = useState(false);
  const [saveToast, setSaveToast] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const motorFileInputRef = useRef<HTMLInputElement>(null);
  const retinalFileInputRef = useRef<HTMLInputElement>(null);

  const handleFieldChange = <K extends keyof AssessmentData>(key: K, value: AssessmentData[K]) => {
    onUpdateAssessmentData({
      ...assessmentData,
      [key]: value,
    });
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onUpdateAssessmentData({
        ...assessmentData,
        voiceFileName: file.name,
        isVoiceUploaded: true,
        voiceFile: file,
      });
    }
  };

  const handleMotorFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onUpdateAssessmentData({
        ...assessmentData,
        motorFileName: file.name,
        motorFile: file,
      });
    }
  };

  const handleRetinalFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onUpdateAssessmentData({
        ...assessmentData,
        retinalFileName: file.name,
        retinalFile: file,
      });
    }
  };

  const triggerFusion = async () => {
    setIsRunning(true);
    try {
      await onRunFusion();
    } finally {
      setIsRunning(false);
    }
  };

  const handleSaveDraft = () => {
    setSaveToast(true);
    setTimeout(() => {
      setSaveToast(false);
    }, 2400);
  };

  return (
    <div className="flex flex-col w-full gap-space-md mx-auto pb-space-xl animate-in fade-in duration-200">
      {/* Step Progress Header Container */}
      <section className="flex flex-col bg-surface-container-lowest p-space-md sm:p-space-lg rounded-2xl shadow-xs border border-surface-container-high/40 gap-space-sm">
        <div className="flex items-center justify-between">
          <span className="font-label-sm text-label-sm uppercase tracking-wider text-primary font-semibold">
            Assessment Protocol
          </span>
          <span className="font-label-sm text-label-sm text-on-surface-variant font-medium">
            Step 2 of 5 • Data Ingestion
          </span>
        </div>

        {/* Active Progress Bar */}
        <div className="w-full bg-surface-container h-2 rounded-full overflow-hidden">
          <div className="bg-primary-container h-full rounded-full transition-all duration-500 w-[40%]"></div>
        </div>

        {/* Scrollable Stepper Pills */}
        <div className="flex items-center gap-space-xs overflow-x-auto py-1 no-scrollbar -mx-1 px-1">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-surface-container-low text-on-surface-variant shrink-0">
            <span className="material-symbols-outlined text-[14px] text-tertiary">check_circle</span>
            <span className="font-label-sm text-[11px] whitespace-nowrap">1. Cohort ID</span>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-primary-fixed text-on-primary-fixed shrink-0 shadow-xs">
            <span className="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
            <span className="font-label-sm text-[11px] whitespace-nowrap font-bold">2. Olfactory &amp; Sleep</span>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-surface-container-low text-on-surface-variant/70 shrink-0">
            <span className="font-label-sm text-[11px] whitespace-nowrap">3. Acoustic Voice</span>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-surface-container-low text-on-surface-variant/70 shrink-0">
            <span className="font-label-sm text-[11px] whitespace-nowrap">4. Motor Tapping</span>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-surface-container-low text-on-surface-variant/70 shrink-0">
            <span className="font-label-sm text-[11px] whitespace-nowrap">5. Retinal OCT</span>
          </div>
        </div>
      </section>

      {/* Participant Demographics Brief Card */}
      <section className="bg-surface-container-lowest p-space-md sm:p-space-lg rounded-2xl shadow-xs border border-surface-container-high/40 flex flex-col gap-space-xs">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-space-xs">
            <span className="material-symbols-outlined text-primary text-[20px]">badge</span>
            <span className="font-label-md text-label-md text-on-surface font-semibold">
              {assessmentData.cohortId}
            </span>
          </div>
          <span className="font-label-sm text-label-sm px-2.5 py-0.5 rounded-full bg-secondary-container text-on-secondary-container">
            Active Cohort M-12
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-space-xs pt-space-xs">
          <div className="flex flex-col bg-surface-container-low p-3 rounded-xl">
            <span className="font-label-sm text-[10px] text-on-surface-variant uppercase tracking-wider">Age (Req)</span>
            <span className="font-headline-sm text-headline-sm text-on-surface">{assessmentData.age} yrs</span>
          </div>
          <div className="flex flex-col bg-surface-container-low p-3 rounded-xl">
            <span className="font-label-sm text-[10px] text-on-surface-variant uppercase tracking-wider">Biological Sex</span>
            <span className="font-headline-sm text-headline-sm text-on-surface">{assessmentData.biologicalSex}</span>
          </div>
          <div className="flex flex-col bg-surface-container-low p-3 rounded-xl">
            <span className="font-label-sm text-[10px] text-on-surface-variant uppercase tracking-wider">Family Hist.</span>
            <span className="font-headline-sm text-headline-sm text-tertiary font-semibold">
              {assessmentData.familyHistory ? 'Yes (1st°)' : 'None Reported'}
            </span>
          </div>
        </div>
      </section>

      {/* Modality Sections Container (Responsive 2-Column Grid on Desktop) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-space-md items-start">
        {/* Section A: Olfactory Evaluation */}
        <div 
          className={`bg-surface-container-lowest p-space-lg rounded-2xl shadow-xs border border-surface-container-high/40 flex flex-col gap-space-md transition-all duration-300 ${
            assessmentData.olfactoryMissing ? 'opacity-60 bg-surface-container-low/60' : ''
          }`}
        >
          <div className="flex items-start justify-between">
            <div className="flex flex-col">
              <span className="font-label-sm text-label-sm uppercase tracking-wider text-tertiary font-semibold">
                Section A • Psychophysics
              </span>
              <h3 className="font-headline-sm text-headline-sm text-on-surface font-semibold">
                Olfactory Evaluation
              </h3>
            </div>
            <span className="material-symbols-outlined text-tertiary-container text-[24px]">air</span>
          </div>

          {/* Mark as Missing Toggle */}
          <label className="flex items-center justify-between p-space-sm rounded-xl bg-surface-container-low cursor-pointer select-none border border-surface-container-high/30">
            <div className="flex items-center gap-space-xs">
              <span className="material-symbols-outlined text-secondary text-[18px]">block</span>
              <span className="font-label-md text-label-md text-on-surface-variant">
                Modality unavailable / participant excluded
              </span>
            </div>
            <input
              type="checkbox"
              checked={assessmentData.olfactoryMissing}
              onChange={(e) => handleFieldChange('olfactoryMissing', e.target.checked)}
              className="w-4 h-4 rounded text-primary accent-primary cursor-pointer"
            />
          </label>

          {/* Content Area */}
          <div className={`flex flex-col gap-space-sm transition-opacity ${assessmentData.olfactoryMissing ? 'opacity-30 pointer-events-none' : ''}`}>
            <div className="flex flex-col gap-1.5">
              <label className="font-label-md text-label-md text-on-surface font-medium">Test Protocol Instrument</label>
              <div className="grid grid-cols-2 gap-space-xs">
                <button
                  type="button"
                  onClick={() => handleFieldChange('olfactoryInstrument', 'UPSIT (40-item)')}
                  className={`py-2.5 px-3 rounded-lg font-label-md text-label-md text-center font-semibold transition-all ${
                    assessmentData.olfactoryInstrument === 'UPSIT (40-item)'
                      ? 'bg-primary-fixed text-on-primary-fixed shadow-xs'
                      : 'bg-surface-container text-on-surface-variant'
                  }`}
                >
                  UPSIT (40-item)
                </button>
                <button
                  type="button"
                  onClick={() => handleFieldChange('olfactoryInstrument', "Sniffin' Sticks 16")}
                  className={`py-2.5 px-3 rounded-lg font-label-md text-label-md text-center font-semibold transition-all ${
                    assessmentData.olfactoryInstrument === "Sniffin' Sticks 16"
                      ? 'bg-primary-fixed text-on-primary-fixed shadow-xs'
                      : 'bg-surface-container text-on-surface-variant'
                  }`}
                >
                  Sniffin' Sticks 16
                </button>
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between items-center">
                <label className="font-label-md text-label-md text-on-surface font-medium">
                  Observed Correct Identification
                </label>
                <span className="font-label-sm text-label-sm text-on-surface-variant">Scale: 0 - 40</span>
              </div>
              <div className="relative flex items-center">
                <input
                  type="number"
                  min="0"
                  max="40"
                  value={assessmentData.olfactoryScore}
                  onChange={(e) => handleFieldChange('olfactoryScore', Number(e.target.value))}
                  className="w-full h-11 px-3.5 rounded-lg bg-surface-container text-on-surface font-headline-sm text-headline-sm outline-none focus:ring-2 focus:ring-primary/40 transition-all"
                />
                <span className="absolute right-3 font-label-md text-label-md text-on-surface-variant">
                  / 40 items
                </span>
              </div>
            </div>

            {/* Micro-validation Alert */}
            {assessmentData.olfactoryScore <= 18 ? (
              <div className="flex items-start gap-space-xs p-space-sm rounded-xl bg-error-container/30 text-on-surface border border-error-container">
                <span className="material-symbols-outlined text-error text-[18px] shrink-0 mt-0.5">warning</span>
                <div className="flex flex-col text-on-surface">
                  <span className="font-label-sm text-[11px] font-semibold text-error">
                    Hyposmia Signal Detected (Score {assessmentData.olfactoryScore})
                  </span>
                  <span className="font-body-sm text-body-sm text-on-surface-variant">
                    Well below age 60+ normative median (≥32). Conforms to prodromal cluster threshold.
                  </span>
                </div>
              </div>
            ) : assessmentData.olfactoryScore < 32 ? (
              <div className="flex items-start gap-space-xs p-space-sm rounded-xl bg-amber-50 text-amber-900 border border-amber-200">
                <span className="material-symbols-outlined text-amber-700 text-[18px] shrink-0 mt-0.5">info</span>
                <div className="flex flex-col">
                  <span className="font-label-sm text-[11px] font-semibold text-amber-900">
                    Borderline Olfactory Score (Score {assessmentData.olfactoryScore})
                  </span>
                  <span className="font-body-sm text-body-sm text-amber-800">
                    Sub-normative identification. Mild risk shift assigned in model tensor.
                  </span>
                </div>
              </div>
            ) : (
              <div className="flex items-start gap-space-xs p-space-sm rounded-xl bg-emerald-50 text-emerald-900 border border-emerald-200">
                <span className="material-symbols-outlined text-emerald-700 text-[18px] shrink-0 mt-0.5">check_circle</span>
                <div className="flex flex-col">
                  <span className="font-label-sm text-[11px] font-semibold text-emerald-900">
                    Normative Olfactory Function (Score {assessmentData.olfactoryScore})
                  </span>
                  <span className="font-body-sm text-body-sm text-emerald-800">
                    Expected sensory function for age cohort. Minimal risk attribution.
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Section B: Sleep / RBD Screening */}
        <div 
          className={`bg-surface-container-lowest p-space-lg rounded-2xl shadow-xs border border-surface-container-high/40 flex flex-col gap-space-md transition-all duration-300 ${
            assessmentData.sleepMissing ? 'opacity-60 bg-surface-container-low/60' : ''
          }`}
        >
          <div className="flex items-start justify-between">
            <div className="flex flex-col">
              <span className="font-label-sm text-label-sm uppercase tracking-wider text-tertiary font-semibold">
                Section B • Parasomnia
              </span>
              <h3 className="font-headline-sm text-headline-sm text-on-surface font-semibold">
                Sleep &amp; RBD Architecture
              </h3>
            </div>
            <span className="material-symbols-outlined text-tertiary-container text-[24px]">bedtime</span>
          </div>

          {/* Mark as Missing Toggle */}
          <label className="flex items-center justify-between p-space-sm rounded-xl bg-surface-container-low cursor-pointer select-none border border-surface-container-high/30">
            <div className="flex items-center gap-space-xs">
              <span className="material-symbols-outlined text-secondary text-[18px]">block</span>
              <span className="font-label-md text-label-md text-on-surface-variant">
                Sleep questionnaire not administered
              </span>
            </div>
            <input
              type="checkbox"
              checked={assessmentData.sleepMissing}
              onChange={(e) => handleFieldChange('sleepMissing', e.target.checked)}
              className="w-4 h-4 rounded text-primary accent-primary cursor-pointer"
            />
          </label>

          <div className={`flex flex-col gap-space-sm transition-opacity ${assessmentData.sleepMissing ? 'opacity-30 pointer-events-none' : ''}`}>
            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between items-center">
                <label className="font-label-md text-label-md text-on-surface font-medium">
                  RBDSQ Total Cumulative Score
                </label>
                <span className="font-label-sm text-label-sm text-error font-medium">Pattern cut-off: ≥ 5</span>
              </div>
              <div className="relative flex items-center">
                <input
                  type="number"
                  min="0"
                  max="13"
                  value={assessmentData.rbdsqScore}
                  onChange={(e) => handleFieldChange('rbdsqScore', Number(e.target.value))}
                  className="w-full h-11 px-3.5 rounded-lg bg-surface-container text-on-surface font-headline-sm text-headline-sm outline-none focus:ring-2 focus:ring-primary/40 transition-all"
                />
                <span className="absolute right-3 font-label-md text-label-md text-on-surface-variant">
                  Range: 0 - 13
                </span>
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="font-label-md text-label-md text-on-surface font-medium">
                Reported Dream-Enactment Behaviors
              </label>
              <div className="relative">
                <select
                  value={assessmentData.dreamEnactmentBehavior}
                  onChange={(e) => handleFieldChange('dreamEnactmentBehavior', e.target.value)}
                  className="w-full h-11 px-3.5 rounded-lg bg-surface-container text-on-surface font-body-md text-body-md outline-none appearance-none cursor-pointer pr-10 focus:ring-2 focus:ring-primary/40"
                >
                  <option>Frequent (3+ nights/week, vocalizations &amp; motor jerks)</option>
                  <option>Occasional (1-2 nights per month)</option>
                  <option>Rare / Isolated lifetime episodes</option>
                  <option>Absent / Normal polysomnography</option>
                </select>
                <span className="material-symbols-outlined absolute right-3 top-3 pointer-events-none text-on-surface-variant text-[20px]">
                  expand_more
                </span>
              </div>
            </div>

            <div className="flex items-center gap-space-xs p-space-sm rounded-xl bg-surface-container text-on-surface">
              <span className="material-symbols-outlined text-tertiary text-[18px]">verified</span>
              <span className="font-body-sm text-body-sm text-on-surface-variant">
                REM Sleep Behavior Disorder screening correlates strongly with synucleinopathy signatures.
              </span>
            </div>
          </div>
        </div>

        {/* Section C: Voice Biomarker Recording */}
        <div 
          className={`bg-surface-container-lowest p-space-lg rounded-2xl shadow-xs border border-surface-container-high/40 flex flex-col gap-space-md transition-all duration-300 ${
            assessmentData.voiceMissing ? 'opacity-60 bg-surface-container-low/60' : ''
          }`}
        >
          <div className="flex items-start justify-between">
            <div className="flex flex-col">
              <span className="font-label-sm text-label-sm uppercase tracking-wider text-tertiary font-semibold">
                Section C • Acoustics
              </span>
              <h3 className="font-headline-sm text-headline-sm text-on-surface font-semibold">
                Voice Tremor &amp; Articulation
              </h3>
            </div>
            <span className="material-symbols-outlined text-tertiary-container text-[24px]">graphic_eq</span>
          </div>

          {/* Mark as Missing Toggle */}
          <label className="flex items-center justify-between p-space-sm rounded-xl bg-surface-container-low cursor-pointer select-none border border-surface-container-high/30">
            <div className="flex items-center gap-space-xs">
              <span className="material-symbols-outlined text-secondary text-[18px]">block</span>
              <span className="font-label-md text-label-md text-on-surface-variant">
                Participant dysphonic or unable to vocalize
              </span>
            </div>
            <input
              type="checkbox"
              checked={assessmentData.voiceMissing}
              onChange={(e) => handleFieldChange('voiceMissing', e.target.checked)}
              className="w-4 h-4 rounded text-primary accent-primary cursor-pointer"
            />
          </label>

          <div className={`flex flex-col gap-space-sm transition-opacity ${assessmentData.voiceMissing ? 'opacity-30 pointer-events-none' : ''}`}>
            {/* Hidden actual file input */}
            <input 
              type="file" 
              ref={fileInputRef} 
              accept=".wav,.mp3,.m4a,.aac" 
              className="hidden" 
              onChange={handleFileUpload} 
            />

            {/* Interactive Drag / Drop Zone */}
            <div
              onClick={() => fileInputRef.current?.click()}
              className="bg-surface-container-low rounded-xl p-space-md flex flex-col items-center justify-center text-center gap-space-xs cursor-pointer hover:bg-surface-container transition-colors border-2 border-dashed border-surface-container-high"
            >
              <div className="w-10 h-10 rounded-full bg-primary-fixed flex items-center justify-center text-primary">
                <span className="material-symbols-outlined text-[20px]">mic</span>
              </div>
              <span className="font-label-md text-label-md text-on-surface font-semibold">
                Upload Sustained /a/ Phonation (.wav)
              </span>
              <span className="font-body-sm text-body-sm text-on-surface-variant">
                Recommended: 5s continuous tone in quiet ambient setting
              </span>
            </div>

            {/* Attached File Status Pill */}
            {assessmentData.isVoiceUploaded && (
              <div className="flex items-center justify-between p-space-sm rounded-xl bg-surface-container border border-surface-container-high/60">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="material-symbols-outlined text-primary text-[20px]">audio_file</span>
                  <div className="flex flex-col min-w-0">
                    <span className="font-label-md text-label-md font-semibold text-on-surface truncate">
                      {assessmentData.voiceFileName}
                    </span>
                    <span className="font-disclaimer-text text-disclaimer-text text-on-surface-variant truncate">
                      {assessmentData.voiceDuration}s • 44.1kHz 16-bit • Jitter: {assessmentData.voiceJitter}%
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  <span className="px-2 py-0.5 rounded-full bg-surface-container-lowest text-tertiary font-label-sm text-[10px] font-bold">
                    Optimal
                  </span>
                  <button
                    type="button"
                    onClick={() => handleFieldChange('isVoiceUploaded', false)}
                    className="text-on-surface-variant hover:text-error p-1"
                    title="Remove audio file"
                  >
                    <span className="material-symbols-outlined text-[18px]">close</span>
                  </button>
                </div>
              </div>
            )}

            {/* Mini Waveform Visualizer Decorator */}
            <div className="flex items-center justify-between gap-1 h-6 px-3 bg-surface-container-low rounded-lg overflow-hidden">
              <div className="h-2 w-1 bg-primary/40 rounded-full animate-pulse"></div>
              <div className="h-4 w-1 bg-primary/60 rounded-full animate-pulse delay-75"></div>
              <div className="h-5 w-1 bg-primary rounded-full animate-pulse delay-100"></div>
              <div className="h-3 w-1 bg-primary/70 rounded-full animate-pulse delay-150"></div>
              <div className="h-6 w-1 bg-primary rounded-full animate-pulse delay-200"></div>
              <div className="h-4 w-1 bg-primary/50 rounded-full animate-pulse delay-75"></div>
              <div className="h-2 w-1 bg-primary/30 rounded-full"></div>
              <div className="h-5 w-1 bg-primary/80 rounded-full animate-pulse delay-150"></div>
              <div className="h-3 w-1 bg-primary/60 rounded-full animate-pulse delay-100"></div>
              <div className="h-1 w-1 bg-primary/40 rounded-full"></div>
              <div className="h-4 w-1 bg-primary/70 rounded-full animate-pulse delay-200"></div>
              <div className="h-5 w-1 bg-primary rounded-full animate-pulse delay-75"></div>
              <div className="h-2 w-1 bg-primary/30 rounded-full"></div>
            </div>
          </div>
        </div>

        {/* Section D: Motor Kinematics (Alternating Tapping) */}
        <div 
          className={`bg-surface-container-lowest p-space-lg rounded-2xl shadow-xs border border-surface-container-high/40 flex flex-col gap-space-md transition-all duration-300 ${
            assessmentData.motorMissing ? 'opacity-60 bg-surface-container-low/60' : ''
          }`}
        >
          <div className="flex items-start justify-between">
            <div className="flex flex-col">
              <span className="font-label-sm text-label-sm uppercase tracking-wider text-tertiary font-semibold">
                Section D • Motor Control
              </span>
              <h3 className="font-headline-sm text-headline-sm text-on-surface font-semibold">
                Alternating Finger Tapping
              </h3>
            </div>
            <span className="material-symbols-outlined text-tertiary-container text-[24px]">touch_app</span>
          </div>

          {/* Mark as Missing Toggle */}
          <label className="flex items-center justify-between p-space-sm rounded-xl bg-surface-container-low cursor-pointer select-none border border-surface-container-high/30">
            <div className="flex items-center gap-space-xs">
              <span className="material-symbols-outlined text-secondary text-[18px]">block</span>
              <span className="font-label-md text-label-md text-on-surface-variant">
                Upper extremity musculoskeletal impairment
              </span>
            </div>
            <input
              type="checkbox"
              checked={assessmentData.motorMissing}
              onChange={(e) => handleFieldChange('motorMissing', e.target.checked)}
              className="w-4 h-4 rounded text-primary accent-primary cursor-pointer"
            />
          </label>

          <div className={`flex flex-col gap-space-sm transition-opacity ${assessmentData.motorMissing ? 'opacity-30 pointer-events-none' : ''}`}>
            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between items-center">
                <label className="font-label-md text-label-md text-on-surface font-medium">
                  Kinematic Tapping Frequency
                </label>
                <span className="font-label-sm text-label-sm text-on-surface-variant">Baseline: &gt; 4.5 taps/s</span>
              </div>
              <div className="relative flex items-center">
                <input
                  type="number"
                  step="0.1"
                  value={assessmentData.tappingFrequency}
                  onChange={(e) => handleFieldChange('tappingFrequency', Number(e.target.value))}
                  className="w-full h-11 px-3.5 rounded-lg bg-surface-container text-on-surface font-headline-sm text-headline-sm outline-none focus:ring-2 focus:ring-primary/40 transition-all"
                />
                <span className="absolute right-3 font-label-md text-label-md text-on-surface-variant">
                  taps / sec
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-space-xs">
              <div className="bg-surface-container-low p-2.5 rounded-xl flex flex-col gap-0.5 border border-surface-container-high/30">
                <span className="font-label-sm text-[10px] text-on-surface-variant uppercase font-panchang">
                  KINETIC FATIGUE SLOPE
                </span>
                <span className="font-headline-sm text-headline-sm text-on-surface">
                  {assessmentData.fatigueSlope} s⁻¹
                </span>
              </div>
              <div className="bg-surface-container-low p-2.5 rounded-xl flex flex-col gap-0.5 border border-surface-container-high/30">
                <span className="font-label-sm text-[10px] text-on-surface-variant uppercase font-panchang">
                  RHYTHM IRREGULARITY
                </span>
                <span className="font-headline-sm text-headline-sm text-on-surface">
                  {assessmentData.rhythmIrregularity} %
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Section E: Retinal OCT Scans */}
        <div 
          className={`lg:col-span-2 bg-surface-container-lowest p-space-lg rounded-2xl shadow-xs border border-surface-container-high/40 flex flex-col gap-space-md transition-all duration-300 ${
            assessmentData.retinalMissing ? 'bg-surface-container-low/40' : ''
          }`}
        >
          <div className="flex items-start justify-between">
            <div className="flex flex-col">
              <span className="font-label-sm text-label-sm uppercase tracking-wider text-tertiary font-semibold">
                Section E • Retinal Imaging
              </span>
              <h3 className="font-headline-sm text-headline-sm text-on-surface font-semibold">
                Retinal RNFL / GCC OCT
              </h3>
            </div>
            <span className="material-symbols-outlined text-tertiary-container text-[24px]">visibility</span>
          </div>

          {/* Mark as Missing Toggle */}
          <label className="flex items-center justify-between p-space-sm rounded-xl bg-surface-container-low cursor-pointer select-none border border-surface-container-high/30">
            <div className="flex items-center gap-space-xs">
              <span className="material-symbols-outlined text-secondary text-[18px]">block</span>
              <span className="font-label-md text-label-md text-on-surface-variant">
                Ophthalmic scan not acquired
              </span>
            </div>
            <input
              type="checkbox"
              checked={assessmentData.retinalMissing}
              onChange={(e) => handleFieldChange('retinalMissing', e.target.checked)}
              className="w-4 h-4 rounded text-primary accent-primary cursor-pointer"
            />
          </label>

          <div className={`flex flex-col gap-space-sm transition-opacity ${assessmentData.retinalMissing ? 'opacity-40' : ''}`}>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-space-sm">
              {/* Image 1: Fundus View */}
              <div className="flex flex-col gap-1">
                <div className="relative rounded-xl overflow-hidden bg-surface-container aspect-video sm:aspect-square lg:aspect-[4/3] border border-surface-container-high/40">
                  <img
                    alt="Clinical optical coherence tomography fundus view showing optic disc and retinal nerve fiber layer contours"
                    className="w-full h-full object-cover"
                    src="https://lh3.googleusercontent.com/aida-public/AB6AXuC3rOvmQQXdYO_V-kQIIV2Hf65JlmTV3apoWQhQn8PtJHZjh5V12NAvbE5gkpwI0HeEhL0V2hFPaJqHgNZqRcC3-IHyjl3Bbuqd_P8ov4pt-b4cJ5-6JdBJv2FUgkoMvTEWuc7LXL4TRD4R8cXSm5JrV7zhi36A8GwLsZbtDt8TujM3XRN-fnJUogtv1etfy5pOB3Tqi_i2-H9-VpBWCJHkeMPRSO6v0K54V0BCTuoQXNc1J6t12p6i"
                  />
                  <div className="absolute bottom-1.5 left-1.5 px-2 py-0.5 rounded bg-inverse-surface/80 text-inverse-on-surface font-label-sm text-[9px]">
                    OD RNFL
                  </div>
                </div>
                <span className="font-label-sm text-[10px] text-on-surface-variant text-center">
                  Right Eye (Peripapillary)
                </span>
              </div>

              {/* Image 2: GCC Tomography Layer */}
              <div className="flex flex-col gap-1">
                <div className="relative rounded-xl overflow-hidden bg-surface-container aspect-video sm:aspect-square lg:aspect-[4/3] border border-surface-container-high/40">
                  <img
                    alt="Cross-sectional optical coherence tomography scan displaying ganglion cell complex thinning analysis"
                    className="w-full h-full object-cover"
                    src="https://lh3.googleusercontent.com/aida-public/AB6AXuC_zwJfUeXWOoNl_gIbU3_zHprR3Y1HnQW10tklaYJXTSIbceiyi-bbkB5WpnHB6U5hiChW53exeilblBulnvD8V9VWkdtoAjhwK1YWDKOlZZV0lcfBJaALZ0rGB6zHoQoGX5r1jsp8t95zjz1mY0lmLyQTuKKXlKZw4ZHvcWKa9q35UpmnPm6VfplTcMm7eo0FhhF344aeYfzlSMQkluT76nqiX5izo6Fx6AaQneVKWArCjID329GZ"
                  />
                  <div className="absolute bottom-1.5 left-1.5 px-2 py-0.5 rounded bg-inverse-surface/80 text-inverse-on-surface font-label-sm text-[9px]">
                    OS GCC
                  </div>
                </div>
                <span className="font-label-sm text-[10px] text-on-surface-variant text-center">
                  Left Eye (Macular Grid)
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between p-space-sm rounded-xl bg-surface-container-low border border-surface-container-high/40">
              <div className="flex items-center gap-space-xs">
                <span className="material-symbols-outlined text-tertiary text-[18px]">check_circle</span>
                <span className="font-label-md text-label-md text-on-surface">Layer Segmentation</span>
              </div>
              <span className="font-label-sm text-label-sm font-semibold text-primary">
                Automated QC Passed
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Missing Modality & Uncertainty Guidance Notice */}
      <section className="bg-surface-container p-space-md rounded-2xl flex flex-col gap-space-xs border border-surface-container-high/40">
        <div className="flex items-center gap-space-xs text-on-surface">
          <span className="material-symbols-outlined text-tertiary text-[20px]">hub</span>
          <h4 className="font-label-md text-label-md font-semibold">
            Multimodal Imputation &amp; Uncertainty Tolerance
          </h4>
        </div>
        <p className="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">
          MPF-PD uses Bayesian Variational Autoencoding to tolerate partial inputs. When a modality is marked missing, confidence intervals widen automatically without corrupting integrated cross-channel risk gradients.
        </p>
      </section>

      {/* Sticky Form Action Bar (Stays pinned above main nav or bottom on desktop) */}
      <div className="sticky bottom-20 lg:bottom-6 z-40 bg-surface-container-lowest/95 backdrop-blur-lg p-space-sm rounded-2xl shadow-lg border border-surface-container-high/60 flex items-center gap-space-sm max-w-2xl mx-auto w-full">
        <button
          type="button"
          onClick={handleSaveDraft}
          className="flex-1 h-11 px-3 rounded-lg bg-surface-container text-on-surface-variant font-label-md text-label-md font-semibold hover:bg-surface-container-high transition-colors text-center cursor-pointer active:scale-98"
        >
          Save Draft
        </button>

        <button
          type="button"
          disabled={isRunning}
          onClick={triggerFusion}
          className="flex-[2] h-11 px-4 rounded-lg bg-primary text-on-primary font-label-md text-label-md font-semibold flex items-center justify-center gap-2 hover:bg-primary-container transition-all active:scale-[0.98] shadow-sm cursor-pointer disabled:opacity-75"
        >
          {isRunning ? (
            <>
              <span className="material-symbols-outlined text-[18px] animate-spin">sync</span>
              <span>Calculating Fusion Tensor...</span>
            </>
          ) : (
            <>
              <span className="material-symbols-outlined text-[18px]">neurology</span>
              <span>Run Multimodal Fusion</span>
            </>
          )}
        </button>
      </div>

      {/* Patient Facing Protocol Clarification Disclaimer */}
      <footer className="bg-surface-container-low p-space-sm rounded-xl flex items-center gap-space-xs text-on-surface-variant border border-surface-container-high/30">
        <span className="material-symbols-outlined text-[16px] text-tertiary shrink-0">info</span>
        <p className="font-disclaimer-text text-disclaimer-text">
          Investigational use only. Does not replace MDS-UPDRS Part III clinical motor exams or expert dopamine transporter (DaTscan) assessment.
        </p>
      </footer>

      {/* Save Draft Toast */}
      {saveToast && (
        <div className="fixed bottom-24 lg:bottom-8 left-1/2 -translate-x-1/2 bg-inverse-surface text-inverse-on-surface px-space-md py-2 rounded-lg font-label-sm text-label-sm flex items-center gap-space-xs shadow-xl z-50 animate-in fade-in slide-in-from-bottom-2">
          <span className="material-symbols-outlined text-[16px] text-tertiary-fixed">task_alt</span>
          <span>Draft assessment state persisted locally.</span>
        </div>
      )}
    </div>
  );
};
