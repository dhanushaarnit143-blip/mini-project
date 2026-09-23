/**
 * MPF Mobile Extension — Sleep Module Index (Phase 8)
 *
 * Public surface of the Sleep/RBD questionnaire collection module.
 *
 * SENSOR INTEGRITY & PRIVACY:
 *   - "Self-reported sleep behavior" & "Questionnaire-based indicator"
 *   - Probable RBD self-report — NOT polysomnography or clinical diagnosis.
 *   - "Research screening result — not a clinical diagnosis."
 *   - "Deviation from personal baseline."
 */

export { SleepQuestionnaireScreen } from './SleepQuestionnaireScreen.jsx';

export {
  computeSleepScore,
  evaluateRbdConcernWindow,
  QUESTIONNAIRE_VERSION,
  SCORER_VERSION,
  SLEEP_LABELS,
  MOVEMENT_RESPONSES,
  VALID_MOVEMENT_RESPONSES,
} from './sleepScorer.js';

export {
  SleepSessionModel,
  CURRENT_QUESTIONNAIRE_VERSION,
} from './sleepSessionModel.js';
