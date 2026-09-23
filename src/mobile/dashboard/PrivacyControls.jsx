import React, { useState } from 'react';
import { Shield, ShieldAlert, Download, Trash2, Eye, Check, X, AlertTriangle, Key, Lock, FileText, ChevronDown, ChevronUp } from 'lucide-react';

/**
 * PrivacyControls Component — Section 6: Privacy & Data Controls
 * 
 * Provides participants with complete sovereignty over their research data:
 * - View and manage granular consent status (data collection, audio storage, research export, sensors)
 * - Revoke consent at any time with immediate collection cessation
 * - Export research data in machine-readable JSON (GDPR Article 20 / portability)
 * - Irreversibly delete all personal data with phrase confirmation (GDPR Article 17)
 * - Transparent inspection of collected features vs forbidden private data
 * 
 * Strict Compliance:
 * - Rule 3: Privacy first (no keystroke text, no background recording, no passwords)
 * - Rule 2: Front camera is designated Ocular/Visual Behavior Module (not retinal imaging)
 */

export const DELETION_CONFIRMATION_PHRASE = 'DELETE MY RESEARCH DATA';

export function PrivacyControls({
  consents = {
    data_collection: true,
    audio_storage: false,
    research_export: true,
    camera_access: true,
    microphone_access: true,
    motion_access: true,
    keyboard_access: true
  },
  pseudonymousId = 'ps_9f8e7d_2026',
  onUpdateConsent,
  onExportData,
  onDeleteData
}) {
  const [localConsents, setLocalConsents] = useState(consents);
  const [showExportModal, setShowExportModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showTransparencyModal, setShowTransparencyModal] = useState(false);
  const [deleteInput, setDeleteInput] = useState('');
  const [deleteError, setDeleteError] = useState('');
  const [exporting, setExporting] = useState(false);
  const [exportComplete, setExportComplete] = useState(false);

  const handleToggleConsent = (key) => {
    const updated = {
      ...localConsents,
      [key]: !localConsents[key]
    };
    setLocalConsents(updated);
    if (onUpdateConsent) {
      onUpdateConsent(key, updated[key]);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    setExportComplete(false);
    try {
      if (onExportData) {
        await onExportData();
      } else {
        // Fallback local download simulation
        await new Promise(r => setTimeout(r, 600));
        const samplePackage = {
          export_version: '1.0.0',
          export_timestamp: new Date().toISOString(),
          pseudonymous_id: pseudonymousId,
          disclaimer: 'MPF Mobile Research Data Export. Research prototype data for personal evaluation and portability. Not a clinical diagnostic report.',
          consents: localConsents
        };
        const blob = new Blob([JSON.stringify(samplePackage, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `mpf_research_export_${pseudonymousId}.json`;
        a.click();
        URL.revokeObjectURL(url);
      }
      setExportComplete(true);
    } catch (err) {
      console.error('Export failed:', err);
    } finally {
      setExporting(false);
    }
  };

  const handleDeleteConfirm = () => {
    if (deleteInput.trim() !== DELETION_CONFIRMATION_PHRASE) {
      setDeleteError(`Please type exact confirmation phrase: "${DELETION_CONFIRMATION_PHRASE}"`);
      return;
    }
    setDeleteError('');
    if (onDeleteData) {
      onDeleteData(deleteInput.trim());
    }
    setShowDeleteModal(false);
  };

  return (
    <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 shadow-lg space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <Lock className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">Privacy & Participant Controls</h3>
            <p className="text-[11px] text-slate-400">
              Pseudonymous ID: <span className="font-mono text-indigo-300">{pseudonymousId}</span>
            </p>
          </div>
        </div>

        <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-300">
          Encrypted & Isolated
        </span>
      </div>

      {/* Consent Toggles */}
      <div className="space-y-2.5">
        <div className="text-xs font-semibold text-slate-300">
          Granular Permission Toggles
        </div>

        <div className="space-y-2">
          {consentItems.map((item) => {
            const isGranted = localConsents[item.key] ?? false;
            return (
              <div
                key={item.key}
                className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex items-center justify-between gap-3"
              >
                <div className="space-y-0.5">
                  <div className="text-xs font-semibold text-slate-200">{item.title}</div>
                  <div className="text-[11px] text-slate-400 leading-tight">{item.description}</div>
                </div>

                <button
                  type="button"
                  onClick={() => handleToggleConsent(item.key)}
                  className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                    isGranted ? 'bg-indigo-600' : 'bg-slate-800'
                  }`}
                  role="switch"
                  aria-checked={isGranted}
                >
                  <span
                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out ${
                      isGranted ? 'translate-x-5' : 'translate-x-0'
                    }`}
                  />
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Action Buttons: Transparency, Export, Delete */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1">
        {/* View What is Collected */}
        <button
          onClick={() => setShowTransparencyModal(true)}
          className="p-3 rounded-xl bg-slate-950 border border-slate-800 hover:border-slate-700 text-xs text-slate-300 font-medium flex items-center justify-center gap-2 transition-colors"
        >
          <Eye className="w-4 h-4 text-indigo-400" />
          <span>What is Collected</span>
        </button>

        {/* Export Data */}
        <button
          onClick={handleExport}
          disabled={exporting}
          className="p-3 rounded-xl bg-slate-950 border border-slate-800 hover:border-slate-700 text-xs text-slate-300 font-medium flex items-center justify-center gap-2 transition-colors"
        >
          <Download className="w-4 h-4 text-teal-400" />
          <span>{exporting ? 'Exporting...' : exportComplete ? 'Exported (JSON)' : 'Export My Data'}</span>
        </button>

        {/* Delete Data */}
        <button
          onClick={() => setShowDeleteModal(true)}
          className="p-3 rounded-xl bg-amber-950/20 border border-amber-800/40 hover:bg-amber-950/40 text-xs text-amber-300 font-medium flex items-center justify-center gap-2 transition-colors"
        >
          <Trash2 className="w-4 h-4 text-amber-400" />
          <span>Delete My Data</span>
        </button>
      </div>

      {/* Modal: What is Collected */}
      {showTransparencyModal && (
        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-bold text-white text-sm">Transparency & Privacy Guarantee</span>
            <button
              onClick={() => setShowTransparencyModal(false)}
              className="text-slate-400 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="space-y-2 text-slate-300 text-[11px] leading-relaxed">
            <div className="p-2.5 rounded-lg bg-emerald-950/30 border border-emerald-700/40 text-emerald-200 space-y-1">
              <span className="font-semibold text-emerald-300">Collected Features:</span>
              <p>• Typing: Key hold durations and flight latencies (in milliseconds).</p>
              <p>• Voice: Acoustic pitch jitter, shimmer, and harmonics-to-noise ratio from guided 5s phonation.</p>
              <p>• Motor: Accelerometer-derived cadence, stride variance, and tremor power (3.5–7.0 Hz band).</p>
              <p>• Visual: Ocular/Visual Behavior Module measures gaze stability and blink rate.</p>
              <p>• Sleep: Daily subjective sleep duration and 13-item RBDSQ survey answers.</p>
            </div>

            <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 space-y-1">
              <span className="font-semibold text-slate-200">Strictly NEVER Collected:</span>
              <p>• Zero keystroke characters, letters, or reconstructed typed text.</p>
              <p>• Zero continuous background microphone or camera recordings.</p>
              <p>• Zero passwords, authentication tokens, or personal identifiers.</p>
              <p>• Zero retinal scans (front camera tracks ocular behavior only, NOT retinal imaging).</p>
            </div>
          </div>
        </div>
      )}

      {/* Modal / Card: Delete Confirmation */}
      {showDeleteModal && (
        <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-600/50 space-y-3 text-xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-amber-300 font-bold text-sm">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <span>Permanent Research Data Deletion</span>
            </div>
            <button
              onClick={() => setShowDeleteModal(false)}
              className="text-amber-400 hover:text-amber-200"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <p className="text-amber-200/90 text-[11px] leading-relaxed">
            This action will permanently and irreversibly erase all your recorded sessions, feature vectors, personal baseline profile, and screening history from this device and research servers.
          </p>

          <div className="space-y-1.5">
            <label className="text-[11px] text-amber-300 font-semibold block">
              Type <span className="font-mono text-white underline">{DELETION_CONFIRMATION_PHRASE}</span> to confirm:
            </label>
            <input
              type="text"
              value={deleteInput}
              onChange={(e) => setDeleteInput(e.target.value)}
              placeholder={DELETION_CONFIRMATION_PHRASE}
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-amber-600/60 text-white font-mono text-xs focus:outline-none focus:border-amber-400"
            />
            {deleteError && (
              <div className="text-[11px] text-amber-400 font-medium">{deleteError}</div>
            )}
          </div>

          <div className="flex justify-end gap-2 pt-1">
            <button
              onClick={() => setShowDeleteModal(false)}
              className="px-3 py-1.5 rounded-lg bg-slate-900 text-slate-300 text-xs hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              onClick={handleDeleteConfirm}
              className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold text-xs"
            >
              Confirm Permanent Erasure
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

const consentItems = [
  {
    key: 'data_collection',
    title: 'Digital Biomarker Collection',
    description: 'Allow on-device extraction of typing, vocal, motor, visual, and sleep metrics.'
  },
  {
    key: 'audio_storage',
    title: 'Research Raw Audio Storage',
    description: 'Optional storage of raw acoustic phonation recordings for acoustic model validation.'
  },
  {
    key: 'research_export',
    title: 'De-identified Research Sharing',
    description: 'Allow inclusion of pseudonymous, encrypted feature records in the open scientific dataset.'
  },
  {
    key: 'camera_access',
    title: 'Ocular/Visual Behavior Module',
    description: 'Front-camera gaze tracking during guided fixation tasks. Not retinal imaging.'
  },
  {
    key: 'microphone_access',
    title: 'Voice Acoustic Module',
    description: 'Microphone access during guided 5-second sustained /a/ phonation tests.'
  },
  {
    key: 'motion_access',
    title: 'Motor & Gait Sensor Module',
    description: '100 Hz accelerometer and gyroscope access during guided walking and tremor tasks.'
  }
];

export default PrivacyControls;
