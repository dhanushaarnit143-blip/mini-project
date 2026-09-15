import React from 'react';
import { Play, RotateCcw, Loader2, AlertCircle } from 'lucide-react';
import { usePipelineStore } from '../../store/usePipelineStore';

export const AnalysisButton: React.FC = () => {
  const {
    isAnalyzing,
    statusMessage,
    errorMessage,
    result,
    runAnalysis,
    resetAnalysis,
  } = usePipelineStore();

  return (
    <div className="flex flex-col items-center gap-4 py-4">
      {errorMessage && (
        <div
          data-testid="error-toast"
          className="w-full max-w-2xl bg-rose-50 border border-rose-200 text-rose-800 px-4 py-3 rounded-xl flex items-start gap-3 text-sm shadow-sm"
        >
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold text-rose-900">Analysis Error</p>
            <p className="text-xs text-rose-700 mt-0.5">{errorMessage}</p>
          </div>
        </div>
      )}

      <div className="flex items-center gap-3">
        <button
          type="button"
          data-testid="run-analysis-button"
          disabled={isAnalyzing}
          onClick={() => runAnalysis()}
          className="flex items-center gap-2.5 px-6 py-3 rounded-xl bg-teal-600 text-white font-semibold text-sm shadow-md hover:bg-teal-700 active:scale-[0.98] transition-all disabled:bg-slate-300 disabled:cursor-not-allowed"
        >
          {isAnalyzing ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>{statusMessage || 'Processing Pipeline...'}</span>
            </>
          ) : (
            <>
              <Play className="w-4 h-4 fill-current" />
              <span>Run Multimodal Analysis</span>
            </>
          )}
        </button>

        {result && (
          <button
            type="button"
            disabled={isAnalyzing}
            onClick={() => resetAnalysis()}
            className="flex items-center gap-2 px-4 py-3 rounded-xl border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 font-medium text-sm transition-all"
          >
            <RotateCcw className="w-4 h-4" />
            <span>Start New Analysis</span>
          </button>
        )}
      </div>

      {isAnalyzing && (
        <p className="text-xs text-slate-500 animate-pulse">
          Executing neural gating across available modalities...
        </p>
      )}
    </div>
  );
};
