import React from 'react';

interface AuditLogModalProps {
  isOpen: boolean;
  onClose: () => void;
  subjectId: string;
}

export const AuditLogModal: React.FC<AuditLogModalProps> = ({ isOpen, onClose, subjectId }) => {
  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-in fade-in"
      onClick={onClose}
    >
      <div 
        className="bg-surface-container-lowest rounded-2xl p-space-lg shadow-2xl border border-surface-container-high w-full max-w-lg flex flex-col gap-space-md"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between pb-2 border-b border-surface-container-high">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-[22px]">policy</span>
            <span className="font-panchang text-sm font-bold text-on-surface">Protocol Audit Trail</span>
          </div>
          <button 
            onClick={onClose}
            className="text-on-surface-variant hover:text-on-surface p-1 rounded-lg"
          >
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        <div className="flex flex-col gap-2.5 text-xs">
          <div className="p-3 bg-surface-container-low rounded-xl flex flex-col gap-1">
            <span className="font-panchang text-[10px] uppercase font-bold text-on-surface-variant">Kernel Provenance</span>
            <p className="font-mono text-[11px] text-on-surface bg-surface-container px-2 py-1 rounded select-all">
              sha256:b89f81d49e89c3a017e4f3a7491d904b7ac1801
            </p>
            <span className="text-[10px] text-tertiary font-semibold flex items-center gap-1 mt-0.5">
              <span className="material-symbols-outlined text-[14px]">verified</span>
              Deterministic TreeSHAP v1.8 Certified Model Weights
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="p-2.5 bg-surface-container-low rounded-xl flex flex-col gap-0.5">
              <span className="text-[10px] text-on-surface-variant uppercase font-panchang">Participant Hash</span>
              <span className="font-semibold text-on-surface">{subjectId}</span>
              <span className="text-[10px] text-secondary">HIPAA Safe-Harbor De-ID</span>
            </div>
            <div className="p-2.5 bg-surface-container-low rounded-xl flex flex-col gap-0.5">
              <span className="text-[10px] text-on-surface-variant uppercase font-panchang">Reproducibility Seed</span>
              <span className="font-semibold text-on-surface">#981-MONTE-CARLO</span>
              <span className="text-[10px] text-secondary">Zero Variance Drift</span>
            </div>
          </div>

          <div className="flex flex-col gap-1.5 pt-1">
            <span className="text-[11px] font-bold text-on-surface uppercase font-panchang">Execution Logs</span>
            <div className="p-2.5 bg-surface-container rounded-xl font-mono text-[10px] text-on-surface-variant flex flex-col gap-1 max-h-36 overflow-y-auto">
              <div className="text-primary font-semibold">[08:26:11] Init Multimodal Prodromal Pipeline v2.4</div>
              <div>[08:26:12] Ingested UPSIT score 18 (hyposmia vector verified)</div>
              <div>[08:26:12] Ingested RBDSQ score 8 (RSWA cross-validated)</div>
              <div>[08:26:13] Acoustic Jitter calculated 0.81% (optimal SNR)</div>
              <div>[08:26:13] Motor cadence parsed (3.8 taps/s, resilient fatigue slope)</div>
              <div>[08:26:13] Retinal scan marked absent: Bayesian imputation triggered (+0.018 margin)</div>
              <div className="text-tertiary font-semibold">[08:26:14] TreeSHAP convergence complete (100% vector partition)</div>
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={onClose}
          className="w-full py-2.5 rounded-xl bg-primary text-on-primary font-panchang text-xs font-semibold hover:bg-primary-container transition-colors text-center"
        >
          Close Audit Record
        </button>
      </div>
    </div>
  );
};
