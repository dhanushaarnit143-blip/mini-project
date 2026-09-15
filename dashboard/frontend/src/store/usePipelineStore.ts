import { create } from 'zustand';
import { AnalysisResponse } from '../types/pipeline';
import { analyzeMultimodal } from '../lib/api';

interface PipelineState {
  // Participant Info
  participantId: string;
  age: number;
  sex: 'female' | 'male';

  // Modality inputs & toggles
  olfactoryEnabled: boolean;
  olfactoryScore: number;

  rbdEnabled: boolean;
  rbdScore: number;

  voiceEnabled: boolean;
  voiceFile: File | null;
  voicePreviewUrl: string | null;

  motorEnabled: boolean;
  motorFile: File | null;
  motorFileName: string | null;

  retinaEnabled: boolean;
  retinaFile: File | null;
  retinaPreviewUrl: string | null;

  // Analysis status
  isAnalyzing: boolean;
  statusMessage: string;
  errorMessage: string | null;
  result: AnalysisResponse | null;

  // Actions
  setParticipantId: (id: string) => void;
  setAge: (age: number) => void;
  setSex: (sex: 'female' | 'male') => void;
  setModalityEnabled: (modality: 'olfactory' | 'rbd' | 'voice' | 'motor' | 'retina', enabled: boolean) => void;
  setOlfactoryScore: (score: number) => void;
  setRbdScore: (score: number) => void;
  setVoiceFile: (file: File | null) => void;
  setMotorFile: (file: File | null) => void;
  setRetinaFile: (file: File | null) => void;
  runAnalysis: () => Promise<void>;
  resetAnalysis: () => void;
}

export const usePipelineStore = create<PipelineState>((set, get) => ({
  participantId: 'PAR-8832',
  age: 67,
  sex: 'male',

  olfactoryEnabled: true,
  olfactoryScore: 21,

  rbdEnabled: true,
  rbdScore: 7,

  voiceEnabled: true,
  voiceFile: null,
  voicePreviewUrl: null,

  motorEnabled: true,
  motorFile: null,
  motorFileName: null,

  retinaEnabled: true,
  retinaFile: null,
  retinaPreviewUrl: null,

  isAnalyzing: false,
  statusMessage: '',
  errorMessage: null,
  result: null,

  setParticipantId: (id) => set({ participantId: id }),
  setAge: (age) => set({ age }),
  setSex: (sex) => set({ sex }),

  setModalityEnabled: (modality, enabled) => {
    switch (modality) {
      case 'olfactory':
        set({ olfactoryEnabled: enabled });
        break;
      case 'rbd':
        set({ rbdEnabled: enabled });
        break;
      case 'voice':
        set({ voiceEnabled: enabled });
        break;
      case 'motor':
        set({ motorEnabled: enabled });
        break;
      case 'retina':
        set({ retinaEnabled: enabled });
        break;
    }
  },

  setOlfactoryScore: (score) => set({ olfactoryScore: score }),
  setRbdScore: (score) => set({ rbdScore: score }),

  setVoiceFile: (file) => {
    const prevUrl = get().voicePreviewUrl;
    if (prevUrl) URL.revokeObjectURL(prevUrl);
    set({
      voiceFile: file,
      voicePreviewUrl: file ? URL.createObjectURL(file) : null,
    });
  },

  setMotorFile: (file) => {
    set({
      motorFile: file,
      motorFileName: file ? file.name : null,
    });
  },

  setRetinaFile: (file) => {
    const prevUrl = get().retinaPreviewUrl;
    if (prevUrl) URL.revokeObjectURL(prevUrl);
    set({
      retinaFile: file,
      retinaPreviewUrl: file ? URL.createObjectURL(file) : null,
    });
  },

  runAnalysis: async () => {
    const state = get();
    set({ isAnalyzing: true, errorMessage: null, statusMessage: 'Preparing session data...' });

    try {
      const payload: Record<string, any> = {
        participant_id: state.participantId,
        age: state.age,
        sex: state.sex,
        olfactory: {
          available: state.olfactoryEnabled,
          total_score: state.olfactoryScore,
          pct_correct: Math.min(1.0, state.olfactoryScore / 40.0),
          response_time_mean: 4.8,
        },
        rbd: {
          available: state.rbdEnabled,
          rbdsq_total: state.rbdScore,
          above_cutoff_flag: state.rbdScore >= 5 ? 1 : 0,
          high_weight_item_flags: state.rbdScore >= 6 ? 2 : 0,
        },
        voice: {
          available: state.voiceEnabled,
        },
        motor: {
          available: state.motorEnabled,
        },
        retina: {
          available: state.retinaEnabled,
        },
      };

      // Default reference features if no raw files were uploaded for enabled modalities
      if (state.voiceEnabled && !state.voiceFile) {
        payload.voice.features = {
          jitter_pct: 0.0078,
          jitter_abs: 0.00005,
          shimmer: 0.058,
          hnr: 15.2,
          rpde: 0.44,
          dfa: 0.72,
          ppe: 0.21,
        };
      }

      if (state.motorEnabled && !state.motorFile) {
        payload.motor.features = {
          gait_speed_m_per_s: 0.92,
          cadence_steps_per_min: 94.0,
          stride_interval_mean_s: 1.15,
          stride_interval_cv_pct: 3.2,
          step_regularity: 0.81,
          symmetry_index_pct: 5.0,
          accel_variance: 0.039,
          stance_swing_ratio: 1.82,
        };
      }

      if (state.retinaEnabled && !state.retinaFile) {
        payload.retina.features = {
          vessel_density: 0.063,
          mean_vessel_diameter_px: 2.85,
          vessel_tortuosity_index: 1.14,
          branch_count: 72.0,
          branch_point_density: 0.0031,
          endpoint_count: 55.0,
          peripapillary_vessel_density: 0.071,
          peripapillary_branch_count: 22.0,
          macular_vessel_density: 0.054,
          foveal_avascular_zone_area_px: 380.0,
          optic_disc_detected: 1.0,
          macula_detected: 1.0,
        };
      }

      const formData = new FormData();
      formData.append('payload', JSON.stringify(payload));

      if (state.voiceEnabled && state.voiceFile) {
        formData.append('voice_file', state.voiceFile);
      }
      if (state.motorEnabled && state.motorFile) {
        formData.append('motor_file', state.motorFile);
      }
      if (state.retinaEnabled && state.retinaFile) {
        formData.append('retina_file', state.retinaFile);
      }

      set({ statusMessage: 'Extracting features and executing neural fusion...' });
      const result = await analyzeMultimodal(formData);
      set({ result, isAnalyzing: false, statusMessage: '' });
    } catch (err: any) {
      set({
        isAnalyzing: false,
        statusMessage: '',
        errorMessage: err.message || 'An error occurred during multimodal analysis.',
      });
    }
  },

  resetAnalysis: () => {
    const { voicePreviewUrl, retinaPreviewUrl } = get();
    if (voicePreviewUrl) URL.revokeObjectURL(voicePreviewUrl);
    if (retinaPreviewUrl) URL.revokeObjectURL(retinaPreviewUrl);

    set({
      result: null,
      errorMessage: null,
      statusMessage: '',
      voiceFile: null,
      voicePreviewUrl: null,
      motorFile: null,
      motorFileName: null,
      retinaFile: null,
      retinaPreviewUrl: null,
    });
  },
}));
