import React from 'react';
import {
  Wind,
  Moon,
  Mic,
  Activity,
  Eye,
  UploadCloud,
  FileText,
  Volume2,
  X,
} from 'lucide-react';
import { usePipelineStore } from '../../store/usePipelineStore';

export const ModalityInputs: React.FC = () => {
  const {
    olfactoryEnabled,
    olfactoryScore,
    rbdEnabled,
    rbdScore,
    voiceEnabled,
    voiceFile,
    voicePreviewUrl,
    motorEnabled,
    motorFileName,
    retinaEnabled,
    retinaFile,
    retinaPreviewUrl,
    isAnalyzing,
    setModalityEnabled,
    setOlfactoryScore,
    setRbdScore,
    setVoiceFile,
    setMotorFile,
    setRetinaFile,
  } = usePipelineStore();

  const handleVoiceUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setVoiceFile(e.target.files[0]);
    }
  };

  const handleMotorUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setMotorFile(e.target.files[0]);
    }
  };

  const handleRetinaUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setRetinaFile(e.target.files[0]);
    }
  };

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Step 2: Modality Inputs & Missingness Toggles</h2>
          <p className="text-xs text-slate-500">
            Include available participant records or toggle to "Missing" to test neural gating adaptation.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {/* Olfactory Card */}
        <div
          data-testid="modality-card-olfactory"
          className={`rounded-xl border p-5 transition-all ${
            olfactoryEnabled
              ? 'bg-white border-slate-200 shadow-sm'
              : 'bg-slate-50/80 border-slate-200/60 opacity-60'
          }`}
        >
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <div className="p-1.5 bg-sky-50 text-sky-700 rounded-lg">
                <Wind className="w-4 h-4" />
              </div>
              <span className="text-sm font-semibold text-slate-900">Olfactory</span>
            </div>
            <button
              type="button"
              disabled={isAnalyzing}
              onClick={() => setModalityEnabled('olfactory', !olfactoryEnabled)}
              className={`text-xs px-2.5 py-1 rounded-full font-medium transition-colors ${
                olfactoryEnabled
                  ? 'bg-teal-50 text-teal-700 border border-teal-200'
                  : 'bg-slate-200 text-slate-600'
              }`}
            >
              {olfactoryEnabled ? 'Included' : 'Marked Missing'}
            </button>
          </div>

          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-xs text-slate-600 mb-1">
                <span>UPSIT Total Score</span>
                <span className="font-semibold text-slate-800">{olfactoryScore} / 40</span>
              </div>
              <input
                type="range"
                min={0}
                max={40}
                disabled={!olfactoryEnabled || isAnalyzing}
                value={olfactoryScore}
                onChange={(e) => setOlfactoryScore(Number(e.target.value))}
                className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-teal-600 disabled:cursor-not-allowed"
              />
              <div className="flex justify-between text-[10px] text-slate-400 mt-1">
                <span>Anosmia (0-18)</span>
                <span>Hyposmia (19-33)</span>
                <span>Normosmia (34+)</span>
              </div>
            </div>
          </div>
        </div>

        {/* RBD Card */}
        <div
          data-testid="modality-card-rbd"
          className={`rounded-xl border p-5 transition-all ${
            rbdEnabled
              ? 'bg-white border-slate-200 shadow-sm'
              : 'bg-slate-50/80 border-slate-200/60 opacity-60'
          }`}
        >
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <div className="p-1.5 bg-indigo-50 text-indigo-700 rounded-lg">
                <Moon className="w-4 h-4" />
              </div>
              <span className="text-sm font-semibold text-slate-900">RBD Questionnaire</span>
            </div>
            <button
              type="button"
              disabled={isAnalyzing}
              onClick={() => setModalityEnabled('rbd', !rbdEnabled)}
              className={`text-xs px-2.5 py-1 rounded-full font-medium transition-colors ${
                rbdEnabled
                  ? 'bg-teal-50 text-teal-700 border border-teal-200'
                  : 'bg-slate-200 text-slate-600'
              }`}
            >
              {rbdEnabled ? 'Included' : 'Marked Missing'}
            </button>
          </div>

          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-xs text-slate-600 mb-1">
                <span>RBDSQ Total Score</span>
                <span className="font-semibold text-slate-800">{rbdScore} / 13</span>
              </div>
              <input
                type="range"
                min={0}
                max={13}
                disabled={!rbdEnabled || isAnalyzing}
                value={rbdScore}
                onChange={(e) => setRbdScore(Number(e.target.value))}
                className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-teal-600 disabled:cursor-not-allowed"
              />
              <p className="text-[11px] text-slate-400 mt-2">
                Probable RBD pattern (questionnaire-based) typically indicated by score ≥ 5.
              </p>
            </div>
          </div>
        </div>

        {/* Voice Card */}
        <div
          data-testid="modality-card-voice"
          className={`rounded-xl border p-5 transition-all ${
            voiceEnabled
              ? 'bg-white border-slate-200 shadow-sm'
              : 'bg-slate-50/80 border-slate-200/60 opacity-60'
          }`}
        >
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <div className="p-1.5 bg-emerald-50 text-emerald-700 rounded-lg">
                <Mic className="w-4 h-4" />
              </div>
              <span className="text-sm font-semibold text-slate-900">Voice Acoustics</span>
            </div>
            <button
              type="button"
              disabled={isAnalyzing}
              onClick={() => setModalityEnabled('voice', !voiceEnabled)}
              className={`text-xs px-2.5 py-1 rounded-full font-medium transition-colors ${
                voiceEnabled
                  ? 'bg-teal-50 text-teal-700 border border-teal-200'
                  : 'bg-slate-200 text-slate-600'
              }`}
            >
              {voiceEnabled ? 'Included' : 'Marked Missing'}
            </button>
          </div>

          <div className="space-y-2.5">
            <label className="block text-xs text-slate-600">Sustained Vowel Recording (.wav)</label>
            <div className="border border-dashed border-slate-300 rounded-lg p-3 text-center hover:bg-slate-50 transition-colors relative">
              <input
                type="file"
                accept="audio/wav,audio/x-wav,audio/*"
                disabled={!voiceEnabled || isAnalyzing}
                onChange={handleVoiceUpload}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
              />
              <div className="flex flex-col items-center gap-1 text-slate-500">
                <UploadCloud className="w-5 h-5 text-slate-400" />
                <span className="text-xs font-medium">
                  {voiceFile ? voiceFile.name : 'Upload .WAV recording'}
                </span>
                <span className="text-[10px] text-slate-400">or default acoustic features used</span>
              </div>
            </div>

            {voicePreviewUrl && (
              <div className="pt-1 flex items-center gap-2">
                <Volume2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <audio controls src={voicePreviewUrl} className="h-7 w-full text-xs" />
                <button
                  type="button"
                  onClick={() => setVoiceFile(null)}
                  className="p-1 text-slate-400 hover:text-slate-600"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Motor Card */}
        <div
          data-testid="modality-card-motor"
          className={`rounded-xl border p-5 transition-all ${
            motorEnabled
              ? 'bg-white border-slate-200 shadow-sm'
              : 'bg-slate-50/80 border-slate-200/60 opacity-60'
          }`}
        >
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <div className="p-1.5 bg-amber-50 text-amber-700 rounded-lg">
                <Activity className="w-4 h-4" />
              </div>
              <span className="text-sm font-semibold text-slate-900">Motor & Gait</span>
            </div>
            <button
              type="button"
              disabled={isAnalyzing}
              onClick={() => setModalityEnabled('motor', !motorEnabled)}
              className={`text-xs px-2.5 py-1 rounded-full font-medium transition-colors ${
                motorEnabled
                  ? 'bg-teal-50 text-teal-700 border border-teal-200'
                  : 'bg-slate-200 text-slate-600'
              }`}
            >
              {motorEnabled ? 'Included' : 'Marked Missing'}
            </button>
          </div>

          <div className="space-y-2.5">
            <label className="block text-xs text-slate-600">Sensor Log (.csv / .json)</label>
            <div className="border border-dashed border-slate-300 rounded-lg p-3 text-center hover:bg-slate-50 transition-colors relative">
              <input
                type="file"
                accept=".csv,.json"
                disabled={!motorEnabled || isAnalyzing}
                onChange={handleMotorUpload}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
              />
              <div className="flex flex-col items-center gap-1 text-slate-500">
                <FileText className="w-5 h-5 text-slate-400" />
                <span className="text-xs font-medium">
                  {motorFileName ? motorFileName : 'Upload Gait/Tapping CSV'}
                </span>
                <span className="text-[10px] text-slate-400">or default kinematic features used</span>
              </div>
            </div>

            {motorFileName && (
              <div className="pt-1 flex items-center justify-between text-xs text-slate-600 bg-slate-50 px-2 py-1 rounded border border-slate-200">
                <span className="truncate">{motorFileName}</span>
                <button
                  type="button"
                  onClick={() => setMotorFile(null)}
                  className="p-1 text-slate-400 hover:text-slate-600"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Retina Card */}
        <div
          data-testid="modality-card-retina"
          className={`rounded-xl border p-5 transition-all md:col-span-2 lg:col-span-1 ${
            retinaEnabled
              ? 'bg-white border-slate-200 shadow-sm'
              : 'bg-slate-50/80 border-slate-200/60 opacity-60'
          }`}
        >
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <div className="p-1.5 bg-rose-50 text-rose-700 rounded-lg">
                <Eye className="w-4 h-4" />
              </div>
              <span className="text-sm font-semibold text-slate-900">Retinal Microvasculature</span>
            </div>
            <button
              type="button"
              disabled={isAnalyzing}
              onClick={() => setModalityEnabled('retina', !retinaEnabled)}
              className={`text-xs px-2.5 py-1 rounded-full font-medium transition-colors ${
                retinaEnabled
                  ? 'bg-teal-50 text-teal-700 border border-teal-200'
                  : 'bg-slate-200 text-slate-600'
              }`}
            >
              {retinaEnabled ? 'Included' : 'Marked Missing'}
            </button>
          </div>

          <div className="space-y-2.5">
            <label className="block text-xs text-slate-600">Fundus Photograph (.jpg / .png)</label>
            <div className="border border-dashed border-slate-300 rounded-lg p-3 text-center hover:bg-slate-50 transition-colors relative">
              <input
                type="file"
                accept="image/jpeg,image/png,image/*"
                disabled={!retinaEnabled || isAnalyzing}
                onChange={handleRetinaUpload}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
              />
              <div className="flex flex-col items-center gap-1 text-slate-500">
                <UploadCloud className="w-5 h-5 text-slate-400" />
                <span className="text-xs font-medium">
                  {retinaFile ? retinaFile.name : 'Upload Fundus Photograph'}
                </span>
                <span className="text-[10px] text-slate-400">or default vessel biomarkers used</span>
              </div>
            </div>

            {retinaPreviewUrl && (
              <div className="pt-1 flex items-center gap-3 bg-slate-50 p-2 rounded-lg border border-slate-200">
                <img
                  src={retinaPreviewUrl}
                  alt="Fundus preview"
                  className="w-12 h-12 object-cover rounded border border-slate-300"
                />
                <div className="text-xs text-slate-600 truncate flex-1">
                  <span className="font-medium truncate block">{retinaFile?.name}</span>
                  <span className="text-[10px] text-slate-400">Client-side preview</span>
                </div>
                <button
                  type="button"
                  onClick={() => setRetinaFile(null)}
                  className="p-1 text-slate-400 hover:text-slate-600"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};
