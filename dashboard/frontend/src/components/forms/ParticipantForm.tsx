import React from 'react';
import { User, ShieldCheck } from 'lucide-react';
import { usePipelineStore } from '../../store/usePipelineStore';

export const ParticipantForm: React.FC = () => {
  const { participantId, age, sex, setParticipantId, setAge, setSex, isAnalyzing } =
    usePipelineStore();

  return (
    <section className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
      <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-100">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-slate-100 rounded-lg text-slate-700">
            <User className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-900">Step 1: Participant Information</h2>
            <p className="text-xs text-slate-500">Pseudonymous identification for screening registry</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-slate-500 bg-slate-50 px-2.5 py-1 rounded-full border border-slate-200">
          <ShieldCheck className="w-3.5 h-3.5 text-teal-600" />
          <span>Strict Privacy: No PII collected</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Participant ID */}
        <div>
          <label htmlFor="participant-id" className="block text-xs font-semibold text-slate-700 mb-1.5">
            Pseudonymous Identifier (PID)
          </label>
          <input
            id="participant-id"
            type="text"
            disabled={isAnalyzing}
            value={participantId}
            onChange={(e) => setParticipantId(e.target.value)}
            placeholder="e.g. PAR-001"
            className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-teal-500 bg-slate-50/50 disabled:bg-slate-100 disabled:text-slate-400 font-mono"
          />
          <p className="text-[11px] text-slate-400 mt-1">De-identified cohort code only.</p>
        </div>

        {/* Age */}
        <div>
          <label htmlFor="participant-age" className="block text-xs font-semibold text-slate-700 mb-1.5">
            Participant Age (Years)
          </label>
          <input
            id="participant-age"
            type="number"
            min={40}
            max={90}
            disabled={isAnalyzing}
            value={age}
            onChange={(e) => setAge(Number(e.target.value))}
            className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-teal-500 bg-slate-50/50 disabled:bg-slate-100 disabled:text-slate-400"
          />
          <p className="text-[11px] text-slate-400 mt-1">Target screening range: 40 to 90 years.</p>
        </div>

        {/* Sex */}
        <div>
          <label htmlFor="participant-sex" className="block text-xs font-semibold text-slate-700 mb-1.5">
            Biological Sex
          </label>
          <select
            id="participant-sex"
            disabled={isAnalyzing}
            value={sex}
            onChange={(e) => setSex(e.target.value as 'female' | 'male')}
            className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-teal-500 bg-slate-50/50 disabled:bg-slate-100 disabled:text-slate-400"
          >
            <option value="female">Female</option>
            <option value="male">Male</option>
          </select>
          <p className="text-[11px] text-slate-400 mt-1">Used for demographic baseline adjustment.</p>
        </div>
      </div>
    </section>
  );
};
