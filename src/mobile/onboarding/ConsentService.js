/**
 * MPF Mobile Extension — Onboarding Consent Coordinator
 * Re-exports core ConsentService and provides onboarding state helpers.
 */

import { ConsentService, CONSENT_TYPES, CURRENT_CONSENT_VERSION } from '../services/consentService.js';

export { ConsentService, CONSENT_TYPES, CURRENT_CONSENT_VERSION };

export class OnboardingConsentManager {
  constructor(supabaseClient = null) {
    this.service = new ConsentService(supabaseClient);
    this.state = {
      understandsScope: false,
      consents: {
        [CONSENT_TYPES.DATA_COLLECTION]: false,
        [CONSENT_TYPES.AUDIO_STORAGE]: false,
        [CONSENT_TYPES.RESEARCH_EXPORT]: false,
        [CONSENT_TYPES.CAMERA_ACCESS]: false,
        [CONSENT_TYPES.MICROPHONE_ACCESS]: false,
        [CONSENT_TYPES.MOTION_ACCESS]: false,
        [CONSENT_TYPES.KEYBOARD_ACCESS]: false,
      },
      permissionsGranted: {
        camera: false,
        microphone: false,
        motion: false,
        keyboard: true
      },
      pseudonymousId: null,
      email: '',
      participantId: null
    };
  }

  setConsent(consentType, value) {
    this.state.consents[consentType] = Boolean(value);
  }

  setPermission(permissionType, value) {
    this.state.permissionsGranted[permissionType] = Boolean(value);
    // Link permission state to consent records
    if (permissionType === 'camera') this.state.consents[CONSENT_TYPES.CAMERA_ACCESS] = Boolean(value);
    if (permissionType === 'microphone') this.state.consents[CONSENT_TYPES.MICROPHONE_ACCESS] = Boolean(value);
    if (permissionType === 'motion') this.state.consents[CONSENT_TYPES.MOTION_ACCESS] = Boolean(value);
    if (permissionType === 'keyboard') this.state.consents[CONSENT_TYPES.KEYBOARD_ACCESS] = Boolean(value);
  }

  canProceedToConsent() {
    return this.state.understandsScope;
  }

  hasRequiredConsents() {
    return this.state.consents[CONSENT_TYPES.DATA_COLLECTION] === true;
  }

  async commitOnboardingConsent(participantId) {
    if (!this.hasRequiredConsents()) {
      throw new Error('Required research data collection consent has not been granted.');
    }
    this.state.participantId = participantId;
    return await this.service.recordConsent({
      participantId,
      consentVersion: CURRENT_CONSENT_VERSION,
      consents: this.state.consents
    });
  }
}

export default OnboardingConsentManager;
