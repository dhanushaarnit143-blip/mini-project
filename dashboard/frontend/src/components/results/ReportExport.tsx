import React from 'react';
import { Download, FileJson, FileText } from 'lucide-react';
import { AnalysisResponse } from '../../types/pipeline';

interface ReportExportProps {
  result: AnalysisResponse;
}

export const ReportExport: React.FC<ReportExportProps> = ({ result }) => {
  const handleDownloadJson = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(result, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `mpf_screening_${result.participant_id}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handleDownloadMarkdown = () => {
    const mdLines = [
      `# MPF-PD Multimodal Risk Screening Session Summary`,
      ``,
      `> **RESEARCH PROTOTYPE ONLY** — NOT FOR CLINICAL DIAGNOSIS.`,
      `> This summary is an investigational risk pattern estimate for research screening studies only.`,
      `> Requires clinician review if used in future clinical studies.`,
      ``,
      `## 1. Participant Details`,
      `- **Participant ID:** ${result.participant_id}`,
      `- **Age:** ${result.demographics.age}`,
      `- **Sex:** ${result.demographics.sex}`,
      `- **Session Date:** ${new Date().toISOString()}`,
      ``,
      `## 2. Multimodal Fusion Risk Signal`,
      `- **Risk Pattern Observed:** ${result.fusion.risk_pattern}`,
      `- **Multimodal Risk Score:** ${(result.fusion.risk_score * 100).toFixed(2)}%`,
      `- **Model Version:** ${result.fusion.model_version}`,
      `- **Experiment Type:** ${result.fusion.experiment_type}`,
      ``,
      `### Gating Attention Weights`,
    ];

    for (const [mod, weight] of Object.entries(result.fusion.gate_weights)) {
      const isPresent = result.fusion.modality_presence[mod];
      mdLines.push(`- **${mod.toUpperCase()}**: ${(weight * 100).toFixed(1)}% (${isPresent ? 'Included' : 'Masked / Absent'})`);
    }

    mdLines.push(``, `## 3. Missing Modality Evaluation`);
    if (result.missing_modalities.length > 0) {
      mdLines.push(`- **Omitted Modalities:** ${result.missing_modalities.join(', ')}`);
      mdLines.push(`- **Uncertainty Note:** Dynamic neural gating rebalanced attention across available modalities. Omitted modalities increase research estimate uncertainty.`);
    } else {
      mdLines.push(`- **Completeness:** All 5 modalities were available for this session.`);
    }

    mdLines.push(``, `## 4. Top SHAP Contributors`);
    mdLines.push(`### Features Increasing Risk Signal`);
    for (const item of result.explainability.positive_contributors.slice(0, 5)) {
      mdLines.push(`- **${item.feature_name}** (${item.modality_group}): +${item.shap_value.toFixed(4)}`);
    }
    mdLines.push(``, `### Features Decreasing Risk Signal`);
    for (const item of result.explainability.negative_contributors.slice(0, 5)) {
      mdLines.push(`- **${item.feature_name}** (${item.modality_group}): ${item.shap_value.toFixed(4)}`);
    }

    mdLines.push(``, `## 5. Investigational Disclaimers`);
    for (const w of result.warnings) {
      mdLines.push(`- ${w}`);
    }

    const dataStr = 'data:text/markdown;charset=utf-8,' + encodeURIComponent(mdLines.join('\n'));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `mpf_report_${result.participant_id}.md`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="bg-slate-50 border border-slate-200 rounded-2xl p-6 flex flex-col sm:flex-row items-center justify-between gap-4">
      <div>
        <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
          <Download className="w-4 h-4 text-teal-600" />
          <span>Export Research Session Artifacts</span>
        </h4>
        <p className="text-xs text-slate-500 mt-0.5">
          Download structured JSON or Markdown session summary with reproducible features and SHAP values.
        </p>
      </div>

      <div className="flex items-center gap-3 w-full sm:w-auto">
        <button
          type="button"
          onClick={handleDownloadJson}
          className="flex-1 sm:flex-initial flex items-center justify-center gap-2 px-4 py-2.5 bg-white border border-slate-300 hover:bg-slate-100 text-slate-700 text-xs font-semibold rounded-xl shadow-sm transition-all"
        >
          <FileJson className="w-4 h-4 text-teal-600" />
          <span>Download JSON</span>
        </button>

        <button
          type="button"
          onClick={handleDownloadMarkdown}
          className="flex-1 sm:flex-initial flex items-center justify-center gap-2 px-4 py-2.5 bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold rounded-xl shadow-sm transition-all"
        >
          <FileText className="w-4 h-4" />
          <span>Download Report (.md)</span>
        </button>
      </div>
    </div>
  );
};
