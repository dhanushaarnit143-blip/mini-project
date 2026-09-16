import React, { useState } from 'react';
import { FusionResult, AssessmentData } from '../types';
import { initialAssessmentData } from '../data/mockCohort';
import { generateRiskReportPdf } from '../utils/generateReportPdf';

interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  result: FusionResult;
  assessmentData?: AssessmentData;
}

export const ExportModal: React.FC<ExportModalProps> = ({ isOpen, onClose, result, assessmentData }) => {
  const [format, setFormat] = useState<'pdf' | 'json'>('pdf');
  const [isExporting, setIsExporting] = useState(false);
  const [downloadReady, setDownloadReady] = useState(false);

  if (!isOpen) return null;

  const handleExport = () => {
    setIsExporting(true);
    setTimeout(() => {
      setIsExporting(false);
      setDownloadReady(true);
      
      if (format === 'pdf') {
        const currentData: AssessmentData = assessmentData || {
          ...initialAssessmentData,
          cohortId: result.subjectId,
        };
        generateRiskReportPdf(result, currentData);
      } else if (format === 'json') {
        const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(
          JSON.stringify({ result, assessmentData: assessmentData || initialAssessmentData }, null, 2)
        )}`;
        const downloadAnchor = document.createElement('a');
        downloadAnchor.setAttribute('href', jsonString);
        downloadAnchor.setAttribute('download', `MPF-${result.subjectId}-report.json`);
        document.body.appendChild(downloadAnchor);
        downloadAnchor.click();
        downloadAnchor.remove();
      }
    }, 900);
  };

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-in fade-in"
      onClick={onClose}
    >
      <div 
        className="bg-surface-container-lowest rounded-2xl p-space-lg shadow-2xl border border-surface-container-high w-full max-w-md flex flex-col gap-space-md"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between pb-2 border-b border-surface-container-high">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-[22px]">download</span>
            <span className="font-panchang text-sm font-bold text-on-surface">Export Research Dossier</span>
          </div>
          <button 
            onClick={onClose}
            className="text-on-surface-variant hover:text-on-surface p-1 rounded-lg"
          >
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        <div className="flex flex-col gap-3 text-xs">
          <p className="text-on-surface-variant leading-relaxed">
            Generate an archival-grade clinical dossier including cross-modal attribution vectors, Bayesian uncertainty intervals, and metadata checksums for {result.subjectId}.
          </p>

          <div className="flex flex-col gap-1.5">
            <label className="font-semibold text-on-surface">Export Format</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => { setFormat('pdf'); setDownloadReady(false); }}
                className={`py-2 px-3 rounded-xl border flex items-center justify-center gap-2 font-semibold transition-all ${
                  format === 'pdf'
                    ? 'border-primary bg-primary-fixed text-on-primary-fixed'
                    : 'border-surface-container-high text-on-surface-variant hover:bg-surface-container-low'
                }`}
              >
                <span className="material-symbols-outlined text-[18px]">picture_as_pdf</span>
                Clinical PDF
              </button>
              <button
                type="button"
                onClick={() => { setFormat('json'); setDownloadReady(false); }}
                className={`py-2 px-3 rounded-xl border flex items-center justify-center gap-2 font-semibold transition-all ${
                  format === 'json'
                    ? 'border-primary bg-primary-fixed text-on-primary-fixed'
                    : 'border-surface-container-high text-on-surface-variant hover:bg-surface-container-low'
                }`}
              >
                <span className="material-symbols-outlined text-[18px]">data_object</span>
                Raw JSON
              </button>
            </div>
          </div>

          <div className="p-3 bg-surface-container-low rounded-xl flex flex-col gap-1.5 text-on-surface-variant">
            <div className="flex justify-between">
              <span>Integrated Risk:</span>
              <span className="font-bold text-on-surface">{result.integratedRiskScore} ({result.riskClassification})</span>
            </div>
            <div className="flex justify-between">
              <span>Uncertainty Margin:</span>
              <span className="font-bold text-on-surface">±{result.uncertaintyMargin}</span>
            </div>
            <div className="flex justify-between">
              <span>Data Streams:</span>
              <span className="font-bold text-on-surface">5 Modalities (1 Imputed)</span>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-2 pt-1">
          {downloadReady ? (
            <div className="p-2.5 rounded-xl bg-emerald-50 text-emerald-900 flex items-center justify-between text-xs font-semibold">
              <div className="flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[18px] text-emerald-700">task_alt</span>
                <span>Dossier compiled: MPF-{result.subjectId}.{format}</span>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="text-emerald-800 underline text-[11px]"
              >
                Done
              </button>
            </div>
          ) : (
            <button
              type="button"
              disabled={isExporting}
              onClick={handleExport}
              className="w-full py-2.5 rounded-xl bg-primary text-on-primary font-panchang text-xs font-semibold flex items-center justify-center gap-2 hover:bg-primary-container transition-all active:scale-98 disabled:opacity-60"
            >
              {isExporting ? (
                <>
                  <span className="material-symbols-outlined text-[18px] animate-spin">sync</span>
                  <span>Compiling Dossier...</span>
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-[18px]">file_download</span>
                  <span>Generate &amp; Download {format.toUpperCase()}</span>
                </>
              )}
            </button>
          )}

          <button
            type="button"
            onClick={onClose}
            className="w-full py-2 rounded-lg text-on-surface-variant hover:bg-surface-container text-xs font-medium transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};
